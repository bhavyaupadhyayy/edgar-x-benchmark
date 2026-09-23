"""Phase 2A analysis: executes only the pre-frozen HUMAN_VALIDATION_ANALYSIS_PLAN.md.

Reads the four reviewer/consensus artifacts, the frozen 188-case packet, and the
sealed key. Computes nothing the plan does not define. Writes results.json,
results.csv and disagreements.csv.

No benchmark model is run, no Phase 1 label is changed, and no case is dropped,
re-drawn or substituted.
"""
from __future__ import annotations
import csv, json, math, hashlib, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
HV = BENCH / "human_validation"
IN = HERE / "inputs"

EXPECT = {
    "reviewer_A_authoritative.csv":            "6588e5573828676ff641cafa050beb81d753fbfbea24257329915b2b0d3b1cf0",
    "reviewer_B_authoritative.csv":            "3da0bbe53d7567140076b705e0d905c348447ec04ed3f5e6e1e17be54efc566a",
    "reviewer_C_form_completed_transcribed.csv":"4ca9e6443fa1c4fce5b197dd7bb88cf07e65d4b874e7495bfd263cbbe5418881",
    "human_consensus_188.csv":                 "49fa629322ffc90df043bc4cacb3dda9e5ce996f76194a9db22baccac9713377",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rows(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open()))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval, as fixed in the analysis plan."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - hw), min(1.0, c + hw))


def norm(v: str | None) -> str:
    return (v or "").strip()


def is_positive(disp: str) -> bool:
    """Binary collapse fixed by the plan: positive vs non-positive.
    'Cannot determine' is non-positive, matching the primary rule."""
    return norm(disp).lower() == "yes"


