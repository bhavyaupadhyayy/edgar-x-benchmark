"""Rate-limited, validating, resumable HTTP client for SEC bulk sources.

Rules this enforces, because every one of them is a way a long download can
corrupt a run silently:

  - a descriptive User-Agent on every request; SEC rejects or throttles without
  - at most SEC_MAX_REQUESTS_PER_SECOND requests per second
  - responses are validated by content before being saved, so an SEC error page
    or rate-limit notice never lands on disk as if it were data
  - downloads write to a .part file and rename only on success, so an
    interrupted run leaves no half file that a later run would trust
  - a non-empty final file is never re-downloaded
  - empty payloads are a failure, never a saved empty file
"""

from __future__ import annotations

import time
import zipfile
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from constants import SEC_MAX_REQUESTS_PER_SECOND

ZIP_MAGIC = b"PK\x03\x04"
PLACEHOLDER_EMAIL = "bhavya.upadhyay@example.com"
PARTIAL_SUFFIX = ".part"

# Anything smaller than this is an error page or a truncated body, not a filing.
MIN_DOCUMENT_BYTES = 200

# Markers SEC returns when it throttles. These arrive with HTTP 200.
THROTTLE_MARKERS = (
    b"Your Request Originates from an Undeclared Automated Tool",
    b"Request Rate Threshold Exceeded",
)


class DownloadError(RuntimeError):
    """A download failed in a way that must not be treated as missing data."""


@dataclass
class DownloadStats:
    downloaded: int = 0
    cached: int = 0
    failed: int = 0
    failures: list[str] = None

    def __post_init__(self) -> None:
        self.failures = self.failures or []

    def record_failure(self, target: str, reason: str) -> None:
        self.failed += 1
        self.failures.append(f"{target}: {reason}")


class SecClient:
    """Throttled SEC fetcher with content validation and atomic caching."""

    def __init__(self, user_agent: str, requests_per_second: float = SEC_MAX_REQUESTS_PER_SECOND):
        validate_user_agent(user_agent)
        self._user_agent = user_agent
        self._min_interval = 1.0 / requests_per_second
        self._last_request_at = 0.0

    def fetch(self, url: str) -> bytes:
        """One validated request. Raises DownloadError on anything suspicious."""
        self._throttle()
        request = Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urlopen(request, timeout=120) as response:
                if response.status != 200:
                    raise DownloadError(f"HTTP {response.status}")
                payload = response.read()
        except HTTPError as error:
            raise DownloadError(f"HTTP {error.code}") from error
        except URLError as error:
            raise DownloadError(f"network error: {error.reason}") from error
        except (HTTPException, TimeoutError) as error:
            # Failures raised while READING the body rather than while opening
            # the connection. http.client.IncompleteRead is an HTTPException,
            # which subclasses neither URLError nor OSError, and a read-phase
            # socket timeout surfaces as a bare TimeoutError; both therefore
            # escaped the two handlers above and killed the interpreter instead
            # of being recorded as a failed target. On a 52-quarter run that
            # aborted the whole acquisition at quarter 45, and on the ~10-20k
            # document stage it would be near certain.
            #
            # Converting them here restores the module's contract: a bad fetch
            # is a recorded DownloadError, the caller keeps going, the summary
            # reports a blocker, and the next run resumes. No retry is added --
            # rerunning is this module's retry mechanism, and the atomic .part
            # rename means nothing partial is ever trusted.
            raise DownloadError(
                f"truncated or interrupted response: {type(error).__name__}"
            ) from error

        validate_payload(payload)
        return payload

    def download_to(self, url: str, destination: Path, expect_zip: bool = False) -> str:
        """Fetch to `destination` unless already cached. Returns the outcome.

        Outcome is "cached" or "downloaded"; failures raise.
        """
        if destination.exists() and destination.stat().st_size > 0:
            return "cached"

        payload = self.fetch(url)
        validate_payload(payload)
        if expect_zip and not payload.startswith(ZIP_MAGIC):
            raise DownloadError("response is not a ZIP archive")
        if not expect_zip and len(payload) < MIN_DOCUMENT_BYTES:
            raise DownloadError(f"body only {len(payload)} bytes, likely an error page")

        partial = destination.with_suffix(destination.suffix + PARTIAL_SUFFIX)
        partial.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(payload)

        if expect_zip and not _is_readable_zip(partial):
            partial.unlink()
            raise DownloadError("archive downloaded but is corrupt")

        partial.replace(destination)
        return "downloaded"

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()


def validate_payload(payload: bytes) -> None:
    """Reject bodies that are not content, whatever the HTTP status said.

    Lives outside SecClient.fetch on purpose: throttle notices arrive with
    HTTP 200, and any caller holding bytes must be able to run the same check
    without going through the network path.
    """
    if not payload:
        raise DownloadError("empty response body")
    for marker in THROTTLE_MARKERS:
        if marker in payload[:4096]:
            raise DownloadError("SEC throttle page returned instead of content")


def validate_user_agent(user_agent: str) -> None:
    """SEC requires a real contact address. Refuse to run without one."""
    if not user_agent or "@" not in user_agent:
        raise DownloadError(
            "SEC requires a User-Agent containing a real contact email. "
            "Pass --email you@domain.com"
        )
    if PLACEHOLDER_EMAIL in user_agent:
        raise DownloadError(
            "The placeholder email from constants.py is still in use. "
            "Pass --email with your real address."
        )


def _is_readable_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False
