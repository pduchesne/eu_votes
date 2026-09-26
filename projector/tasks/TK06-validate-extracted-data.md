---
id: TK06-validate-extracted-data
title: Validate Extracted Data
status: todo
component: CMP-ETL
---
# TK06 — Validate Extracted Data

## Scope
`PJ01` claims the data is "ready to process"; this task is what makes that a verified
statement rather than an assertion. Add automated sanity checks over the normalized
store, run as part of the pipeline (`CMP-ORCH`) rather than as a one-off notebook.

Why this is not optional: the existing codebase already demonstrates how silently
assumptions rot here. `eu_utils.py:51-52` comments "select MEPs that have voted in at
least 40% of votes" while the code filters on `len(selected_indices)*0.1` — 10%. Nobody
noticed, because nothing checked. Every published figure downstream inherits that class
of error.

Checks to cover:
- **MEP counts per term** against known values — 751 for 2014-2019, 705 after the
  UK's departure in early 2020, 720 for 2024-2029. Confirm these against the source
  rather than trusting them as written here; they are the point of the check.
- **Vote counts per term**, and per-session distribution (a term with suspiciously few
  votes in a period signals a truncated fetch — note the old
  `ep_meps_extract.ipynb` even had a leftover `if idx > 10: break` debug guard that
  would silently truncate extraction).
- **Ballot coverage** — distribution of ballots per vote and per MEP; flag votes with
  implausibly few ballots recorded.
- **Missing/absent distinction** — that "did not vote" is distinguishable from "no data
  for this MEP", since conflating them biases attendance and cohesion figures.
- **Spot-check against the primary record** — pick a handful of known votes and verify
  individual ballots against the EP's own published result. This is the only check that
  catches a systematically mis-parsed source.
- **Referential integrity** — every ballot references a known MEP and a known vote; no
  orphans.

## Acceptance criteria
- Validation runs as a pipeline stage and fails loudly on violation.
- Results are reported in a readable summary (counts, coverage rates, anomalies).
- At least one manual spot-check against the EP's published record is documented per
  term.
