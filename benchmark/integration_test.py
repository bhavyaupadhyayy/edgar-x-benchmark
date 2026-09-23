"""End-to-end check that Gate 1 orchestrates every component it claims to.

Builds a tiny synthetic archive rather than mocking, so a component that is
written but never called fails here instead of after a multi-hour run.
"""

from __future__ import annotations

import inspect
import json
import tempfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

from bankruptcy_event import assemble_events
from dera_sic import build_sic_index
from event_classification import Classification, Disposition, classify, extract_item_section
from event_counts import build_gate_one
from filing_history import CompanyProfile, SubmissionsArchive
from submissions_scan import SubmissionsArchiveScanner

DELINQUENT_CIK = 111
FIRE_CIK = 222


def _submissions_payload(cik: int, sic: int, tenk_dates: list[str],
                         eightk: list[tuple[str, str, str]]) -> dict:
    """Mirrors the real archive layout, primaryDocument included."""
    forms = ["10-K"] * len(tenk_dates) + [form for form, _, _ in eightk]
    accessions = [f"{cik}-10K-{i}" for i in range(len(tenk_dates))] + [
        accession for _, accession, _ in eightk
    ]
    accepted = tenk_dates + [stamp for _, _, stamp in eightk]
    return {
        "cik": str(cik),
        "sic": str(sic),
        "entityType": "operating",
        "filings": {
            "recent": {
                "form": forms,
                "accessionNumber": accessions,
                "acceptanceDateTime": accepted,
                "filingDate": [stamp[:10] for stamp in accepted],
                "items": ["" for _ in tenk_dates] + ["1.03" for _ in eightk],
                "primaryDocument": ["tenk.htm" for _ in tenk_dates]
                + [f"{accession}.htm" for _, accession, _ in eightk],
            },
            "files": [],
        },
    }


def build_fixture(root: Path) -> tuple[Path, Path, Path]:
    submissions = root / "submissions.zip"
    with zipfile.ZipFile(submissions, "w") as archive:
        # Delinquent catch-up filer: two 10-Ks two months apart, then Chapter 11.
        archive.writestr(
            f"CIK{DELINQUENT_CIK:010d}.json",
            json.dumps(
                _submissions_payload(
                    DELINQUENT_CIK, 3711,
                    ["2019-01-15T08:00:00.000Z", "2019-03-20T08:00:00.000Z"],
                    [("8-K", "111-8K-0", "2019-09-10T08:00:00.000Z"),
                     ("8-K/A", "111-8K-1", "2019-10-01T08:00:00.000Z")],
                )
            ),
        )
        # FIRE filer that must be excluded by SIC as filed.
        archive.writestr(
            f"CIK{FIRE_CIK:010d}.json",
            json.dumps(
                _submissions_payload(
                    FIRE_CIK, 6021, ["2019-02-01T08:00:00.000Z"],
                    [("8-K", "222-8K-0", "2019-06-10T08:00:00.000Z")],
                )
            ),
        )

    documents = root / "docs"
    documents.mkdir()
    # The case amendment merging exists for: the original announces the
    # bankruptcy with NO petition date and NO docket, and the /A supplies both.
    # Identity-based matching cannot link these, because the original has no
    # identity yet.
    (documents / "111-8K-0.txt").write_text(
        "Item 1.03 Bankruptcy or Receivership.\nThe Registrant filed a voluntary "
        "petition for relief under chapter 11 of the Bankruptcy Code."
    )
    (documents / "111-8K-1.txt").write_text(
        "Item 1.03 Bankruptcy or Receivership.\nOn September 1, 2019, the "
        "Registrant filed a voluntary petition for relief under chapter 11 in the "
        "United States Bankruptcy Court for the District of Delaware. "
        "Case No. 19-12345."
    )
    (documents / "222-8K-0.txt").write_text(
        "Item 1.03 Bankruptcy or Receivership.\nOn June 1, 2019, the Registrant "
        "filed a voluntary petition under chapter 11 in the United States "
        "Bankruptcy Court for the District of Delaware."
    )

    dera = root / "dera"
    dera.mkdir()
    with zipfile.ZipFile(dera / "2019q1.zip", "w") as archive:
        rows = ["adsh\tsic"]
        rows += [f"{DELINQUENT_CIK}-10K-{i}\t3711" for i in range(2)]
        rows.append(f"{FIRE_CIK}-10K-0\t6021")
        archive.writestr("sub.txt", "\n".join(rows))

    return submissions, documents, dera


def _candidate_urls_resolve() -> list[bool]:
    """Every Item 1.03 candidate must yield a fetchable primary-document URL.

    A candidate with no URL cannot be classified, so this is a Gate 1 blocker
    rather than a cosmetic gap.
    """
    from submissions_scan import BankruptcyCandidate

    candidate = BankruptcyCandidate(
        cik=111, accession="111-8K-0", accepted_at=datetime(2019, 9, 10),
        form="8-K", primary_document="111-8K-0.htm",
    )
    missing = BankruptcyCandidate(
        cik=111, accession="x", accepted_at=datetime(2019, 9, 10), form="8-K",
    )
    return [
        candidate.document_url is not None,
        candidate.document_url.endswith("/111-8K-0.htm"),
        missing.document_url is None,
    ]


def check_merge_guards() -> list[tuple[str, bool]]:
    """Negative guards: a merge rule that never refuses is worse than no rule.

    The amendment window is 120 days, so these three cases pin down that the
    window is reachable only by an actual /A filing. Without them a later
    loosening of `_amends` would pass every positive assertion in this file.
    """
    chapter_11 = classify(
        "Item 1.03\nOn March 2, 2015, the Registrant filed a voluntary petition "
        "under chapter 11. Case No. 15-10001."
    )
    chapter_7 = classify(
        "Item 1.03\nOn May 4, 2015, the Registrant filed a voluntary petition "
        "under chapter 7. Case No. 15-20002."
    )
    undated = classify(
        "Item 1.03\nThe Registrant filed a voluntary petition under chapter 11."
    )

    distinct = assemble_events(
        1,
        [("a", datetime(2015, 3, 4), chapter_11, False),
         ("b", datetime(2015, 5, 6), chapter_7, False)],
    )
    not_absorbed = assemble_events(
        2,
        [("a", datetime(2015, 3, 4), chapter_11, False),
         ("b", datetime(2015, 3, 20), undated, False)],
    )
    absorbed = assemble_events(
        3,
        [("a", datetime(2015, 3, 4), undated, False),
         ("b", datetime(2015, 3, 20), chapter_11, True)],
    )

    return [
        ("two genuine bankruptcies stay two events", len(distinct) == 2),
        ("ordinary undated 8-K is not absorbed by proximity",
         len(not_absorbed) == 2),
        ("an /A at the same gap IS absorbed", len(absorbed) == 1),
    ]


