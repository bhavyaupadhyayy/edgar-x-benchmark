"""Acquire the primary 10-K document for each frozen 10-K accession.

Resumable, atomic, rate-limited, and auditable. Every requirement here exists
because a multi-hour download has many ways to corrupt a corpus quietly:

  - the accession -> primary-document mapping is deterministic, taken from the
    bulk submissions archive inventory, never guessed from a directory listing;
  - **no 10-K/A substitution.** Only the exact primary document of the exact
    frozen accession is fetched. A missing original is recorded as missing and is
    never replaced by a later amendment;
  - raw downloaded bytes are preserved. Files are stored gzip-compressed to keep
    the corpus inside available disk, and the recorded SHA-256 is of the
    UNCOMPRESSED payload, so the original bytes are recoverable and verifiable;
  - writes are atomic: a .part file is renamed only after the payload validates;
  - retries are bounded, with backoff, and distinguish permanently unavailable
    from retryable;
  - the manifest is appended per document, so an interrupted run resumes without
    re-requesting anything already recorded.

Rate limiting: the global request rate is capped at SEC_MAX_REQUESTS_PER_SECOND
(8 rps) by `_GlobalLimiter`, a single lock-guarded gate every worker passes
through. `--workers N` overlaps request LATENCY only -- measured single-threaded
throughput was 1.1 docs/s against a 0.125 s rate floor, i.e. ~85% of wall time
was round-trip wait, which would have made a 59,499-document run take ~14.6 h.
Concurrency does not raise the request rate above 8 rps and never can: each
worker's SecClient has its internal throttle made inert precisely so the one
shared limiter is the only governor, rather than having two independent
limiters neither of which sees the true global rate.

Do not run this concurrently with production EDGAR ingestion.

    python3 gate3_acquire_tenk.py --email you@domain.com
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from constants import SEC_MAX_REQUESTS_PER_SECOND

# A nominal 8.0 rps limiter measured 8.09 rps under 12-thread contention: the
# gate hands out grants on a monotonic schedule, but thread wake-up jitter lets a
# burst land marginally early. 8.09 > 8 breaches the stated requirement even
# though the cause is only timing noise, so the configured rate carries a safety
# margin below the cap rather than sitting exactly on it.
GLOBAL_RATE_LIMIT = 7.5
from sec_download import DownloadError, SecClient, validate_payload

GATE2_DIR = Path("outputs/gate2")
GATE3_DIR = Path("outputs/gate3")
INVENTORY = GATE3_DIR / "tenk_document_inventory.csv"
CORPUS_DIR = Path("10k_text")
MANIFEST = GATE3_DIR / "tenk_acquisition_manifest.csv"

ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{document}"

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2.0, 6.0)
MIN_PLAUSIBLE_BYTES = 200

MANIFEST_FIELDS = ["accession", "cik", "accepted_at", "form",
                   "primary_document", "local_path", "status", "bytes", "sha256"]

# Two denominators that must never be mixed, permanently separated here.
#
#   BENCHMARK OBSERVATION denominator  every eligible 10-K observation, 59,500.
#                                      Used for coverage partitions only.
#   RETRIEVAL TARGET denominator       observations with a named primary
#                                      document, 59,499. Used for HTTP progress
#                                      and for every acquisition rate or success
#                                      figure.
#
# The single observation with no named primary document belongs to the first and
# never to the second: no HTTP request is issued for it. Counting it in the
# retrieval denominator made every progress line and every prose remainder
# off by one (52,217 instead of 52,216; 59,275 instead of 59,274).

STATUS_OK = "ok"
STATUS_NO_NAMED_DOCUMENT = "no_named_primary_document"
STATUS_PERMANENT = "permanently_unavailable"
STATUS_RETRYABLE = "retryable_failure"
STATUS_MALFORMED = "malformed_or_empty"


class _GlobalLimiter:
    """One gate for every worker, so the global rate can never exceed the cap."""

    def __init__(self, requests_per_second: float):
        self._min_interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._next_at = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self._min_interval
        if wait:
            time.sleep(wait)


def load_targets() -> list[dict]:
    accepted = {}
    with (GATE2_DIR / "panel.jsonl").open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                accepted[row["adsh"]] = row["accepted_at"]
    targets = []
    with INVENTORY.open() as handle:
        for row in csv.DictReader(handle):
            targets.append({
                "accession": row["adsh"],
                "cik": int(row["cik"]),
                "accepted_at": accepted.get(row["adsh"], ""),
                "form": "10-K",
                "primary_document": row["primary_document"],
            })
    return targets


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open() as handle:
        return {row["accession"]: row for row in csv.DictReader(handle)}


def document_url(cik: int, accession: str, document: str) -> str:
    return ARCHIVE_URL.format(cik=cik, folder=accession.replace("-", ""),
                              document=document)


def store(payload: bytes, destination: Path) -> None:
    """Atomic gzip write. The uncompressed bytes are what the hash covers."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with gzip.open(partial, "wb") as handle:
        handle.write(payload)
    partial.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True,
                        help="real contact address for the SEC User-Agent")
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after this many new downloads (0 = all)")
    parser.add_argument("--workers", type=int, default=1,
                        help="concurrent fetchers; the global 8 rps cap is "
                             "enforced regardless, so this overlaps latency only")
    args = parser.parse_args()

    workers = max(1, args.workers)
    limiter = _GlobalLimiter(GLOBAL_RATE_LIMIT)
    # Each worker's own throttle is made inert on purpose: two independent
    # limiters would each believe it was under budget while the global rate ran
    # at workers x 8 rps. The shared limiter above is the single governor.
    local = threading.local()

    def worker_client() -> SecClient:
        if not hasattr(local, "client"):
            local.client = SecClient(f"EDGAR-X Research {args.email}",
                                     requests_per_second=10_000)
        return local.client

    # Validate the address once, loudly, before any worker starts.
    SecClient(f"EDGAR-X Research {args.email}",
              requests_per_second=SEC_MAX_REQUESTS_PER_SECOND)
    assert GLOBAL_RATE_LIMIT <= SEC_MAX_REQUESTS_PER_SECOND, "rate above the cap"

    targets = load_targets()
    done = load_manifest()
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    GATE3_DIR.mkdir(parents=True, exist_ok=True)

    fresh_manifest = not MANIFEST.exists()
    handle = MANIFEST.open("a", newline="")
    writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
    if fresh_manifest:
        writer.writeheader()
        handle.flush()

    # Observations with no named primary document are recorded up front and are
    # excluded from the retrieval-progress denominator: they are benchmark
    # observations, not retrieval targets.
    unnamed = [target for target in targets if not target["primary_document"]]
    retrieval_targets = [target for target in targets if target["primary_document"]]
    for target in unnamed:
        if target["accession"] in done:
            continue
        record = dict(target, local_path="", status=STATUS_NO_NAMED_DOCUMENT,
                      bytes=0, sha256="")
        writer.writerow(record)
        handle.flush()
        done[target["accession"]] = record

    pending = [target for target in retrieval_targets
               if target["accession"] not in done
               or done[target["accession"]]["status"] == STATUS_RETRYABLE]
    print(f"benchmark observations       {len(targets)}")
    print(f"retrieval targets            {len(retrieval_targets)} "
          f"(observations with a named primary document)")
    print(f"no primary document          {len(unnamed)} "
          f"(recorded, never requested)")
    print(f"already recorded             {len(done)}")
    print(f"retrieval targets to attempt {len(pending)}")
    print(f"configured global limit {GLOBAL_RATE_LIMIT} rps "
          f"(cap {SEC_MAX_REQUESTS_PER_SECOND}); "
          f"estimated {len(pending) / GLOBAL_RATE_LIMIT / 3600:.2f} h")

    counts = {STATUS_OK: 0, STATUS_PERMANENT: 0, STATUS_RETRYABLE: 0,
              STATUS_MALFORMED: 0, STATUS_NO_NAMED_DOCUMENT: len(unnamed)}
    http_status: dict[str, int] = {}
    state = {"requested": 0, "done": 0, "stop": False, "retries": 0,
             "first_request_at": None, "last_request_at": None}
    write_lock = threading.Lock()
    started = time.time()

    def record_row(record: dict, status: str) -> None:
        with write_lock:
            counts[status] += 1
            state["done"] += 1
            writer.writerow(record)
            handle.flush()
            index = state["done"]
            if index % 500 == 0:
                elapsed = time.time() - started
                rate = index / elapsed if elapsed else 0
                remaining = (len(pending) - index) / rate / 3600 if rate else 0
                print(f"  {index}/{len(pending)}  ok={counts[STATUS_OK]} "
                      f"perm={counts[STATUS_PERMANENT]} "
                      f"retry={counts[STATUS_RETRYABLE]} "
                      f"malformed={counts[STATUS_MALFORMED]}  "
                      f"{rate:.1f} doc/s  ~{remaining:.2f} h left", flush=True)
            if args.limit and counts[STATUS_OK] >= args.limit:
                state["stop"] = True

    def process(target: dict) -> None:
        if state["stop"]:
            return
        accession = target["accession"]
        document = target["primary_document"]
        record = dict(target, local_path="", status="", bytes=0, sha256="")

        if not document:
            record["status"] = STATUS_NO_NAMED_DOCUMENT
            record_row(record, STATUS_NO_NAMED_DOCUMENT)
            return

        destination = CORPUS_DIR / f"{accession}.html.gz"
        if destination.exists() and destination.stat().st_size > 0:
            payload = gzip.open(destination, "rb").read()
            record.update(local_path=str(destination), status=STATUS_OK,
                          bytes=len(payload),
                          sha256=hashlib.sha256(payload).hexdigest())
            record_row(record, STATUS_OK)
            return

        url = document_url(target["cik"], accession, document)
        status = STATUS_RETRYABLE
        payload = b""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            with write_lock:
                state["requested"] += 1
                if attempt > 1:
                    state["retries"] += 1
            limiter.acquire()
            issued_at = time.monotonic()
            try:
                payload = worker_client().fetch(url)
                validate_payload(payload)
                if len(payload) < MIN_PLAUSIBLE_BYTES:
                    status = STATUS_MALFORMED
                    break
                status = STATUS_OK
                with write_lock:
                    http_status["200"] = http_status.get("200", 0) + 1
                    if state["first_request_at"] is None:
                        state["first_request_at"] = issued_at
                    state["last_request_at"] = time.monotonic()
                break
            except DownloadError as error:
                message = str(error)
                with write_lock:
                    label = message.split(":")[0][:40] or "unknown"
                    http_status[label] = http_status.get(label, 0) + 1
                    if state["first_request_at"] is None:
                        state["first_request_at"] = issued_at
                    state["last_request_at"] = time.monotonic()
                if "HTTP 404" in message or "HTTP 403" in message:
                    status = STATUS_PERMANENT
                    break
                status = STATUS_RETRYABLE
                if attempt < MAX_ATTEMPTS:
                    time.sleep(BACKOFF_SECONDS[min(attempt - 1,
                                                   len(BACKOFF_SECONDS) - 1)])

        if status == STATUS_OK:
            store(payload, destination)
            record.update(local_path=str(destination), bytes=len(payload),
                          sha256=hashlib.sha256(payload).hexdigest())
        record["status"] = status
        record_row(record, status)

    if workers == 1:
        for target in pending:
            if state["stop"]:
                break
            process(target)
    else:
        print(f"using {workers} workers under one "
              f"{GLOBAL_RATE_LIMIT} rps global limiter")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(process, pending))

    handle.close()
    print("\nacquisition summary")
    span = 0.0
    if state["first_request_at"] and state["last_request_at"]:
        span = state["last_request_at"] - state["first_request_at"]
    realized = state["requested"] / span if span > 0 else 0.0
    print(f"  benchmark observations      {len(targets)}")
    print(f"  retrieval targets           {len(retrieval_targets)}")
    print(f"  configured global limit     {GLOBAL_RATE_LIMIT} rps "
          f"(cap {SEC_MAX_REQUESTS_PER_SECOND})")
    print(f"  measured realized rate      {realized:.3f} rps "
          f"over {span / 3600:.2f} h of requesting")
    print(f"  worker count                {workers}")
    print(f"  HTTP requests issued        {state['requested']}")
    print(f"  retry attempts              {state['retries']}")
    print("  HTTP status distribution")
    for label in sorted(http_status, key=lambda k: -http_status[k]):
        print(f"    {label:<40} {http_status[label]}")
    for status in (STATUS_OK, STATUS_PERMANENT, STATUS_RETRYABLE,
                   STATUS_MALFORMED, STATUS_NO_NAMED_DOCUMENT):
        print(f"  {status:<27} {counts[status]}")
    print(f"  manifest                    {MANIFEST}")
    print(f"  corpus                      {CORPUS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
