---
id: TK10-verify-all-ballots
title: Verify Every Ballot Against the Archived Record
status: done
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

## Outcome (2026-09-26)
Whole-corpus verification, superseding TK06's 2.5% sample.

| Term | Checked | Verified | Unverified |
|---|---|---|---|
| T8 | 6,375 | 5,398 | 977 |
| T9 | 19,098 | 19,091 | 7 |
| T10 | 5,926 | 5,925 | 1 |

**30,414 of 36,490 votes (83.3%) verified against Parliament's own record.** The two
terms with complete metadata are 99.96%+ clean; the shortfall is concentrated in the
8th term and is characterised rather than mysterious.

Three distinctions the checker now draws, each of which changes the number materially:
- **Members Parliament lists but we cannot name** (older documents carry no `PersId`)
  are charged to neither side. An earlier version intersected our ballots with the
  bridge's range instead, which manufactured ~150 phantom T9 discrepancies — the fix
  came from checking one flagged vote by hand and finding Parliament's record agreed
  with us exactly.
- **Gaps our own ingest already declared** are matched against a per-vote record of
  what parltrack could not attribute. 4,643 gaps reconcile exactly this way, which is
  the difference between "5,620 discrepancies" and a quantified source limitation.
- **Defects in Parliament's own record** — 3,807 of them, including results with no
  identifier and `PersId="UNKNOWN"` — are reported as EP-side, never charged to us.

4,983 votes in the store have no counterpart in the archived record at all (mostly 8th
term votes whose source identifiers are synthetic). They count as unverified.

Per FR02, unverified votes are excluded from every published figure: mining draws only
on verified ballots, and each published vote carries its own status.

## Acceptance criteria
- Every ballot in the store is compared against the archived EP record, or explicitly
  accounted for as unverifiable with a stated reason.
- Verification runs incrementally as new sittings are archived.
- Coverage statistics are emitted into the published data for `UC05` to surface.
- Discrepancies fail the pipeline rather than being logged and passed over.
- EP-side record defects remain distinguished from our own errors.
