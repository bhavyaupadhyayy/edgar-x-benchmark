"""Offline checks on the acquisition layer.

None of this touches the network. It proves the failure modes behave, because
a download bug only shows up hours into a real run and by then the cache is
already polluted.

    python3 acquisition_test.py
"""

from __future__ import annotations

import tempfile
import zipfile
from http.client import IncompleteRead
from pathlib import Path

import prepare_gate1_data as prepare
import sec_download
from event_classification import Disposition, classify
from sec_download import (
    DownloadError,
    SecClient,
    validate_payload,
    validate_user_agent,
)


class _StubClient(SecClient):
    """SecClient with the network replaced by a scripted response."""

    def __init__(self, payload: bytes):
        self._payload = payload
        self._min_interval = 0.0
        self._last_request_at = 0.0
        self._user_agent = "test test@example.org"

    def fetch(self, url: str) -> bytes:
        validate_payload(self._payload)
        return self._payload


# urlopen is stubbed out, but SecClient.fetch builds a Request before calling
# it, and Request rejects a non-URL string. Never contacted.
FAKE_URL = "https://sec.gov.invalid/x.zip"


class _RaisingResponse:
    """urlopen result whose body read fails, as a truncated transfer does."""

    status = 200

    def __init__(self, error: Exception):
        self._error = error

    def __enter__(self) -> _RaisingResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        raise self._error


def check_user_agent() -> list[tuple[str, bool]]:
    return [
        ("empty User-Agent rejected", _rejects("")),
        ("User-Agent without an email rejected", _rejects("EDGAR-X Research")),
        ("placeholder email rejected",
         _rejects("EDGAR-X Research bhavya.upadhyay@example.com")),
        ("real contact accepted", not _rejects("EDGAR-X Research real@person.org")),
    ]


def check_download_validation() -> list[tuple[str, bool]]:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)

        html_error = b"<html><body>Page not found</body></html>" * 20
        checks.append(
            ("HTML served where a ZIP was expected is rejected",
             _raises(_StubClient(html_error), root / "a.zip", expect_zip=True))
        )
        checks.append(
            ("corrupt ZIP is rejected and not left on disk",
             _raises(_StubClient(b"PK\x03\x04" + b"garbage" * 60),
                     root / "b.zip", expect_zip=True)
             and not (root / "b.zip").exists())
        )
        checks.append(
            ("SEC throttle page is rejected",
             _raises(_StubClient(b"Request Rate Threshold Exceeded" + b" " * 500),
                     root / "c.txt"))
        )
        checks.append(
            ("short body is rejected as an error page",
             _raises(_StubClient(b"nope"), root / "d.txt"))
        )

        good = _zip_bytes()
        client = _StubClient(good)
        first = client.download_to("u", root / "e.zip", expect_zip=True)
        second = client.download_to("u", root / "e.zip", expect_zip=True)
        checks.append(("valid ZIP saved", first == "downloaded"))
        checks.append(("existing file is not re-downloaded", second == "cached"))
        checks.append(
            ("no .part files survive a successful run",
             not list(root.glob("*.part")))
        )
    return checks


def check_planning_and_extraction() -> list[tuple[str, bool]]:
    quarters = prepare.required_quarters(2012, 2024)
    text = prepare._to_text(
        b"<html><body><script>x</script><p>Item 1.03 Bankruptcy.</p>"
        b"<p>On June 19, 2024, the Registrant filed a voluntary petition under "
        b"chapter 11 in the United States Bankruptcy Court for the District of "
        b"Delaware. Case No. 24-11390.</p></body></html>"
    )
    classification = classify(text)
    return [
        ("52 DERA quarters planned for 2012-2024", len(quarters) == 52),
        ("quarter range endpoints correct",
         quarters[0] == "2012q1" and quarters[-1] == "2024q4"),
        ("block tags become line breaks so item headings survive",
         "\n" in text and text.startswith("Item 1.03")),
        ("stripped HTML still classifies end to end",
         classification.disposition is Disposition.REGISTRANT_CHAPTER_11
         and classification.docket == "24-11390"),
        ("missing DERA quarters are a blocker",
         any("DERA" in problem for problem in prepare._problems(quarters, 50, 500, 500, True))),
        ("implausibly few candidates is a blocker",
         any("candidates" in problem for problem in prepare._problems(quarters, 52, 5, 5, True))),
        ("low document success rate is a blocker",
         any("documents retrieved" in problem
             for problem in prepare._problems(quarters, 52, 1000, 500, True))),
        ("a missing submissions archive is a blocker",
         any("submissions archive" in problem
             for problem in prepare._problems(quarters, 52, 1000, 1000, False))),
        ("a complete run reports no blockers",
         not prepare._problems(quarters, 52, 1000, 1000, True)),
    ]


