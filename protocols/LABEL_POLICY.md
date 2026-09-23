# Label Policy

Frozen label semantics for the bankruptcy benchmark. Adopted 2026-09-14, before
the repair pass that follows the development audit. Classifier, date and
event-assembly code must implement these rules; where earlier code or comments
disagree, this document wins.

This file clarifies what the frozen methodology in `CLAUDE.md` and
`research/docs/PIT_CONTRACT.md` means in edge cases. It does not change the
cohorts, horizon, unit, FIRE/SIC rules or data sources.

## Positive event

1. **A positive event is an initial U.S. Chapter 7 or Chapter 11 petition by the
   same SEC CIK legal registrant.**
2. **Receivership alone is not a positive.**
3. **Foreign insolvency proceedings alone are not positives** (e.g. CCAA, BIA,
   UK administration, Dutch *surseance*, German *Insolvenz*).
4. **Prospective intent, authorization to file, preparation to file, and
   explicit negation such as "has not filed" are not positives.**

## Chapter

5. **A later Chapter 11 → Chapter 7 conversion is not a new bankruptcy event and
   does not change the benchmark's initial chapter.** A conversion may be kept
   as metadata only.
6. **A motion or intent to convert is never a Chapter 7 event.**

## Event time

7. **In an involuntary bankruptcy, canonical event time is the petition filing
   date, not the order-for-relief date.**
8. **Never use the 8-K/report date as a fallback petition date.**
9. **If the true petition date cannot be established, the event stays
   `event_date_unresolved`.**
10. **An 8-K/A that explicitly corrects the petition date overrides the earlier
    value for the same event.**

## Registrant identity

11. **CIK remains the legal-registrant unit.** A co-registrant is positive only if
    that exact registrant is explicitly named, or unambiguously included in the
    debtor definition. Otherwise the event is classified `ambiguous`.
    **No corporate parent–child resolution is added.**
