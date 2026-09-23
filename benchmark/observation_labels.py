"""Labelling 10-K observations, and measuring event-to-observation multiplicity.

The benchmark's unit is a 10-K, not a bankruptcy. Every eligible 10-K gets its
own forward 365-day outcome, so one bankruptcy can label more than one
observation whenever two 10-K acceptances fall less than a horizon apart.

That is not a rare edge case, and the arithmetic says where it concentrates. A
duplicate appears when the bankruptcy lands in the gap between the second
filing and one horizon after the first, a window of width

    365 - (days between the two 10-K acceptances)

For a punctual annual filer the gap sits near 365 and the window is days wide.
For a delinquent filer catching up on two years of 10-Ks two months apart, the
gap is 60 and the window is 305 days wide, so duplication is close to certain.
Delinquent catch-up filing is concentrated in exactly the distressed population
that supplies the positive class, so multiplicity is correlated with the label
rather than spread evenly across the panel.

Consequences that must not be papered over:

  - Gate 1 has to report unique events AND positive observations. Selecting
    only the latest 10-K would let the power model quietly redefine the
    scientific target.
  - Duplicated positives are not independent. Inference must cluster by event,
    not only by CIK, and Gate 2 must deflate effective event count accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from filing_history import CompanyProfile, TenKFiling


@dataclass(frozen=True)
class EventLabelling:
    """Every 10-K observation that one bankruptcy event turns positive."""

    cik: int
    event_at: datetime
    labelled_filings: tuple[TenKFiling, ...]

    @property
    def multiplicity(self) -> int:
        return len(self.labelled_filings)

    @property
    def is_eligible(self) -> bool:
        return self.multiplicity > 0


def label_observations(
    profile: CompanyProfile, event_at: datetime, horizon_days: int
) -> EventLabelling:
    """All same-CIK 10-Ks whose forward horizon contains the event.

    Returns every match, not the latest. The count is the quantity Gate 1 must
    report alongside unique events.
    """
    window_start = event_at - timedelta(days=horizon_days)
    labelled = tuple(
        filing
        for filing in profile.tenk_filings
        if window_start < filing.accepted_at < event_at
    )
    return EventLabelling(
        cik=profile.cik, event_at=event_at, labelled_filings=labelled
    )


def summarize_multiplicity(labellings: list[EventLabelling]) -> dict[str, float]:
    """Distribution of positive observations per bankruptcy event."""
    eligible = [labelling for labelling in labellings if labelling.is_eligible]
    if not eligible:
        return {
            "unique_events": 0,
            "positive_observations": 0,
            "mean_multiplicity": 0.0,
            "duplicate_event_rate": 0.0,
        }

    multiplicities = [labelling.multiplicity for labelling in eligible]
    duplicated = sum(1 for count in multiplicities if count > 1)
    return {
        "unique_events": len(eligible),
        "positive_observations": sum(multiplicities),
        "mean_multiplicity": sum(multiplicities) / len(eligible),
        "duplicate_event_rate": duplicated / len(eligible),
    }

