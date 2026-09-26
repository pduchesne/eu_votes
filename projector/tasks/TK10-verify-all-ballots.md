---
id: TK10-verify-all-ballots
title: Verify Every Ballot Against the Archived Record
status: todo
component: CMP-ETL
---
# TK10 — Verify Every Ballot Against the Archived Record

## Scope
Raise verification from the `TK06` sample (628 votes, 2.5%) to the whole corpus, per
`FR02-primary-record-verification`. `pipeline/spotcheck.py` already does the hard
parts and is the starting point: it joins on the XML's `Identifier` (verified equal to
our `vote_id`) and `PersId` (verified equal to our `member_id`), tolerates both XML
schema generations, and distinguishes defects in the EP's own record from
discrepancies in ours.

What changes at full scale:
- **Performance.** 17.9M ballots against 400+ XML files needs set comparison in bulk,
  not the per-vote round-trips the sampling version does.
- **The identity bridge becomes the binding constraint.** Pre-2023 XML carries no
  `PersId`; we currently bridge `MepId` from newer files and could not name ~155
  MEPs who left before the schema changed. At full scale this must be resolved
  properly — most likely from the EP's own MEP register — or the unverifiable
  remainder must be measured and published rather than glossed.
- **Reporting becomes a published figure.** Coverage is part of the platform's claim,
  so it needs to be a number citizens can see: how many ballots verified, how many
  not, and why.
- **Failure must block.** A discrepancy should stop the affected figures being
  published, not merely log a warning.

## Acceptance criteria
- Every ballot in the store is compared against the archived EP record, or explicitly
  accounted for as unverifiable with a stated reason.
- Verification runs incrementally as new sittings are archived.
- Coverage statistics are emitted into the published data for `UC05` to surface.
- Discrepancies fail the pipeline rather than being logged and passed over.
- EP-side record defects remain distinguished from our own errors.