def check_classifier_regressions() -> list[tuple[str, bool]]:
    """The three defects the first real Gate 1 run exposed, each pinned here.

    All three were found by reading actual filings out of the corpus, not by
    reasoning about the rules, and every case below is the real text.
    """
    def disp(text: str) -> Disposition:
        return classify(text).disposition

    # --- 1. Item title contamination ------------------------------------
    # "Bankruptcy or Receivership" is Form 8-K's NAME for item 1.03. It sat
    # inside the classified section, so RECEIVERSHIP matched on essentially
    # every filing and won whenever no chapter was named. 910 of 1,094
    # no-chapter filings had no "receiver*" anywhere but that title.
    title_only = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On May 1, 2020, the Court entered an order confirming the Plan."
    )
    # Fairchild Corporation, CIK 9779: a real registrant chapter 11 that never
    # writes the string "chapter 11", so it was filed away as a receivership.
    fairchild = (
        "Item 1.03 Bankruptcy or Receivership\n"
        "On March 18, 2009, The Fairchild Corporation (the \"Company\") and "
        "sixty-one of its consolidated subsidiaries filed voluntary petitions "
        "in the United States Bankruptcy Court for the District of Delaware "
        "for reorganization of its business."
    )
    # A genuine receivership must still be detected from the BODY.
    real_receivership = (
        "Item 1.03 Bankruptcy or Receivership\n"
        "On March 2, 2015, the Federal Deposit Insurance Corporation was "
        "appointed receiver of the Bank."
    )

    # --- 2. Legal-abbreviation punctuation -------------------------------
    # Stage Stores, CIK 6885. "Specialty Retailers, Inc." put a full stop
    # between the subject and the verb, so the [^.]{0,120} subject-verb bound
    # could not span it and a plain registrant chapter 11 became AMBIGUOUS.
    stage_stores = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On May 10, 2020, Stage Stores, Inc. (the \"Company\") and Specialty "
        "Retailers, Inc. (collectively, the \"Debtors\") filed voluntary "
        "petitions for reorganization under Chapter 11 of the United States "
        "Bankruptcy Code in the United States Bankruptcy Court for the "
        "Southern District of Texas."
    )
    # The bound must still refuse to cross a REAL sentence boundary. Without
    # this, normalising abbreviations would slide into making the rule
    # globally permissive, matching a registrant in one sentence against a
    # subsidiary's petition in the next.
    across_sentences = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "The Company announced its quarterly results. A lender filed a "
        "voluntary petition under chapter 11 against an unrelated party."
    )

    # --- 3. Subsidiary-as-debtor apposition ------------------------------
    # Adams Resources, CIK 2178, which reached the usable set as a registrant
    # chapter 11. The debtor is the SUBSIDIARY; the parent's defined term
    # ("the Company") merely sits between the real subject and the verb.
    adams = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On April 21, 2017, Adams Resources Exploration Corporation (\"AREC\"), "
        "a wholly owned subsidiary of Adams Resources & Energy, Inc. (the "
        "\"Company\"), filed a petition under Chapter 11 of the United States "
        "Bankruptcy Code in the United States Bankruptcy Court for the "
        "District of Delaware."
    )
    # The registrant explicitly among the debtors stays positive even though
    # the same apposition appears. Without this the fix would suppress real
    # positives instead of correcting one.
    registrant_among_debtors = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On June 2, 2019, the Company and certain of its subsidiaries, "
        "including Acme Holdings, a wholly owned subsidiary of the Company, "
        "filed voluntary petitions under chapter 11."
    )
    # An apposition in a LATER sentence must not suppress a genuine positive:
    # the registrant filed, and some unrelated subsidiary is mentioned after.
    apposition_later_sentence = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On July 11, 2005, Pharmaceutical Formulations, Inc., referred to herein "
        "as the Debtor or the Company, filed a voluntary petition under chapter "
        "11 in the United States Bankruptcy Court for the District of Delaware. "
        "The case relates to business conducted by Konsyl Pharmaceuticals, Inc., "
        "a subsidiary of the Company."
    )
    # An unambiguous subsidiary-only filing must NOT drift into ambiguous.
    subsidiary_only = (
        "Item 1.03 Bankruptcy or Receivership.\n"
        "On October 19, 2011, certain of its wholly-owned subsidiaries filed "
        "voluntary petitions for relief under Chapter 11 of the Bankruptcy Code."
    )

    return [
        ("item title alone does not make a filing a receivership",
         disp(title_only) is not Disposition.RECEIVERSHIP_ONLY),
        ("no-chapter, no-receivership filing is ambiguous",
         disp(title_only) is Disposition.AMBIGUOUS),
        ("registrant petition without the literal chapter string is not a receivership",
         disp(fairchild) is not Disposition.RECEIVERSHIP_ONLY),
        ("a receivership named in the BODY is still detected",
         disp(real_receivership) is Disposition.RECEIVERSHIP_ONLY),
        ("the stripped title is absent from the classified text",
         "Receivership" not in extract_item_section(title_only, "1.03")),

        ("'Inc.' between subject and verb no longer blocks the match",
         disp(stage_stores) is Disposition.REGISTRANT_CHAPTER_11),
        ("the subject-verb bound still refuses to cross a sentence boundary",
         disp(across_sentences) is not Disposition.REGISTRANT_CHAPTER_11),
        ("abbreviation normalisation preserves the docket",
         classify(stage_stores).petition_date is not None),

        ("subsidiary-as-debtor is not a registrant positive",
         not disp(adams).is_positive),
        ("unresolved debtor identity lands in ambiguous",
         disp(adams) is Disposition.AMBIGUOUS),
        ("registrant explicitly among the debtors stays positive",
         disp(registrant_among_debtors) is Disposition.REGISTRANT_CHAPTER_11),
        ("an apposition in a later sentence does not suppress a real positive",
         disp(apposition_later_sentence) is Disposition.REGISTRANT_CHAPTER_11),
        ("an unambiguous subsidiary-only filing stays subsidiary-only",
         disp(subsidiary_only) is Disposition.SUBSIDIARY_ONLY),
    ]


def _evaluate(cases: list[tuple[str, object]]) -> list[tuple[str, bool]]:
    """Run (label, zero-argument check) pairs; an exception is a failure.

    Keeping each check lazy lets the same fixtures run against older code, where
    a missing attribute must count as a failure rather than abort the suite.
    """
    results = []
    for label, check in cases:
        try:
            results.append((label, bool(check())))
        except Exception as error:  # noqa: BLE001 - reported as a failed check
            results.append((f"{label} [{type(error).__name__}]", False))
    return results


def check_stage1_section_extraction() -> list[tuple[str, object]]:
    """Repair stage 1: select the substantive Item 1.03 body; title variants.

    Shapes taken from development filings: an index stub before the real section
    (CanArgo, CalGen), pre-2004 "Item 3" numbering (Rotate Black), no Item 1.03
    heading at all (Fearless), and heading variants seen in the corpus.
    """
    canargo = (
        "Item 1.03 Bankruptcy or Receivership\n SIGNATURES\nTable of Contents\n"
        "This Current Report may contain forward-looking statements, including the "
        "effects of the Chapter 11 filing on the Company.\n"
        "Item 1.03\nBankruptcy or Receivership.\nAs previously disclosed, on October "
        "28, 2009 the Company filed a voluntary petition seeking relief under "
        "Chapter 11 of the United States Bankruptcy Code.\n"
    )
    calgen = (
        "Item 1.03. Bankruptcy or Receivership.\nItem 2.04. Triggering Events.\n"
        "Item 9.01. Financial Statements and Exhibits.\n"
        "Item 1.03. Bankruptcy or Receivership.\n(a) On December 20, 2005, Calpine "
        "Corporation and certain of its subsidiaries filed voluntary petitions for "
        "reorganization under Chapter 11 of the United States Bankruptcy Code.\n"
        "Item 2.04. Triggering Events.\nThe filing accelerated certain obligations.\n"
    )
    rotate_black = (
        "FORM 8-K CURRENT REPORT ROTATEBLACK, INC. cover page text.\n"
        "ITEM\n 3. Bankruptcy or Receivership.\nOn May 6, 2004, the Court granted a "
        "motion by Bevsystems International, Inc. (the \"Company\") to convert the "
        "Chapter 7 bankruptcy proceeding filed against the Company on March 31, 2004 "
        "to a Chapter 11 bankruptcy proceeding.\n"
        "ITEM 5.01 Changes in Control of Registrant.\nUnrelated governance text.\n"
    )
    fearless = (
        "FORM 8-K\nITEM 3.02 UNREGISTERED SALES OF EQUITY SECURITIES\nSee Item 8.01.\n"
        "ITEM 8.01 OTHER EVENTS\nOn July 23, 2008 the Company filed for bankruptcy "
        "protection under Chapter 11 of the bankruptcy code.\n"
    )
    # Fallback must stay conservative: a registrant verb and a chapter reference
    # in DIFFERENT sentences of other items are not a registrant bankruptcy.
    weak_fallback = (
        "FORM 8-K\nITEM 8.01 OTHER EVENTS\nThe Company filed a petition to intervene "
        "in a supplier proceeding. Separately, that supplier remains in Chapter 11 "
        "and a receiver was appointed for one of its lenders.\n"
    )
    plural_title = (
        "Item 1.03 BANKRUPTCIES OR RECEIVERSHIP\nOn June 1, 2020, the Court entered "
        "an order confirming the Plan.\n"
    )
    of_typo_stub = "Item 1.03 Bankruptcy of Receivership.\nItem 9.01 Exhibits.\n"
    and_title = (
        "Item 1.03 Bankruptcy and Receivership.\nOn June 1, 2020, the Court entered "
        "an order confirming the Plan.\n"
    )

    def section(text: str) -> str:
        return " ".join(extract_item_section(text, "1.03").split())

    return [
        ("CanArgo: index stub skipped, dated body extracted",
         lambda: "filed a voluntary petition" in section(canargo)
         and "forward-looking" not in section(canargo)),
        ("CanArgo: petition date recovered from the real section",
         lambda: classify(canargo).petition_date == datetime(2009, 10, 28).date()),
        ("CalGen: '. .' index stub skipped",
         lambda: "On December 20, 2005" in section(calgen)),
        ("CalGen: section ends at the next item heading",
         lambda: "accelerated" not in section(calgen)),
        ("Rotate Black: legacy 'ITEM 3' heading recognised",
         lambda: "filed against the Company on March 31, 2004" in section(rotate_black)
         and "cover page" not in section(rotate_black)),
        ("Rotate Black: legacy section excludes the following item",
         lambda: "governance" not in section(rotate_black)),
        ("Fearless: no Item 1.03 body -> the Item 8.01 statement is reachable",
         lambda: "filed for bankruptcy protection under Chapter 11" in section(fearless)),
        ("fallback is conservative: split-sentence evidence is not a positive",
         lambda: not classify(weak_fallback).disposition.is_positive),
        ("fallback never yields receivership-only",
         lambda: classify(weak_fallback).disposition is not Disposition.RECEIVERSHIP_ONLY),
        ("plural title 'BANKRUPTCIES OR RECEIVERSHIP' is not receivership evidence",
         lambda: classify(plural_title).disposition is Disposition.AMBIGUOUS),
        ("'Bankruptcy of Receivership' stub is not receivership evidence",
         lambda: classify(of_typo_stub).disposition is not Disposition.RECEIVERSHIP_ONLY),
        ("'Bankruptcy and Receivership' title is not receivership evidence",
         lambda: classify(and_title).disposition is Disposition.AMBIGUOUS),
    ]


