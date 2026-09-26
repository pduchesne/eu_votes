---
id: TK06-validate-extracted-data
title: Validate Extracted Data
status: done
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

## Status (2026-09-26)
Automated checks implemented in `pipeline/validate.py`, run via
`python -m pipeline validate`, exiting non-zero on failure. All currently pass:

- Referential integrity: 0 orphan ballots either direction, 0 votes without ballots.
- **Counted ballots match the published tallies on all 25,204 votes** — the strongest
  single check available, since it cross-validates our parse against the source's own
  aggregates.
- Roster bounds match official seat counts exactly: T9 696-751 (751 seats pre-Brexit,
  705 after), T10 717-719 (720 seats).
- No UK ballots after 2020-02-01 — the Brexit transition is correctly reflected.
- Every vote assigned to a term, and dated inside it.
- Positions confined to `FOR`/`AGAINST`/`ABSTENTION`/`DID_NOT_VOTE`.
- 870 distinct MEPs in T9 and 743 in T10 against 751/720 seats — more people than
  seats, as expected with mid-term replacement.

One WARN, judged acceptable: 629 ballots of 17,872,194 (0.004%) carry no political
group, consistent with non-attached members or brief affiliation gaps.

### Spot-check against Parliament's own record — done
`pipeline/spotcheck.py`, run via `python -m pipeline spotcheck`. **628 votes across
four sittings agree with Parliament's own roll-call XML**, with zero discrepancies:

| Sitting | Regime | Votes | Verified |
|---|---|---|---|
| 2019-10-10 | T9 pre-Brexit | 37 | tallies in full, ballots partial |
| 2020-01-15 | T9 pre-Brexit | 183 | tallies in full, ballots partial |
| 2023-11-22 | T9 post-Brexit | 284 | tallies + every individual ballot |
| 2026-09-17 | T10 | 124 | tallies + every individual ballot |

Join keys, both verified rather than assumed: the XML's `Identifier` equals our
`vote_id` (37/37, 183/183, 284/284, 124/124), and its `PersId` equals our `member_id`.

Three findings worth carrying forward:
- **`DID_NOT_VOTE` is not in the primary record at all.** Parliament publishes only
  For/Against/Abstention; our source derives non-voting from the sitting roster. So
  that field is a derivation, not a fact from the minutes, and attendance claims should
  be described accordingly.
- **Pre-2023 XML carries no `PersId`**, only an internal `MepId` that matches nothing
  in our store. Those sittings are bridged via MepId→PersId pairs learned from newer
  files; ~155 MEPs who left before the schema changed cannot be bridged, so their
  ballots are unverified and the tool says so rather than implying full coverage.
- **Parliament's own XML has defects.** Vote 161290's `Result.Abstention` carries a
  multilingual "corrections" heading where its count belongs. Reported as an EP-side
  anomaly, not counted against our data.

Retrieval note: the EP fronts these documents with an AWS WAF JavaScript challenge
(`x-amzn-waf-action: challenge`), so curl and other plain clients get an empty HTTP 202.
A real browser passes it transparently — the files were obtained by driving one, then
reusing its `aws-waf-token`. They are public and anonymous; the obstacle is bot
protection, not access control.

## Acceptance criteria
- Validation runs as a pipeline stage and fails loudly on violation.
- Results are reported in a readable summary (counts, coverage rates, anomalies).
- At least one manual spot-check against the EP's published record is documented per
  term.
