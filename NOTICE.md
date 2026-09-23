# Licensing notice

This repository contains three kinds of material with different rights, and the
licences are applied accordingly rather than uniformly.

## 1. Original source code — MIT

Everything under `benchmark/` and `repro/` was written for EDGAR-X by the author.
MIT is applied because the intended use is for other researchers to lift the
point-in-time reconstruction, the label policy implementation and the evaluation
harness into their own work with minimal friction, including commercially, and
because the code carries no patent or trademark entanglement that would justify
a more restrictive choice.

## 2. Documentation, protocols, paper, figures and tables — CC BY 4.0

Everything under `protocols/`, `validation/` and `paper/`, and this README. These
are written work and generated exposition rather than software, so a documentation
licence fits better than a software one. CC BY 4.0 keeps reuse and quotation easy
while requiring attribution, which is the only condition the author cares about.

The working paper PDF is the author's own copyright and is released under the
same terms. Note that this may need revisiting if the paper is later submitted to
a venue that requires a copyright transfer or an exclusive licence.

## 3. Material the author does not own — no licence granted

**SEC filing content is not licensed by this repository, because it is not the
author's to license.** United States federal government works, including EDGAR
submissions and the DERA Financial Statement Data Sets, are in the public domain
in the United States; the individual filings are authored by the registrants.
**No SEC document, no extracted 10-K text and no raw filing corpus is
redistributed here.** Only derived, aggregated metrics appear, in
`benchmark/gate4_release/`.

Users acquiring source documents with the included tooling are bound by the SEC's
own access terms, including its rate limit and its requirement that requests
carry a real contact address.

**Third-party dependencies** are listed in `benchmark/requirements.txt` and remain
under their own licences. This repository neither vendors nor relicenses them.

**Cited works** in `paper/references.bib` are the property of their publishers.
The bibliography records metadata only; no copyrighted text is reproduced.

## What is deliberately absent

Reviewer packets, completed reviewer forms, the human-consensus file, the sealed
answer key and all reviewer identities are **not** published, to protect the
reviewers and to keep the validation holdout usable by others.