def check_stage2_amendment_correction() -> list[tuple[str, object]]:
    """Repair stage 2: an explicit 8-K/A date correction overrides (LABEL_POLICY 10).

    Proxim's amendment corrects the petition YEAR in an explanatory note placed
    before Item 1.03; Brooke Capital's states it was filed to correct the dates.
    The guards pin that nothing weaker overrides an established date.
    """
    proxim_original = (
        "Item 1.03 Bankruptcy or Receivership.\nOn June 11, 2004, the Company and "
        "certain of its subsidiaries each filed voluntary petitions for relief under "
        "Chapter 11 of the United States Bankruptcy Code.\n"
    )
    proxim_amendment = (
        "EXPLANATORY NOTE The Company amends its Current Report on Form 8-K in order "
        "to correct a scrivener's error in Item 1.03. The date on which the Company "
        "filed voluntary petitions under Chapter 11 was June 11, 2005, not June 11, "
        "2004 as originally disclosed.\nItem 1.03 Bankruptcy or Receivership.\n"
        "On June 11, 2005, the Company and certain of its subsidiaries each filed "
        "voluntary petitions for relief under Chapter 11 of the United States "
        "Bankruptcy Code.\n"
    )
    brooke_original = (
        "Item 1.03 Bankruptcy or Receivership.\nOn October 27, 2008, the Company and "
        "its majority parent filed petitions for protection under Chapter 11 of the "
        "Bankruptcy Code.\n"
    )
    brooke_amendment = (
        "Item 1.03 Bankruptcy or Receivership.\nThis Form 8-K/A amends the Form 8-K "
        "filed by the Company on October 29, 2008. This amended Form 8-K correctly "
        "states the dates of the "
        "bankruptcy filing and does not otherwise change the disclosure. On October "
        "28, 2008, the Company and its majority parent filed petitions for protection "
        "under Chapter 11 of the Bankruptcy Code.\n"
    )
    silent_amendment = (
        "Item 1.03 Bankruptcy or Receivership.\nOn October 28, 2008, the Company and "
        "its majority parent filed petitions for protection under Chapter 11 of the "
        "Bankruptcy Code. Management believes this report is correct and complete.\n"
    )

    def one_event(original: str, later: str, later_is_amendment: bool) -> list:
        return assemble_events(
            9,
            [("orig", datetime(2008, 10, 29), classify(original), False),
             ("later", datetime(2008, 10, 30), classify(later), later_is_amendment)],
        )

    return [
        ("Proxim: /A correcting the petition year merges into one event",
         lambda: len(one_event(proxim_original, proxim_amendment, True)) == 1),
        ("Proxim: corrected date 2005-06-11 replaces the original 2004-06-11",
         lambda: one_event(proxim_original, proxim_amendment, True)[0].petition_date
         == datetime(2005, 6, 11).date()),
        ("Brooke Capital: corrected date 2008-10-28 replaces 2008-10-27",
         lambda: one_event(brooke_original, brooke_amendment, True)[0].petition_date
         == datetime(2008, 10, 28).date()),
        ("Brooke Capital: the amended report's own date is never taken as the petition date",
         lambda: one_event(brooke_original, brooke_amendment, True)[0].petition_date
         != datetime(2008, 10, 29).date()),
        ("guard: an /A without correction wording does not override the date",
         lambda: one_event(brooke_original, silent_amendment, True)[0].petition_date
         == datetime(2008, 10, 27).date()),
        ("guard: an ordinary 8-K with correction wording does not override the date",
         lambda: one_event(brooke_original, brooke_amendment, False)[0].petition_date
         == datetime(2008, 10, 27).date()),
    ]


def check_stage3_chapter_and_identity() -> list[tuple[str, object]]:
    """Repair stage 3: initial-petition chapter (B) and cross-chapter identity (C-i).

    Shapes from development filings: DIP events-of-default and risk boilerplate
    (Rite Aid, Bird Global, Rowe), a subsidiary's involuntary Chapter 7 beside the
    registrant's Chapter 11 (South Texas Oil), a pending conversion motion
    (Benson Hill), and the duplicate events those produced (Benson Hill, CBL).
    """
    ch11 = Disposition.REGISTRANT_CHAPTER_11
    ch7 = Disposition.REGISTRANT_CHAPTER_7

    dip_default = (
        "Item 1.03 Bankruptcy or Receivership.\nOn December 20, 2023, the Company and "
        "certain of its subsidiaries filed voluntary petitions under chapter 11 of the "
        "Bankruptcy Code. The DIP facility contains events of default, including the "
        "conversion of any of the Chapter 11 Cases to a case under chapter 7.\n"
    )
    risk_boilerplate = (
        "Item 1.03 Bankruptcy or Receivership.\nOn September 18, 2006, the Company "
        "filed a voluntary petition for reorganization under Chapter 11 of the "
        "Bankruptcy Code. Risks include motions for the appointment of a trustee or to "
        "convert the cases to Chapter 7 cases.\n"
    )
    subsidiary_chapter_7 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn October 29, 2009, the Registrant "
        "filed a voluntary petition for relief under chapter 11 of the Bankruptcy "
        "Code. Separately, creditors of STO Operating Company, a wholly owned "
        "subsidiary of the Registrant, filed an involuntary petition pursuant to "
        "Chapter 7.\n"
    )
    conversion_motion = (
        "Item 1.03 Bankruptcy or Receivership.\nAs previously disclosed, on March 20, "
        "2025, the Company filed voluntary petitions for relief under chapter 11 of "
        "the Bankruptcy Code. The Debtors filed a motion seeking to convert the "
        "Chapter 11 Cases into Chapter 7 Cases. If the motion is approved, the cases "
        "will be converted to Chapter 7.\n"
    )
    genuine_chapter_7 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn July 2, 2024, the Company filed a "
        "voluntary petition for relief under Chapter 7 of the Bankruptcy Code. A "
        "Chapter 7 trustee will be appointed and may liquidate the assets.\n"
    )
    converted_11_to_7 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn June 18, 2020 the Company filed a "
        "voluntary petition for reorganization under Chapter 11 of the Bankruptcy "
        "Code. On January 21, 2021, the Bankruptcy Court converted the Chapter 11 "
        "case to a Chapter 7 liquidation.\n"
    )
    converted_7_to_11 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn March 31, 2004, the Company filed a "
        "voluntary petition under Chapter 7 of the Bankruptcy Code. On May 6, 2004, "
        "the Court granted the Company's motion to convert its Chapter 7 case to a "
        "case under Chapter 11.\n"
    )
    hypothetical_only = (
        "Item 1.03 Bankruptcy or Receivership.\nThe Company filed a voluntary "
        "petition. If the case is converted to chapter 7, a trustee would be "
        "appointed.\n"
    )
    benson_original = (
        "Item 1.03 Bankruptcy or Receivership.\nOn March 20, 2025, the Company filed "
        "voluntary petitions for relief under chapter 11 of the Bankruptcy Code.\n"
    )
    cbl_original = (
        "Item 1.03 Bankruptcy or Receivership.\nOn November 1, 2020, the Company filed "
        "voluntary petitions under Chapter 11 of the Bankruptcy Code.\n"
    )
    cbl_later = (
        "Item 1.03 Bankruptcy or Receivership.\nOn November 1, 2020, the Company filed "
        "voluntary petitions under Chapter 11 of the Bankruptcy Code. Events of "
        "default include the conversion of the Chapter 11 Cases to cases under "
        "chapter 7. Case No. 20-35226.\n"
    )
    nevada_11 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn June 18, 2020, the Registrant filed "
        "a voluntary petition under Chapter 11 in the United States Bankruptcy Court "
        "for the District of Nevada.\n"
    )
    nevada_7_same_day = (
        "Item 1.03 Bankruptcy or Receivership.\nOn June 18, 2020, the Registrant filed "
        "a voluntary petition under Chapter 7 in the United States Bankruptcy Court "
        "for the District of Nevada.\n"
    )
    delaware_11 = (
        "Item 1.03 Bankruptcy or Receivership.\nOn March 2, 2015, the Registrant filed "
        "a voluntary petition under Chapter 11 in the United States Bankruptcy Court "
        "for the District of Delaware.\n"
    )
    delaware_7_next_day = (
        "Item 1.03 Bankruptcy or Receivership.\nOn March 3, 2015, the Registrant filed "
        "a voluntary petition under Chapter 7 in the United States Bankruptcy Court "
        "for the District of Delaware.\n"
    )
    oregon_7_same_day = (
        "Item 1.03 Bankruptcy or Receivership.\nOn June 18, 2020, the Registrant filed "
        "a voluntary petition under Chapter 7 in the United States Bankruptcy Court "
        "for the District of Oregon.\n"
    )

    def disp(text: str) -> Disposition:
        return classify(text).disposition

    def pair(first: str, second: str) -> list:
        return assemble_events(
            5,
            [("first", datetime(2020, 1, 1), classify(first), False),
             ("second", datetime(2020, 6, 1), classify(second), False)],
        )

    return [
        ("DIP events-of-default Chapter 7 does not override Chapter 11",
         lambda: disp(dip_default) is ch11),
        ("risk/exclusivity Chapter 7 boilerplate does not override Chapter 11",
         lambda: disp(risk_boilerplate) is ch11),
        ("a subsidiary's Chapter 7 does not override the registrant's Chapter 11",
         lambda: disp(subsidiary_chapter_7) is ch11),
        ("a pending conversion motion is never a Chapter 7 event",
         lambda: disp(conversion_motion) is ch11),
        ("an actual 11->7 conversion keeps the initial Chapter 11",
         lambda: disp(converted_11_to_7) is ch11),
        ("a Chapter 7 mentioned only as a conversion target is not a positive",
         lambda: not disp(hypothetical_only).is_positive),
        ("guard: a genuine Chapter 7 petition stays Chapter 7",
         lambda: disp(genuine_chapter_7) is ch7),
        ("guard: a 7->11 conversion keeps the initial Chapter 7",
         lambda: disp(converted_7_to_11) is ch7),
        ("Benson Hill: petition and conversion-motion filings are ONE event",
         lambda: len(pair(benson_original, conversion_motion)) == 1),
        ("Benson Hill: that event stays Chapter 11",
         lambda: pair(benson_original, conversion_motion)[0].disposition is ch11),
        ("CBL: boilerplate-Chapter-7 filing merges with the Chapter 11 event",
         lambda: len(pair(cbl_original, cbl_later)) == 1),
        ("cross-chapter records merge on exact date plus same court",
         lambda: len(pair(nevada_11, nevada_7_same_day)) == 1),
        ("guard: cross-chapter records one day apart are NOT merged by tolerance",
         lambda: len(pair(delaware_11, delaware_7_next_day)) == 2),
        ("guard: cross-chapter records on the same date in different courts stay apart",
         lambda: len(pair(nevada_11, oregon_7_same_day)) == 2),
    ]