def main() -> int:
    # ---- integrity -----------------------------------------------------------
    absent = [f for f in EXPECT if not (IN / f).exists()]
    if absent:
        print(
            "The reviewer inputs this script needs are not published.\n"
            "  missing: " + ", ".join(sorted(absent)) + "\n\n"
            "Reviewer packets, completed forms, the consensus file and the sealed\n"
            "answer key are withheld for reviewer privacy and to keep the 188-case\n"
            "holdout usable by other work. See validation/README.md.\n\n"
            "The results this script produced are published in results.json and\n"
            "results.csv, and every figure is reproduced in RESULTS.md with its\n"
            "numerator and denominator.",
            file=sys.stderr)
        return 2
    bad = [f for f, h in EXPECT.items() if sha256(IN / f) != h]
    if bad:
        print(f"INPUT HASH MISMATCH: {bad}", file=sys.stderr)
        return 1

    A = {r["case_id"]: r for r in rows(IN / "reviewer_A_authoritative.csv")}
    B = {r["case_id"]: r for r in rows(IN / "reviewer_B_authoritative.csv")}
    C = {r["case_id"]: r for r in rows(IN / "reviewer_C_form_completed_transcribed.csv")}
    K = {r["case_id"]: r for r in rows(IN / "human_consensus_188.csv")}

    frozen = [r["case_id"] for r in rows(HV / "reviewer_A_form.csv")]
    fset = set(frozen)
    if not (len(frozen) == 188 and set(A) == fset and set(B) == fset and set(K) == fset):
        print("case-id set does not match the frozen 188", file=sys.stderr)
        return 1
    if not set(C) <= fset:
        print("reviewer C cases are not a subset of the frozen 188", file=sys.stderr)
        return 1

    # ---- sealed key ----------------------------------------------------------
    sample = rows(HV / "sealed_key" / "final_validation_sample.csv")
    packet = rows(BENCH / "final_human_review_packet.csv")
    cik2case = {r["cik"]: r["case_id"] for r in packet}
    if len(cik2case) != 188:
        print("packet CIK->case_id is not 1:1", file=sys.stderr)
        return 1
    key = {}
    for r in sample:
        cid = cik2case.get(r["cik"])
        if cid:
            key[cid] = r
    if len(key) != 188:
        print("sealed key did not join onto all 188 cases", file=sys.stderr)
        return 1

    mapped_positive = [c for c in frozen if norm(key[c]["in_observation_map"]) == "1"]
    cls_pos = set(mapped_positive)

    ai = {r["case_id"]: r for r in rows(HV / "sealed_key" / "final_ai_adjudication.csv")}

    out: dict = {"n_cases": len(frozen)}

    # ---- protocol deviations (plan 4a) --------------------------------------
    TRIGGER = ("searched", "search of", "looked up", "google", "pacer", "docket search",
               "web search", "edgar search", "outside source", "external source",
               "ai assistant", "chatgpt", "claude", "asked a colleague", "asked another")
    dev = []
    for who, D in (("A", A), ("B", B)):
        for cid, r in D.items():
            t = norm(r.get("F_rationale")).lower()
            for k in TRIGGER:
                if k in t:
                    dev.append({"reviewer": who, "case_id": cid, "trigger": k,
                                "rationale": norm(r.get("F_rationale"))})
                    break
    out["deviations"] = {
        "contaminated_reviewer_case_judgements": len(dev),
        "affected_cases": len({d["case_id"] for d in dev}),
        "affected_mapped_positive_cases": sorted({d["case_id"] for d in dev} & set(mapped_positive)),
        "detail": dev,
    }
    excluded = {d["case_id"] for d in dev}

    # ---- primary (plan 2) ----------------------------------------------------
    conf, notconf, cannot = [], [], []
    for c in mapped_positive:
        v = norm(K[c]["A_registrant_is_debtor"])
        (conf if v.lower() == "yes" else notconf).append(c)
        if v.lower().startswith("cannot"):
            cannot.append(c)
    lo, hi = wilson(len(conf), len(mapped_positive))
    out["primary"] = {
        "definition": "classifier mapped-positive confirmation rate against final human consensus",
        "numerator": len(conf), "denominator": len(mapped_positive),
        "estimate": len(conf) / len(mapped_positive),
        "wilson_95_lo": lo, "wilson_95_hi": hi,
        "not_confirmed_cases": notconf,
        "cannot_determine_counted_as_not_confirmed": len(cannot),
        "cannot_determine_cases": cannot,
        "denominator_reduced_by_deviations": False,
    }

    # ---- first-pass A vs B (plan 3.5, 4) ------------------------------------
    FIELDS = [("A_registrant_is_debtor", "disposition"),
              ("B_initial_chapter", "chapter"),
              ("C_petition_date", "petition_date"),
              ("D_identity_assessment", "identity")]
    fp = {}
    for col, name in FIELDS:
        if name == "disposition":
            elig = [c for c in frozen if c not in excluded]
        elif name == "chapter":
            elig = [c for c in frozen if c not in excluded
                    and is_positive(A[c]["A_registrant_is_debtor"])
                    and is_positive(B[c]["A_registrant_is_debtor"])]
        elif name == "petition_date":
            elig = [c for c in frozen if c not in excluded
                    and is_positive(A[c]["A_registrant_is_debtor"])
                    and is_positive(B[c]["A_registrant_is_debtor"])]
        else:
            elig = [c for c in frozen if c not in excluded]
        agree = [c for c in elig if norm(A[c][col]) == norm(B[c][col])]
        fp[name] = {"agree": len(agree), "n": len(elig),
                    "rate": (len(agree) / len(elig)) if elig else None,
                    "excluded_for_deviation": len(excluded)}
    out["first_pass_agreement"] = fp

    # ---- Cohen's kappa, binary (plan 4) -------------------------------------
    elig = [c for c in frozen if c not in excluded]
    tab = Counter((is_positive(A[c]["A_registrant_is_debtor"]),
                   is_positive(B[c]["A_registrant_is_debtor"])) for c in elig)
    n = len(elig)
    po = (tab[(True, True)] + tab[(False, False)]) / n
    pa1 = (tab[(True, True)] + tab[(True, False)]) / n
    pb1 = (tab[(True, True)] + tab[(False, True)]) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    degenerate = (pe == 1) or pa1 in (0.0, 1.0) or pb1 in (0.0, 1.0)
    out["kappa_binary"] = {
        "n": n, "observed_agreement": po, "expected_agreement": pe,
        "kappa": None if degenerate else (po - pe) / (1 - pe),
        "undefined": bool(degenerate),
        "contingency_AposBpos": tab[(True, True)], "contingency_AposBneg": tab[(True, False)],
        "contingency_AnegBpos": tab[(False, True)], "contingency_AnegBneg": tab[(False, False)],
        "excluded_for_deviation": len(excluded),
    }

    # ---- adjudication (plan 3.6) --------------------------------------------
    disputed = defaultdict(list)
    for c in frozen:
        for col, name in FIELDS:
            if norm(A[c][col]) != norm(B[c][col]):
                disputed[c].append(name)
    out["adjudication"] = {
        "cases_requiring_reviewer_C": len(disputed),
        "percentage": 100.0 * len(disputed) / len(frozen),
        "reviewer_C_rows_supplied": len(C),
        "reviewer_C_covers_all_disputed": set(disputed) == set(C),
        "disputed_only_in_C": sorted(set(C) - set(disputed)),
        "disputed_missing_from_C": sorted(set(disputed) - set(C)),
    }

    vacuous = [c for c, f in disputed.items()
               if f == ["chapter"]
               and not is_positive(A[c]["A_registrant_is_debtor"])
               and not is_positive(B[c]["A_registrant_is_debtor"])]
    # ---- taxonomy (plan 5) ---------------------------------------------------
    tax = Counter()
    rowsout = []
    for c, flds in disputed.items():
        a, b = A[c], B[c]
        ad, bd = norm(a["A_registrant_is_debtor"]), norm(b["A_registrant_is_debtor"])
        if ad.lower().startswith("cannot") or bd.lower().startswith("cannot"):
            code = "DETERMINABLE"
        elif "disposition" in flds:
            code = "IDENTITY" if "identity" in flds else "OTHER"
        elif "chapter" in flds:
            code = "CHAPTER"
        elif "petition_date" in flds:
            code = "DATE"
        elif "identity" in flds:
            code = "IDENTITY"
        else:
            code = "OTHER"
        tax[code] += 1
        rowsout.append({"case_id": c, "disputed_fields": "|".join(flds), "taxonomy": code,
                        "A_disposition": ad, "B_disposition": bd,
                        "A_identity": norm(a["D_identity_assessment"]),
                        "B_identity": norm(b["D_identity_assessment"]),
                        "A_chapter": norm(a["B_initial_chapter"]), "B_chapter": norm(b["B_initial_chapter"]),
                        "A_date": norm(a["C_petition_date"]), "B_date": norm(b["C_petition_date"]),
                        "consensus_disposition": norm(K[c]["A_registrant_is_debtor"]),
                        "in_reviewer_C_form": c in C})
    out["disagreement_taxonomy"] = dict(sorted(tax.items()))
    tax_sub = Counter(r["taxonomy"] for r in rowsout if r["case_id"] not in set(vacuous))
    out["disagreement_taxonomy_substantive_only"] = dict(sorted(tax_sub.items()))

    # ---- AI adjudication vs human consensus (plan 6) ------------------------
    # The AI form uses its own vocabulary, not the reviewers' Yes/No. The human
    # question is "is the exact registrant a debtor in an INITIAL US Ch 7/11
    # proceeding", so the AI analogue is the conjunction of its three fields.
    def ai_positive(r: dict) -> bool:
        return (norm(r.get("ai_bankruptcy_event")).lower() == "yes"
                and norm(r.get("ai_registrant_is_debtor")).lower() == "registrant"
                and norm(r.get("ai_initial_event")).lower() == "initial")

    ai_agree = ai_n = 0
    ai_div = []
    for c in frozen:
        r = ai.get(c)
        if not r:
            continue
        ai_n += 1
        same = ai_positive(r) == is_positive(K[c]["A_registrant_is_debtor"])
        ai_agree += int(same)
        if not same:
            ai_div.append({"case_id": c,
                           "ai_bankruptcy_event": norm(r.get("ai_bankruptcy_event")),
                           "ai_registrant_is_debtor": norm(r.get("ai_registrant_is_debtor")),
                           "ai_initial_event": norm(r.get("ai_initial_event")),
                           "ai_positive": ai_positive(r),
                           "human_consensus": norm(K[c]["A_registrant_is_debtor"]),
                           "classifier_mapped_positive": c in cls_pos})
    out["ai_vs_human_consensus"] = {
        "mapping": "AI positive := ai_bankruptcy_event=yes AND ai_registrant_is_debtor=registrant AND ai_initial_event=initial",
        "agree": ai_agree, "n": ai_n, "rate": (ai_agree / ai_n) if ai_n else None,
        "n_divergences": len(ai_div), "divergences": ai_div}

    # ---- classifier vs consensus, all 188 (plan 3.1, 3.4) -------------------
    # The classifier's disposition field is the right analogue of the reviewers'
    # question. in_observation_map is a different thing: whether the event was
    # mapped onto an eligible 10-K observation, which also depends on panel
    # eligibility and the horizon. Both are reported; they are not the same.
    DISP_POS = {"registrant_chapter_7", "registrant_chapter_11"}
    hum_pos = {c for c in frozen if is_positive(K[c]["A_registrant_is_debtor"])}

    def confusion(cls_pos: set) -> dict:
        tp, fp_ = len(cls_pos & hum_pos), len(cls_pos - hum_pos)
        fn, tn = len(hum_pos - cls_pos), len(frozen) - len(cls_pos | hum_pos)
        return {"agree": tp + tn, "n": len(frozen), "rate": (tp + tn) / len(frozen),
                "classifier_pos_human_pos": tp, "classifier_pos_human_neg": fp_,
                "classifier_neg_human_pos": fn, "classifier_neg_human_neg": tn}

    disp_pos = {c for c in frozen if norm(key[c]["disposition"]) in DISP_POS}
    out["classifier_vs_consensus_all_188"] = {
        "by_classifier_disposition": confusion(disp_pos),
        "by_observation_map_membership": confusion(cls_pos),
        "note": ("The stratified holdout deliberately oversamples ambiguous, "
                 "subsidiary-only and receivership-only events, so neither table is a "
                 "population accuracy and neither is reported as one."),
    }

    # ---- AI vs human consensus on the mapped-positive subset ----------------
    mp = set(mapped_positive)
    ai_mp_agree = sum(1 for c in mapped_positive
                      if c in ai and ai_positive(ai[c]) == is_positive(K[c]["A_registrant_is_debtor"]))
    out["ai_vs_human_consensus_mapped_positives"] = {
        "agree": ai_mp_agree, "n": len(mapped_positive),
        "rate": ai_mp_agree / len(mapped_positive)}

    # ---- chapter / date agreement among human-confirmed positives (3.2, 3.3) -
    hc = sorted(hum_pos)
    ch_ok = ch_n = 0
    for c in hc:
        k = norm(key[c]["disposition"])
        want = {"registrant_chapter_11": "Chapter 11", "registrant_chapter_7": "Chapter 7"}.get(k)
        if want:
            ch_n += 1
            ch_ok += int(norm(K[c]["B_initial_chapter"]) == want)
    out["chapter_agreement_confirmed_positives"] = {
        "agree": ch_ok, "n": ch_n, "rate": (ch_ok / ch_n) if ch_n else None,
        "note": "denominator is human-confirmed positives whose classifier disposition names a chapter"}
    d_ok = d_n = d_unres = 0
    for c in hc:
        hd = norm(K[c]["C_petition_date"])
        kd = norm(key[c]["petition_date"])
        if hd.lower().startswith("cannot") or not hd or not kd:
            d_unres += 1
            continue
        d_n += 1
        d_ok += int(hd[:10] == kd[:10])
    out["petition_date_agreement_confirmed_positives"] = {
        "agree": d_ok, "n": d_n, "rate": (d_ok / d_n) if d_n else None,
        "excluded_unresolvable_under_consensus": d_unres}

    # ---- consensus provenance audit ------------------------------------------
    eq = {f: sum(1 for c in frozen if norm(K[c][f]) == norm(A[c][f])) for f, _ in FIELDS}
    out["consensus_provenance_audit"] = {
        "consensus_equals_reviewer_A_per_field": eq,
        "consensus_equals_reviewer_A_on_all_fields_all_cases":
            all(v == len(frozen) for v in eq.values()),
        "note": ("Reviewer C selected Reviewer A for every disputed field, so the final "
                 "consensus is Reviewer A's authoritative adjudication in full. Reviewer B "
                 "functions as an independent agreement check, not as a contributor to the "
                 "reference standard."),
    }

    # ---- literal vs substantive dispute routing ------------------------------
    out["adjudication"]["literal_field_level_disagreements"] = len(disputed)
    out["adjudication"]["vacuous_chapter_only_not_routed"] = len(vacuous)
    out["adjudication"]["substantive_disagreements_routed_to_C"] = len(disputed) - len(vacuous)
    out["adjudication"]["vacuous_cases"] = sorted(vacuous)
    out["adjudication"]["vacuous_definition"] = (
        "Both reviewers answered No to disposition, so the chapter question was not "
        "applicable; Reviewer A left it blank and Reviewer B wrote 'Cannot determine'. "
        "This is an encoding difference, not a substantive disagreement. The frozen plan "
        "did not define a not-applicable carve-out, so this routing is a declared "
        "post-hoc refinement, reported in full rather than applied silently.")

    # ---- write ---------------------------------------------------------------
    (HERE / "results.json").write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")
    with (HERE / "disagreements.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rowsout[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rowsout, key=lambda r: r["case_id"]))
    flat = [
        ("primary_numerator", out["primary"]["numerator"]),
        ("primary_denominator", out["primary"]["denominator"]),
        ("primary_estimate", round(out["primary"]["estimate"], 6)),
        ("primary_wilson_lo", round(out["primary"]["wilson_95_lo"], 6)),
        ("primary_wilson_hi", round(out["primary"]["wilson_95_hi"], 6)),
        ("primary_cannot_determine_as_not_confirmed", out["primary"]["cannot_determine_counted_as_not_confirmed"]),
        ("first_pass_disposition_agree", fp["disposition"]["agree"]),
        ("first_pass_disposition_n", fp["disposition"]["n"]),
        ("first_pass_identity_agree", fp["identity"]["agree"]),
        ("first_pass_identity_n", fp["identity"]["n"]),
        ("first_pass_chapter_agree", fp["chapter"]["agree"]),
        ("first_pass_chapter_n", fp["chapter"]["n"]),
        ("first_pass_date_agree", fp["petition_date"]["agree"]),
        ("first_pass_date_n", fp["petition_date"]["n"]),
        ("kappa_binary", out["kappa_binary"]["kappa"]),
        ("kappa_undefined", out["kappa_binary"]["undefined"]),
        ("cases_requiring_reviewer_C", out["adjudication"]["cases_requiring_reviewer_C"]),
        ("classifier_disposition_vs_consensus_agree_188", out["classifier_vs_consensus_all_188"]["by_classifier_disposition"]["agree"]),
        ("ai_vs_consensus_mapped_positive_agree", out["ai_vs_human_consensus_mapped_positives"]["agree"]),
        ("ai_vs_consensus_agree", out["ai_vs_human_consensus"]["agree"]),
        ("ai_vs_consensus_n", out["ai_vs_human_consensus"]["n"]),
        ("contaminated_judgements", out["deviations"]["contaminated_reviewer_case_judgements"]),
    ]
    with (HERE / "results.csv").open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["quantity", "value"])
        w.writerows(flat)
    print(json.dumps({k: v for k, v in out.items() if k != "deviations"}, indent=2)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
