"""Rebuild every public table and figure from the frozen release CSVs and compare.

Reads only `benchmark/gate4_release/*.csv`. No model is fitted, no bootstrap is
regenerated and no label is recomputed; the scripts perform deterministic
transformations of already-frozen values.

Figure PDFs embed a creation timestamp, so they are compared with `/CreationDate`
stripped. Everything else is compared byte for byte. Any mismatch is reported,
never corrected.
"""
from __future__ import annotations
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAB, FIG, REPRO = ROOT / "paper/tables", ROOT / "paper/figures", ROOT / "repro"
FIGS = ("fig1_pipeline", "fig2_ap_by_cohort", "fig3_text_increment",
        "fig4_review_budget", "fig5_contamination_channels")


def canon(p: Path) -> bytes:
    b = p.read_bytes()
    return re.sub(rb"/CreationDate \([^)]*\)", b"", b) if p.suffix == ".pdf" else b


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        keep = Path(tmp)
        for d in (TAB, FIG):
            shutil.copytree(d, keep / d.name)

        subprocess.run([sys.executable, "build_tables.py"], cwd=REPRO, check=True,
                       stdout=subprocess.DEVNULL)
        for f in FIGS:
            subprocess.run([sys.executable, f"{f}.py"], cwd=REPRO, check=True,
                           stdout=subprocess.DEVNULL)

        bad = []
        for d in (TAB, FIG):
            for cur in sorted(d.iterdir()):
                if cur.name.startswith("."):
                    continue
                ref = keep / d.name / cur.name
                if not ref.exists():
                    bad.append(f"{cur.name}: new file, not in the frozen set")
                elif canon(cur) != canon(ref):
                    bad.append(f"{cur.name}: content differs from the frozen artifact")
                else:
                    print(f"  OK   {d.name}/{cur.name}")
        # restore the shipped artifacts so a verification run leaves no diff
        for d in (TAB, FIG):
            shutil.rmtree(d); shutil.copytree(keep / d.name, d)

    if bad:
        print("\nMISMATCHES (reported, not corrected):", file=sys.stderr)
        for b in bad:
            print("  " + b, file=sys.stderr)
        return 1
    print("\nAll public tables and figures reproduce from the frozen release CSVs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