def check_stage4_petition_dates() -> list[tuple[str, object]]:
    """Repair stage 4: petition dates ranked by their tie to the filing (mechanism D).

    Shapes are taken from development filings. The formats (weekday, ordinal,
    day-first, "Effective", compound, missing space or comma, a Petition Date
    defined in another item) used to be unparseable; the referent cases (prior
    8-K date, plan filing, board vote, dismissal petition, conversion order,
    order for relief) used to take whichever date came first.
    """
    head = "Item 1.03 Bankruptcy or Receivership.\n"

    def petition_date(text: str) -> object:
        return classify(text).petition_date

    def day(year: int, month: int, dom: int) -> object:
        return datetime(year, month, dom).date()

    leiner = head + (
        "On Monday, March 10, 2008, Leiner Health Products Inc. (the “Company”) "
        "filed a voluntary petition under Chapter 11 of the United States Bankruptcy Code."
    )
    china_ivy = head + (
        "On March 25th, 2005 two of the Company's note holders filed an involuntary "
        "petition against the Company under Title 11 of the United States Code, Chapter 7."
    )
    vision = head + (
        "On 24 September 2014 Vision Industries Corp. (the “Company”) filed a "
        "voluntary petition, Case No. 2:14-bk-28225, seeking relief under Chapter 11."
    )
    tootie_pie = head + (
        "Effective July 3, 2013, Tootie Pie Company, Incorporated (the “Company”) "
        "filed a Chapter 11 Bankruptcy Petition in the United States Bankruptcy Court."
    )
    meruelo = head + (
        "On March 26 and 27, 2009, Meruelo Maddux Properties, Inc. and certain of its "
        "subsidiaries (collectively, the “Company”) filed voluntary petitions for "
        "relief under Chapter 11 of the United States Bankruptcy Code."
    )
    hraa = head + (
        "On August11, 2014 (the “Petition Date”), the Company filed a voluntary "
        "petition seeking relief under Chapter 11 of the United States Bankruptcy Code."
    )
    wyndstorm = head + (
        "Bankruptcy On October 7 2011 registrant filed for chapter 7 bankruptcy at the "
        "United States Bankruptcy Court for the District of Columbia."
    )
    avaya = (
        "Item 1.01 Entry into a Material Definitive Agreement.\nThe forbearance ends "
        "eight business days after January 19, 2017. On January 19, 2017 (the "
        "“Petition Date”), the Company entered into a forbearance agreement.\n"
        + head + "On the Petition Date, the Company, together with certain of its "
        "affiliates, filed voluntary petitions for relief under chapter 11 of title 11."
    )
    qvc = head + (
        "As previously disclosed in the Current Report on Form 8-K filed by QVC, Inc. "
        "(the “Company”) on April 17, 2026, on April 16, 2026 (the “Petition "
        "Date”), the Company filed voluntary petitions for relief under chapter 11."
    )
    rancher_plan = head + (
        "On December 13, 2010, the Company filed with the Court its proposed Debtor's "
        "First Amended Plan of Reorganization in its Chapter 11 case."
    )
    spindle = head + (
        "On March 21, 2019, the Board of Directors of Spindle, Inc. (the “Company”) "
        "voted to authorize Management to file a petition for relief under Chapter 7. "
        "On March 22, 2019, the Company filed a petition for relief under Chapter 7 of "
        "the United States Bankruptcy Code."
    )
    ensurge = head + (
        "On March 21, 2005, Ensurge, Inc. (“the Company”) filed a petition with the "
        "Bankruptcy Court in the District of Nevada to voluntarily dismiss the Chapter 11 "
        "bankruptcy filed in September 2004."
    )
    wave = head + (
        "On May 16, 2016, the Bankruptcy Court entered an order converting the Chapter 7 "
        "Case of the Company to a case under Chapter 11."
    )
    midgard = head + (
        "In connection with the previously reported involuntary petition under Chapter 7 "
        "against MidgardXXI, Inc. (the \"Company\") filed by a former landlord, an order "
        "for relief was entered on January 30, 2007."
    )
    rotate_black = head + (
        "On May 6, 2004, the Bankruptcy Court granted a motion by the Company to convert "
        "the Chapter 7 bankruptcy proceeding filed against the Company on March 31, 2004 "
        "to a Chapter 11 bankruptcy proceeding."
    )
    heartland = head + (
        "Heartland Partners, L.P. (the \"Company\") and its affiliates have filed voluntary "
        "petitions under the provisions of chapter 11 of the United States Bankruptcy Code."
    )
    prior_report = head + (
        "As previously reported on our Current Report on Form 8-K filed on November 12, "
        "2024, the Company filed a voluntary petition under Chapter 11."
    )
    spirit = head + (
        "As previously disclosed, on November 18, 2024, Spirit Airlines, Inc. (the "
        "“Company”), and subsequently on November 25, 2024, its subsidiaries, "
        "filed voluntary petitions under chapter 11 of the Bankruptcy Code."
    )
    abitibi = head + (
        "On April 16, 2009, AbitibiBowater and certain of its subsidiaries filed voluntary "
        "petitions for relief under Chapter 11. On April 17, 2009, Abitibi-Consolidated "
        "Company of Canada filed a voluntary petition under Chapter 15 to obtain "
        "recognition of the CCAA Proceedings."
    )
    jennifer = head + (
        "As previously disclosed, on July 18, 2010, Jennifer Convertibles, Inc. and all of "
        "its affiliated debtors (the “Company”) filed voluntary petitions for "
        "bankruptcy relief under Chapter 11."
    )
    garrett_plan = head + (
        "On April 20, 2021, the Company filed an amended Chapter 11 plan of reorganization "
        "with the Bankruptcy Court."
    )

    return [
        ("weekday prefix: Leiner 2008-03-10", lambda: petition_date(leiner) == day(2008, 3, 10)),
        ("ordinal involuntary: China Ivy 2005-03-25",
         lambda: petition_date(china_ivy) == day(2005, 3, 25)),
        ("day-first: Vision 2014-09-24", lambda: petition_date(vision) == day(2014, 9, 24)),
        ("'Effective <date>': Tootie Pie 2013-07-03",
         lambda: petition_date(tootie_pie) == day(2013, 7, 3)),
        ("compound 'March 26 and 27': Meruelo Maddux takes the earlier day",
         lambda: petition_date(meruelo) == day(2009, 3, 26)),
        ("missing space 'August11': HRAA 2014-08-11",
         lambda: petition_date(hraa) == day(2014, 8, 11)),
        ("missing comma: Wyndstorm 2011-10-07",
         lambda: petition_date(wyndstorm) == day(2011, 10, 7)),
        ("Petition Date defined in another item: Avaya 2017-01-19",
         lambda: petition_date(avaya) == day(2017, 1, 19)),
        ("QVC: labelled Petition Date beats the prior 8-K's date",
         lambda: petition_date(qvc) == day(2026, 4, 16)),
        ("Rancher: a plan-filing date is not a petition date",
         lambda: petition_date(rancher_plan) is None),
        ("Spindle: the board-vote date is skipped for the filing date",
         lambda: petition_date(spindle) == day(2019, 3, 22)),
        ("Ensurge: a petition to dismiss does not date the bankruptcy",
         lambda: petition_date(ensurge) is None),
        ("Wave Systems: a conversion-order date is not a petition date",
         lambda: petition_date(wave) is None),
        ("MidgardXXI: an order-for-relief date is never the involuntary petition date",
         lambda: petition_date(midgard) is None),
        ("Rotate Black: involuntary petition date, not the conversion-granted date",
         lambda: petition_date(rotate_black) == day(2004, 3, 31)),
        ("Heartland: no stated date stays unresolved",
         lambda: petition_date(heartland) is None),
        ("a prior report's filing date is never the petition date",
         lambda: petition_date(prior_report) is None),
        ("Spirit: a coordinated later date for subsidiaries does not displace the registrant's",
         lambda: petition_date(spirit) == day(2024, 11, 18)),
        ("Abitibi: a Chapter 15 recognition petition does not supply the date",
         lambda: petition_date(abitibi) == day(2009, 4, 16)),
        ("guard: 'Convertibles' in a debtor name is not a conversion",
         lambda: petition_date(jennifer) == day(2010, 7, 18)),
        ("guard: 'filed an amended Chapter 11 plan' is not a petition",
         lambda: petition_date(garrett_plan) is None),
    ]