def check_transport_failures() -> list[tuple[str, bool]]:
    """A read-phase transport failure must become DownloadError, not escape.

    Regression test. The first real 52-quarter DERA acquisition died at quarter
    45 with an unhandled http.client.IncompleteRead: SEC closed the connection
    after 52.7 MB of a 113.9 MB body. IncompleteRead is an HTTPException, which
    subclasses neither URLError nor OSError, so it passed through both handlers
    in SecClient.fetch and killed the interpreter instead of being recorded as
    a failed target. A read-phase socket timeout surfaces as a bare
    TimeoutError and escaped the same way.

    These assert on the REAL fetch path with urlopen swapped out, not on a
    stubbed fetch -- stubbing fetch is exactly what hid the gap, since the
    existing _StubClient replaces the method under test.
    """
    checks: list[tuple[str, bool]] = []
    for label, error in (
        ("truncated body (IncompleteRead)", IncompleteRead(b"partial body", 999)),
        ("read timeout (TimeoutError)", TimeoutError("timed out")),
    ):
        original = sec_download.urlopen
        sec_download.urlopen = lambda *args, **kwargs: _RaisingResponse(error)  # noqa: B023
        try:
            client = SecClient("test test@example.org")
            client._min_interval = 0.0
            outcome = _fetch_outcome(client)
        finally:
            sec_download.urlopen = original
        checks.append((f"{label} becomes DownloadError", outcome == "DownloadError"))

    # The failure must stay recorded rather than aborting the caller's loop.
    original = sec_download.urlopen
    sec_download.urlopen = lambda *args, **kwargs: _RaisingResponse(
        IncompleteRead(b"partial body", 999)
    )
    try:
        stats = sec_download.DownloadStats()
        client = SecClient("test test@example.org")
        client._min_interval = 0.0
        with tempfile.TemporaryDirectory() as raw:
            try:
                client.download_to(FAKE_URL, Path(raw) / "q.zip", expect_zip=True)
            except DownloadError as error:
                stats.record_failure("dera/2023q1", str(error))
            survived = stats.failed == 1 and not list(Path(raw).glob("*"))
    finally:
        sec_download.urlopen = original
    checks.append(
        ("a truncated download is recorded and leaves no file behind", survived)
    )
    return checks


def _fetch_outcome(client: SecClient) -> str:
    """Name of what fetch raised, so an escape is distinguishable from a pass."""
    try:
        client.fetch(FAKE_URL)
    except DownloadError:
        return "DownloadError"
    except Exception as error:  # noqa: BLE001 - the escape we are testing for
        return type(error).__name__
    return "no error"


def _rejects(user_agent: str) -> bool:
    try:
        validate_user_agent(user_agent)
        return False
    except DownloadError:
        return True


def _raises(client: SecClient, destination: Path, expect_zip: bool = False) -> bool:
    try:
        client.download_to("u", destination, expect_zip=expect_zip)
        return False
    except DownloadError:
        return True


def _zip_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "tmp.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("sub.txt", "adsh\tsic\nx\t3711\n")
        return path.read_bytes()


def main() -> None:
    checks = (
        check_user_agent()
        + check_download_validation()
        + check_transport_failures()
        + check_planning_and_extraction()
    )
    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {label}")
    raise SystemExit(0 if all(passed for _, passed in checks) else 1)


if __name__ == "__main__":
    main()