def _classify_as(
    text: str, names: tuple[str, ...] = (), co_registered: bool = False
) -> Classification:
    """classify() with registrant identity, passed only where the signature takes it.

    Keeps every stage-5 fixture runnable against earlier classifier versions, so a
    negative control measures the rule rather than a TypeError.
    """
    params = inspect.signature(classify).parameters
    kwargs: dict[str, object] = {}
    if "registrant_names" in params:
        kwargs["registrant_names"] = names
    if "co_registered" in params:
        kwargs["co_registered"] = co_registered
    return classify(text, **kwargs)


def check_stage5_registrant_identity() -> list[tuple[str, object]]:
    """Repair stage 5: registrant/debtor identity (A1-A5) with F and G safeguards.

    Every rule has a development example it fixes and a guard against the
    opposite error. Shapes are from development filings; names are the filers'
    EDGAR names.
    """
    head = "Item 1.03 Bankruptcy or Receivership.\n"
    ch11, ch7 = Disposition.REGISTRANT_CHAPTER_11, Disposition.REGISTRANT_CHAPTER_7
    sub, amb = Disposition.SUBSIDIARY_ONLY, Disposition.AMBIGUOUS

    def disp(text: str, names: tuple[str, ...] = (), co_registered: bool = False) -> Disposition:
        return _classify_as(text, names, co_registered).disposition

    # --- A1: bankruptcy verbs and objects other than "filed ... petition" ---
    virgin_orbit = head + (
        "On April 4, 2023 (the “Petition Date”), Virgin Orbit Holdings, Inc. (the "
        "“Company”) and its domestic subsidiaries (together with the Company, the "
        "“Debtors”), commenced voluntary proceedings under Chapter 11 of the United "
        "States Bankruptcy Code."
    )
    team_financial = head + (
        "On April 5, 2009, Team Financial, Inc. (the “Registrant”) filed for voluntary "
        "bankruptcy protection under Chapter 11 of the U.S. Bankruptcy Code."
    )
    wyndstorm = head + (
        "Bankruptcy On October 7 2011 registrant filed for chapter 7 bankruptcy at the United "
        "States Bankruptcy Court for the District of Columbia."
    )
    mallinckrodt = head + (
        "As previously disclosed, on August 28, 2023, Mallinckrodt plc (in examination under "
        "Part 10 of the Companies Act 2014 of Ireland and hereinafter “Mallinckrodt” or "
        "the “Company”) and certain of its subsidiaries (collectively, the “Debtors”) "
        "voluntarily initiated proceedings (the “Chapter 11 Cases”) under chapter 11 of "
        "title 11 of the United States Code."
    )
    plan_filing = head + (
        "As previously disclosed, on August 1, 2019, the Company filed a joint chapter 11 plan of "
        "reorganization and a related disclosure statement with the Bankruptcy Court."
    )
    risk_sentence = head + (
        "Many factors could cause actual future events to differ materially, including the "
        "Company's ability to obtain approval of motions filed in the Chapter 11 Cases."
    )
    dismissal_petition = head + (
        "On March 21, 2005, Ensurge, Inc. (“the Company”) filed a petition with the "
        "Bankruptcy Court to voluntarily dismiss the Chapter 11 bankruptcy."
    )

    # --- A1: involuntary petitions and consent to relief ---------------------
    midgard = head + (
        "In connection with the previously reported involuntary petition under Chapter 7 of the "
        "United States Bankruptcy Code against MidgardXXI, Inc. (the \"Company\") filed in the "
        "United States Bankruptcy Court for the District of Colorado by Eastpark Investors, LLC, "
        "a former landlord, an order for relief was entered on January 30, 2007."
    )
    impart = head + (
        "Following the filing of an involuntary petition on February 14, 2008, Impart Media "
        "Group, Inc. (the \"Company\") consented to bankruptcy relief, and the Bankruptcy Court "
        "entered an order for relief under Chapter 11 on May 21, 2008."
    )
    involuntary_against_subsidiary = head + (
        "Creditors filed an involuntary petition under Chapter 7 against Acme Mining, LLC, a "
        "wholly owned subsidiary of the Company."
    )

    # --- A2: the registrant's other names for itself -------------------------
    we_filed = head + (
        "On January 21, 2011, we filed a voluntary petition for relief in the United States "
        "Bankruptcy Court for the District of Kansas under Chapter 11 of the US Bankruptcy Code."
    )
    emerge = (
        "Item 1.01 Entry into a Material Definitive Agreement.\nOn February 14, 2007, eMerge "
        "Interactive, Inc. (“eMerge”) and The Bank entered into an agreement.\n" + head +
        "On February 14, 2007, eMerge filed a voluntary petition for relief under Chapter 11 of "
        "the United States Bankruptcy Code."
    )
    debtors_defined_with_company = (
        "EXPLANATORY NOTE As previously disclosed, Trinseo PLC (the “Company,” “we” "
        "or “us”) and certain of its direct and indirect subsidiaries (collectively, the "
        "“Debtors”) intend to conduct a restructuring.\n" + head +
        "On May 26, 2026 (the “Petition Date”), the Debtors filed voluntary petitions under "
        "Chapter 11 of the Bankruptcy Code."
    )
    debtors_defined_without_company = (
        "EXPLANATORY NOTE Certain of the Company's subsidiaries (collectively, the "
        "“Debtors”) entered into a support agreement.\n" + head +
        "On May 26, 2026, the Debtors filed voluntary petitions under Chapter 11 of the "
        "Bankruptcy Code."
    )
    debtors_undefined = head + (
        "On February 17, 2009 the Debtors filed voluntary petitions seeking relief under the "
        "provisions of chapter 11 of title 11 of the United States Code."
    )
    partnership = head + (
        "As previously disclosed on July 15, 2019, Emerge Energy Services LP (the "
        "“Partnership”), along with its general partner Emerge Energy Services GP, LLC and "
        "certain of the Partnership's subsidiaries (collectively, the “Debtors”), filed "
        "voluntary petitions for relief under chapter 11 of the Bankruptcy Code."
    )
    nortel = head + (
        "On January 14, 2009, NNC's indirect subsidiaries Nortel Networks Inc. (“NNI”), a "
        "Delaware corporation, and certain other subsidiaries (collectively, the “U.S. "
        "Debtors”) filed voluntary petitions under Chapter 11 of the Bankruptcy Code."
    )

    # --- A3 / A4 / A5: punctuation, long lists, "U.S." -----------------------
    intelsat = head + (
        "Chapter 11 Filing On May 13, 2020, Intelsat S.A. (the “Company”) and certain of "
        "its subsidiaries (such subsidiaries, each a “Debtor,” and together with the "
        "Company, the “Debtors”) commenced voluntary cases (the “Chapter 11 Cases”) "
        "under Chapter 11 of the United States Bankruptcy Code."
    )
    rentech = head + (
        "On December 19, 2017, the Company and one of its subsidiaries, Rentech WP U.S. Inc., "
        "filed voluntary petitions in the Bankruptcy Court seeking relief under Chapter 11 of "
        "the Bankruptcy Code."
    )
    dri = head + (
        "On March 25, 2012, DRI Corporation (“DRI”), including its wholly-owned North "
        "Carolina subsidiaries Digital Recorders, Inc., TwinVision of North America, Inc. and "
        "Robinson Turney International, Inc. (collectively, the “Debtors”) filed voluntary "
        "petitions to sell its assets and operations pursuant to Section 363 of Chapter 11 of "
        "the U.S. Bankruptcy Code."
    )
    former_name_subsidiary = head + (
        "On March 25, 2012, its wholly-owned subsidiaries Digital Recorders, Inc. and TwinVision "
        "of North America, Inc. filed voluntary petitions under Chapter 11."
    )
    subsidiaries_only_long = head + (
        "On March 25, 2012, the Company's wholly-owned subsidiaries Digital Recorders, Inc., "
        "TwinVision of North America, Inc. and Robinson Turney International, Inc. "
        "(collectively, the “Debtors”) filed voluntary petitions under Chapter 11."
    )
    premier = head + (
        "As previously announced, on June 14, 2016, Premier Exhibitions, Inc. (the "
        "“Company”) and each of its U.S. subsidiaries filed voluntary petitions for "
        "reorganization relief under Chapter 11 of the United States Bankruptcy Code."
    )
    us_sentence_end = head + (
        "The Company operates in the U.S. Its subsidiary filed a voluntary petition under "
        "Chapter 11 of the Bankruptcy Code."
    )

    # --- F: subsidiary-only leakage ------------------------------------------
    e_biofuels = head + (
        "On April 4, 2012, the Registrant’s wholly-owned subsidiary, e-Biofuels, LLC filed a "
        "voluntary petition for protection from creditors under Chapter 7 of Title 11 of the "
        "Bankruptcy Code."
    )
    accupoll = head + (
        "On February 21, 2006 AccuPoll, Inc., a Delaware corporation and wholly owned subsidiary "
        "of AccuPoll Holding Corp. (the \"Company\"), filed a voluntary bankruptcy case under "
        "Chapter 7 of the United States Bankruptcy Code."
    )
    hraa = head + (
        "On August11, 2014 (the “Petition Date”), Health Revenue Assurance Associates, Inc. "
        "( “HRAA”), the operating subsidiary of Health Revenue Assurance Holdings, Inc. (the "
        "“Company”), filed a voluntary petition seeking relief under Chapter 11."
    )
    filed_for_subsidiaries = head + (
        "On April 6, 2020 Amazing Energy Oil & Gas, Co. (the “Company”) filed Chapter 11 "
        "Bankruptcy petitions, in the Southern District of Mississippi, for three (3) of its "
        "wholly owned subsidiaries."
    )
    filed_for_itself_too = head + (
        "On April 6, 2020 the Company filed Chapter 11 petitions for itself and its wholly owned "
        "subsidiaries in the Southern District of Mississippi."
    )
    echostar = head + (
        "On August 2, 2026 (the “Petition Date”), EchoStar Corporation’s "
        "(“EchoStar”) subsidiary Hughes Satellite Systems Corporation and certain of its "
        "wholly-owned subsidiaries, (i) EchoStar Orbital L.L.C. and (ii) EchoStar Government "
        "Services L.L.C., filed voluntary petitions under chapter 11 of the Bankruptcy Code."
    )
    vesta = head + (
        "As previously disclosed, an involuntary petition under Chapter 7 of the United States "
        "Bankruptcy Code, styled In re: Vesta Insurance Group, Inc., Case No. 06-02517-TBB7, "
        "United States Bankruptcy Court – Northern District of Alabama (the “Chapter 7 "
        "Petition”), was filed on July 18, 2006. On August 7, 2006, Vesta Insurance Group, "
        "Inc. (“Vesta”) filed a request with the Bankruptcy Court to convert the Chapter 7 "
        "Petition to a voluntary Chapter 11 petition. Also, on August 7, 2006, J. Gordon Gaines, "
        "Inc. (“JGG”), the management company subsidiary of Vesta, filed a voluntary "
        "petition for relief under Chapter 11 of the Bankruptcy Code."
    )
    lost_full_stop = head + (
        "On February 7, 2009, Crescent Fuels, Inc. (“Crescent”), a subsidiary of Titan "
        "Global Holdings, Inc. (the “Company”), filed a voluntary petition under Chapter 11. "
        "The guarantees were reaffirmed by the Company and Philip Near, the former President of "
        "Crescent Oil Company, Inc. Also on February 9, 2009, Appalachian Oil Company, Inc. "
        "(“Appco”), a subsidiary of the Company filed a voluntary petition under Chapter 11."
    )

    # --- G: prospective, authorisation, negation; names are not event words --
    heartland_planned = head + (
        "Heartland Partners, L.P. (the \"Company\") and its affiliates are planning on dissolving "
        "and liquidating by filing, in the near future, voluntary petitions under the provisions "
        "of chapter 11 of the United States Bankruptcy Code."
    )
    heartland_filed = head + (
        "Heartland Partners, L.P. (the \"Company\") and its affiliates have filed voluntary "
        "petitions under the provisions of chapter 11 of the United States Bankruptcy Code."
    )
    csa = head + (
        "On April 27th, 2018, the Board of Directors of CSA authorized the President to instruct "
        "the company’s bankruptcy counsel to prepare such documents as may be necessary to "
        "place the company in chapter 7 bankruptcy, and instruct that they be filed."
    )
    board_engaged_counsel = head + (
        "On April 3, 2013, our Board of Directors unanimously voted to engage a law firm to file "
        "a Chapter 7 liquidation petition on our behalf under the United States Bankruptcy Code."
    )
    negated = head + (
        "On April 6, 2020 three of the Company's wholly owned subsidiaries filed Chapter 11 "
        "Bankruptcy petitions. The Company itself has not filed for Bankruptcy protection."
    )
    negation_of_other_filing = head + (
        "The Company has not filed its annual report on Form 10-K. On May 11, 2009, the Company "
        "filed for voluntary bankruptcy protection under Chapter 11 of the Bankruptcy Code."
    )
    t3_motion = head + (
        "On May 15, 2017, T3 Motion, Inc. filed a voluntary petition under Chapter 7 of the "
        "United States Bankruptcy Code."
    )
    voteco = head + (
        "On July 28, 2009, the Company and its affiliates FCP VoteCo, LLC and Fertitta "
        "Partners, LLC filed voluntary petitions under Chapter 11 of the Bankruptcy Code."
    )
    jennifer = head + (
        "On July 18, 2010, Jennifer Convertibles, Inc. and all of its affiliated debtors (the "
        "“Company”) filed voluntary petitions for bankruptcy relief under Chapter 11."
    )

    # --- co-registrant identity (LABEL_POLICY 11) ----------------------------
    refco = head + (
        "On October 17, 2005, Refco Inc. (\"Refco\") and certain of its subsidiaries, including "
        "Refco Group Ltd., LLC (\"Refco Group\") and Refco Finance Inc. (\"Refco Finance\") "
        "(collectively, the \"Debtors\") filed voluntary petitions for reorganization under "
        "Chapter 11 of the United States Bankruptcy Code."
    )
    calgen_cover = (
        "FORM 8-K Additional Registrants: Calpine Generating Company, LLC Delaware; Calpine "
        "Freestone Energy GP, LLC Delaware; CalGen Finance Corp. Delaware.\n"
    )
    calgen_item = head + (
        "(a) On December 20, 2005, Calpine Corporation (“Calpine”) and certain of its "
        "subsidiaries, including Calpine Generating Company, LLC, CalGen Finance Corp., the "
        "additional registrants listed in the “Additional Registrants” table above "
        "(collectively, the “Company” or “CalGen”) (collectively, the "
        "“Debtors”) filed voluntary petitions for reorganization under Chapter 11."
    )
    atlas = head + (
        "On July 27, 2016, Atlas Resource Partners, L.P. (“ARP”) and certain of its "
        "subsidiaries (collectively with ARP, the “Debtors”) filed voluntary petitions for "
        "relief under chapter 11 of the Bankruptcy Code. The Debtors include Atlas Resources, "
        "LLC, which is the Managing General Partner of ATLAS AMERICA SERIES 25-2004(B) L.P. "
        "(the “Partnership”)."
    )
    generic_only_coregistered = head + (
        "On December 20, 2005, the Company and certain of its subsidiaries filed voluntary "
        "petitions for reorganization under Chapter 11."
    )
    # --- rules added from the corpus transition review --------------------------
    announced_it_filed = head + (
        "On June 18, 2008, Fremont General Corporation (the \u201cCompany\u201d) announced that it "
        "had filed a voluntary petition under Chapter 11 of the United States Bankruptcy Code."
    )
    announced_dated_it_filed = head + (
        "On June 7, 2005, Ramp Corporation (the \u201cCompany\") announced that on June 2, 2005 "
        "it filed a voluntary petition in the United States Bankruptcy Court under Chapter 11."
    )
    announced_subsidiary_filed = head + (
        "On June 18, 2008, the Company announced that its subsidiary, Acme Loans, LLC, had filed "
        "a voluntary petition under Chapter 11 of the United States Bankruptcy Code."
    )
    which_aside = head + (
        "On December 14, 2017, Cobalt International Energy, Inc. (the \u201cCompany\u201d) and its "
        "affiliates listed on Exhibit 99.1 hereto (together with the Company, the "
        "\u201cDebtors\u201d), which Exhibit is incorporated herein by reference, filed voluntary "
        "petitions for relief under chapter 11 of the Bankruptcy Code."
    )
    which_aside_subsidiaries = head + (
        "The Company announced that its subsidiaries, which are not guarantors, filed voluntary "
        "petitions under Chapter 11 of the Bankruptcy Code."
    )
    semicolon_list = head + (
        "On July 2, 2012, GameTech International, Inc. (the \u201cCompany\u201d) and its wholly "
        "owned subsidiaries; GameTech Arizona Corp. and GameTech Canada Corp. filed voluntary "
        "petitions under Chapter 11 of the Bankruptcy Code."
    )
    semicolon_clause = head + (
        "The Company entered into a forbearance agreement with its lenders; its subsidiary filed "
        "a voluntary petition under Chapter 11 of the Bankruptcy Code."
    )
    ampersand_name = head + (
        "On January 29, 2019, PG&E Corporation and Pacific Gas and Electric Company (the "
        "\u201cUtility\u201d) (together, the \u201cDebtors\u201d) filed voluntary petitions for "
        "relief under chapter 11 of title 11 of the United States Code."
    )
    ampersand_name_absent = head + (
        "On January 29, 2019, PG&E Corporation and certain of its subsidiaries filed voluntary "
        "petitions for relief under chapter 11 of title 11 of the United States Code."
    )
    owned_entities_not_included = head + (
        "On January 31, 2023, the Company and certain of its direct subsidiaries filed voluntary "
        "petitions under chapter 11 of the Bankruptcy Code. Certain of the Company\u2019s "
        "international subsidiaries were not included in the Chapter 11 filing."
    )
    caused_to_be_filed = head + (
        "On May 6, 2005, LMIC, Inc. (the \"Registrant\") and its wholly owned subsidiary caused to "
        "be filed voluntary petitions for relief under Chapter 11 of the Bankruptcy Code."
    )
    expected_to_be_filed = head + (
        "The Registrant expects petitions for relief under Chapter 11 of the Bankruptcy Code to "
        "be filed next month."
    )
    co_company_us_dots = head + (
        "On December 7, 2011, Americas Energy Company-Aeco, Inc. and U.S. Dry Cleaning Services "
        "Corporation filed voluntary petitions under Chapter 11 of the Bankruptcy Code."
    )
    sibling_names_only = head + (
        "On December 7, 2011, Americas Energy Holdings, Inc. filed a voluntary petition under "
        "Chapter 11 of the Bankruptcy Code."
    )
    ferrellgas = (
        "EXPLANATORY NOTE Ferrellgas Partners, L.P. (the \u201cCompany\u201d) reports as follows.\n"
        + head + "On January 11, 2021, the Company and Ferrellgas Partners Finance Corp. filed "
        "voluntary petitions under chapter 11 of the Bankruptcy Code."
    )
    parent_of_registrant = head + (
        "On March 14, 2018, iHeartMedia, Inc., the indirect parent of Clear Channel Outdoor "
        "Holdings, Inc. (\u201cCCOH\u201d), and certain of its subsidiaries listed on Exhibit 99.1 "
        "(collectively, the \u201cDebtors\u201d), filed voluntary petitions under Chapter 11."
    )
    owner_of_securities = head + (
        "On September 15, 2008, Lehman Brothers Holdings Inc. (\u201cLBHI\u201d), the sole owner "
        "of the common securities of Lehman Brothers Holdings E-Capital LLC I, filed a voluntary "
        "petition under Chapter 11 of the Bankruptcy Code."
    )
    neither_nor = head + (
        "On September 19, 2023, UpHealth Holdings, Inc. (the \u201cDebtor\u201d), a subsidiary of "
        "the Company, filed a voluntary petition under Chapter 11. Neither the Company nor any "
        "other subsidiary of the Company besides the Debtor has filed a petition for relief "
        "under Chapter 11 of the U.S. Bankruptcy Code."
    )
    jcrew = head + (
        "On May 4, 2020, Chinos Holdings, Inc. (\u201cParent\u201d), the ultimate parent of J.Crew "
        "Group, Inc. (the \u201cCompany\u201d), Chinos Intermediate Holdings B, Inc. the direct "
        "parent of the Company, the Company and certain of the Company\u2019s direct and indirect "
        "subsidiaries (collectively, the \u201cDebtors\u201d) filed voluntary petitions under "
        "chapter 11 of the Bankruptcy Code."
    )
    none_of_subsidiaries = head + (
        "On March 9, 2015, BPZ Resources, Inc. (the \u201cCompany\u201d) filed a voluntary "
        "petition under Chapter 11. None of the Company\u2019s direct or indirect subsidiaries "
        "has filed for reorganization under Chapter 11."
    )
    parent_itself_filed = head + (
        "On March 27, 2009, the Company, the indirect parent of its operating subsidiaries, "
        "filed a voluntary petition under Chapter 11 of the Bankruptcy Code."
    )
    dynegy = head + (
        "On November 7, 2011, Dynegy Holdings, LLC (“DH”) and four of its wholly-owned "
        "subsidiaries (collectively, the “Debtor Entities”), filed voluntary petitions for "
        "relief under Chapter 11 of the United States Bankruptcy Code."
    )
    adams = head + (
        "On April 21, 2017, Adams Resources Exploration Corporation (\"AREC\"), a wholly owned "
        "subsidiary of Adams Resources & Energy, Inc. (the \"Company\"), filed a petition under "
        "Chapter 11 of the United States Bankruptcy Code."
    )

    freestone = ("Calpine Freestone Energy GP, LLC",)
    dri_profile = CompanyProfile(853695, None, None, (), (
        ("DRI CORP", datetime(2007, 7, 19), None),
        ("DIGITAL RECORDERS INC", datetime(1996, 7, 15), datetime(2007, 7, 19)),
    ))
    mirant_profile = CompanyProfile(1138258, None, None, (), (
        ("GENON MID-ATLANTIC, LLC", datetime(2010, 11, 5), None),
        ("MIRANT MID ATLANTIC LLC", datetime(2001, 7, 3), datetime(2010, 11, 5)),
    ))
    return [
        ("A1 Virgin Orbit: 'commenced voluntary proceedings' is a registrant Chapter 11",
         lambda: disp(virgin_orbit) is ch11),
        ("A1 Team Financial: 'filed for voluntary bankruptcy protection'",
         lambda: disp(team_financial) is ch11),
        ("A1 Wyndstorm: 'registrant filed for chapter 7 bankruptcy'",
         lambda: disp(wyndstorm) is ch7),
        ("A1 Mallinckrodt: 'voluntarily initiated proceedings' with a quote-paren subject",
         lambda: disp(mallinckrodt, ("Mallinckrodt plc",)) is ch11),
        ("A1 guard: filing a chapter 11 plan is not a petition",
         lambda: not disp(plan_filing).is_positive),
        ("A1 guard: 'motions filed in the Chapter 11 Cases' in a risk sentence is not a filing",
         lambda: not disp(risk_sentence).is_positive),
        ("A1 guard: a petition to dismiss is not a bankruptcy filing",
         lambda: not disp(dismissal_petition).is_positive),
        ("A1 MidgardXXI: involuntary Chapter 7 petition against the Company",
         lambda: disp(midgard) is ch7),
        ("A1 Impart Media: the Company consented to relief on an involuntary petition",
         lambda: disp(impart) is ch11),
        ("A1 guard: an involuntary petition against a named subsidiary is not the registrant's",
         lambda: not disp(involuntary_against_subsidiary).is_positive),
        ("A2 'we filed a voluntary petition'", lambda: disp(we_filed) is ch11),
        ("A2 eMerge: the filer's defined short name",
         lambda: disp(emerge, ("EMERGE INTERACTIVE INC",)) is ch11),
        ("A2 Trinseo: 'the Debtors' defined elsewhere to include the Company",
         lambda: disp(debtors_defined_with_company, ("Trinseo PLC",)) is ch11),
        ("A2 guard: 'the Debtors' defined as subsidiaries only is not the registrant",
         lambda: not disp(debtors_defined_without_company).is_positive),
        ("A2 guard: an undefined 'the Debtors' leaves identity unresolved",
         lambda: disp(debtors_undefined) is amb),
        ("A2 Emerge Energy: 'the Partnership' with a long debtor list",
         lambda: disp(partnership, ("Emerge Energy Services LP",)) is ch11),
        ("A2 guard: 'Nortel Networks Inc.' does not name registrant 'Nortel Networks Corp'",
         lambda: disp(nortel, ("NORTEL NETWORKS CORP",)) is sub),
        ("A3 Intelsat: quote-paren '\") and certain of its' + 'commenced voluntary cases'",
         lambda: disp(intelsat) is ch11),
        ("A3 Rentech: 'the Company and one of its subsidiaries'", lambda: disp(rentech) is ch11),
        ("A4 DRI: ~200-character debtor enumeration before the verb",
         lambda: disp(dri, dri_profile.names_at(datetime(2012, 3, 26))) is ch11),
        ("A2 guard: a name given up years earlier is not used (a subsidiary carries it)",
         lambda: disp(former_name_subsidiary, dri_profile.names_at(datetime(2012, 3, 26))) is sub),
        ("A2 guard: a name adopted later is not used to read an earlier filing",
         lambda: mirant_profile.names_at(datetime(2005, 11, 1)) == ("MIRANT MID ATLANTIC LLC",)),
        ("A4 guard: a long list of subsidiaries alone stays subsidiary-only",
         lambda: disp(subsidiaries_only_long) is sub),
        ("A5 Premier Exhibitions: 'each of its U.S. subsidiaries filed'",
         lambda: disp(premier) is ch11),
        ("A5 guard: a sentence really ending in 'U.S.' does not join the next",
         lambda: not disp(us_sentence_end).is_positive),
        ("F e-Biofuels: 'the Registrant's wholly-owned subsidiary ... filed' is subsidiary-only",
         lambda: disp(e_biofuels) is sub),
        ("F AccuPoll: 'a Delaware corporation and wholly owned subsidiary of' is not positive",
         lambda: disp(accupoll, ("ACCUPOLL HOLDING CORP",)) is amb),
        ("F HRAA: 'the operating subsidiary of' is not positive", lambda: disp(hraa) is amb),
        ("F Amazing Energy: petitions filed FOR its subsidiaries are subsidiary-only",
         lambda: disp(filed_for_subsidiaries) is sub),
        ("F guard: petitions filed for itself and its subsidiaries stay positive",
         lambda: disp(filed_for_itself_too) is ch11),
        ("F EchoStar: a defined term inside the parent's possessive does not make it a debtor",
         lambda: not disp(echostar, ("EchoStar CORP",), True).is_positive),
        ("F Vesta: involuntary Chapter 7 'In re: Vesta' beats the subsidiary's Chapter 11",
         lambda: disp(vesta, ("VESTA INSURANCE GROUP INC",)) is ch7),
        ("F Vesta: event date is the involuntary petition date",
         lambda: _classify_as(vesta, ("VESTA INSURANCE GROUP INC",)).petition_date
         == datetime(2006, 7, 18).date()),
        ("F Titan: a lost full stop after 'Inc.' does not make the Company a filer",
         lambda: not disp(lost_full_stop, ("Titan Global Holdings, Inc.",)).is_positive),
        ("F guard: Adams Resources remains ambiguous with registrant names supplied",
         lambda: disp(adams, ("ADAMS RESOURCES & ENERGY, INC.",)) is amb),
        ("G Heartland: 'planning on ... filing, in the near future' is not an event",
         lambda: not disp(heartland_planned).is_positive),
        ("G guard: Heartland 'have filed voluntary petitions' is an event",
         lambda: disp(heartland_filed) is ch11),
        ("G CSA: authorisation to prepare and file is not an event",
         lambda: not disp(csa).is_positive),
        ("G board vote to engage counsel to file is not an event",
         lambda: not disp(board_engaged_counsel).is_positive),
        ("G explicit 'The Company itself has not filed' overrides: subsidiary-only",
         lambda: disp(negated) is sub),
        ("G guard: 'has not filed its annual report' does not negate a real petition",
         lambda: disp(negation_of_other_filing) is ch11),
        ("G guard: 'T3 Motion, Inc.' is a name, not a motion",
         lambda: disp(t3_motion, ("T3 Motion, Inc.",)) is ch7),
        ("G guard: 'FCP VoteCo, LLC' is a name, not a vote", lambda: disp(voteco) is ch11),
        ("G guard: 'Jennifer Convertibles' is a name, not a conversion",
         lambda: disp(jennifer) is ch11),
        ("co-registrant Refco Finance: exact named co-registrant is positive",
         lambda: disp(refco, ("Refco Finance Inc.",), True) is ch11),
        ("co-registrant CalGen: 'additional registrants' + exact name in the filing is positive",
         lambda: disp(calgen_cover + calgen_item, freestone, True) is ch11),
        ("co-registrant guard: 'additional registrants' without this exact name is ambiguous",
         lambda: disp(calgen_item, freestone, True) is amb),
        ("co-registrant guard: a generic 'the Company' in a co-registered filing is ambiguous",
         lambda: disp(generic_only_coregistered, freestone, True) is amb),
        ("guard: an Atlas-style managed partnership is not treated as a debtor",
         lambda: not disp(atlas, ("ATLAS AMERICA SERIES 25-2004 (B) L.P.",)).is_positive),
        ("F Clear Channel Outdoor: 'the indirect parent of <registrant>' filed, not the registrant",
         lambda: not disp(parent_of_registrant, ("Clear Channel Outdoor Holdings, Inc.",))
         .is_positive),
        ("F Lehman E-Capital: 'owner of the common securities of <registrant>' is not a debtor",
         lambda: not disp(owner_of_securities, ("Lehman Brothers Holdings E-Capital LLC I",), True)
         .is_positive),
        ("G UpHealth: 'Neither the Company nor ... has filed' is an explicit negation",
         lambda: not disp(neither_nor, ("UpHealth, Inc.",)).is_positive),
        ("F guard J.Crew: a reference after a list comma ('parent of the Company, the Company and')"
         " is a debtor",
         lambda: disp(jcrew, ("J CREW GROUP INC",)) is ch11),
        ("G guard BPZ: 'None of the Company's subsidiaries has filed' does not negate the Company",
         lambda: disp(none_of_subsidiaries, ("BPZ RESOURCES INC",)) is ch11),
        ("F guard: the registrant that is itself a parent and filed stays positive",
         lambda: disp(parent_itself_filed) is ch11),
        ("A2 Fremont: 'announced that it had filed' resolves 'it' to the Company",
         lambda: disp(announced_it_filed) is ch11),
        ("A2 Ramp: 'announced that on June 2, 2005 it filed'",
         lambda: disp(announced_dated_it_filed) is ch11),
        ("A2 guard: 'announced that its subsidiary had filed' is subsidiary-only",
         lambda: disp(announced_subsidiary_filed) is sub),
        ("A4 Cobalt: a ', which ... ,' aside does not cut off the subject",
         lambda: disp(which_aside, ("Cobalt International Energy, Inc.",)) is ch11),
        ("A4 guard: an aside about subsidiaries does not add the Company",
         lambda: disp(which_aside_subsidiaries) is sub),
        ("A3 GameTech: a semicolon inside the debtor list", lambda: disp(semicolon_list) is ch11),
        ("A3 guard: a semicolon between clauses still separates subjects",
         lambda: disp(semicolon_clause) is sub),
        ("A2 PG&E: EDGAR '&' matches the text's 'and' for an exact co-registrant",
         lambda: disp(ampersand_name, ("PACIFIC GAS & ELECTRIC Co",), True) is ch11),
        ("A2 guard: the co-registrant absent from the debtor list stays ambiguous",
         lambda: disp(ampersand_name_absent, ("PACIFIC GAS & ELECTRIC Co",), True) is amb),
        ("G guard Invacare: 'the Company's subsidiaries were not included' does not negate it",
         lambda: disp(owned_entities_not_included) is ch11),
        ("A1 LMIC: 'caused to be filed voluntary petitions' is an actual filing",
         lambda: disp(caused_to_be_filed) is ch11),
        ("G guard: 'expects petitions ... to be filed' is not an event",
         lambda: not disp(expected_to_be_filed).is_positive),
        ("A2 EDGAR 'Co' is 'Company' and 'US' is 'U.S.'",
         lambda: disp(co_company_us_dots, ("AMERICAS ENERGY Co - AECO",)) is ch11
         and disp(co_company_us_dots, ("US Dry Cleaning Services Corp",)) is ch11),
        ("A2 guard: a sibling that extends the name is not the registrant",
         lambda: not disp(sibling_names_only, ("AMERICAS ENERGY Co - AECO",)).is_positive),
        ("co-registrant Ferrellgas Partners: 'the Company' defined as this exact registrant",
         lambda: disp(ferrellgas, ("FERRELLGAS PARTNERS L P",), True) is ch11),
        ("co-registrant guard: Ferrellgas, L.P. is not that defined term",
         lambda: disp(ferrellgas, ("FERRELLGAS L P",), True) is amb),
        ("guard: parent Dynegy Inc. is not inferred from Dynegy Holdings' filing",
         lambda: not disp(dynegy, ("DYNEGY INC.",), True).is_positive),
    ]


def run() -> None:
    with tempfile.TemporaryDirectory() as raw_root:
        root = Path(raw_root)
        submissions, documents, dera = build_fixture(root)
        sic_index = build_sic_index(dera)
        rows, census, mapping = build_gate_one(
            scanner=SubmissionsArchiveScanner(submissions),
            archive=SubmissionsArchive(submissions, sic_index),
            documents=documents,
            start_year=2019,
            end_year=2019,
        )
        _assert_all(rows, census, mapping, sic_index)
    _report(check_merge_guards())
    _report(check_classifier_regressions())
    _report(_evaluate(check_stage1_section_extraction()))
    _report(_evaluate(check_stage2_amendment_correction()))
    _report(_evaluate(check_stage3_chapter_and_identity()))
    _report(_evaluate(check_stage4_petition_dates()))
    _report(_evaluate(check_stage5_registrant_identity()))


def _assert_all(rows, census: Counter, mapping, sic_index) -> None:
    checks = [
        ("DERA SIC index populated", len(sic_index) == 3),
        ("primary document URLs are constructible",
         all(_candidate_urls_resolve())),
        ("amendment detected", census["amendment_filings"] == 1),
        ("amendment merged, not double counted", census["assembled_events"] == 2),
        ("amendment supplies missing petition date",
         mapping and mapping[0]["petition_date"] == "2019-09-01"),
        ("amendment supplies missing docket",
         mapping and mapping[0]["docket"] == "19-12345"),
        ("unidentified original plus amendment is one event",
         mapping and len(mapping[0]["source_accessions"]) == 2),
        ("FIRE filer excluded by SIC as filed",
         census["observation_fire_excluded"] == 1),
        ("multiplicity captured: one event labels two 10-Ks",
         mapping and mapping[0]["multiplicity"] == 2),
        ("unique events and observations differ",
         rows[0]["unique_events"] == 1 and rows[0]["positive_observations"] == 2),
        ("canonical event time comes from the amendment, not disclosure",
         mapping and mapping[0]["petition_date"] == "2019-09-01"),
    ]
    _report(checks)


def _report(checks: list[tuple[str, bool]]) -> None:
    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {label}")
    if not all(passed for _, passed in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
