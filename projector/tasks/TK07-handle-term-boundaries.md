---
id: TK07-handle-term-boundaries
title: Handle Terms and MEP Identity in the Store Schema
status: done
component: CMP-ETL
---
# TK07 — Handle Terms and MEP Identity in the Store Schema

## Scope
Decide and implement how the normalized store (`IF-DATASTORE`) represents terms and MEP
identity. Gates `TK03`, because schema decisions are expensive to revisit once two
terms of data and downstream mining depend on them.

`TK01` removed much of the difficulty that was anticipated here. The selected source
already provides, verified against a real release:
- a single stable `member_id` spanning both terms (1,279 MEPs in one table), so a
  person serving twice is already one person;
- `group_memberships` with `term`, `start_date`, `end_date`, so affiliation is a
  time-bounded fact rather than the flattened `current_group` the old pipeline stored;
- `group_code` and `country_code` denormalized onto each ballot, i.e. affiliation
  as-at the vote is available without a join.

### What still needs deciding
- **Term as a store dimension.** The source keys votes by timestamp, not term. Derive
  term explicitly (T9 begins 2019-07-02, T10 begins 2024-07-16) so per-term queries
  don't rely on every caller re-deriving date arithmetic.
- **Mandates.** `group_memberships` gives group spells, but an MEP's *mandate* (when
  they actually sat) is a distinct fact — and this term's roster is not constant:
  members resign and are replaced mid-term. Decide whether mandate is modelled
  explicitly or inferred from first/last observed ballot.
- **Attendance denominators.** "Votes an MEP could have voted in" must be computed per
  mandate, not per term, or every attendance and cohesion figure is distorted for
  anyone who did not serve the full five years. `DID_NOT_VOTE` rows help but do not
  settle it: an MEP absent from the file entirely for a sitting is different from one
  recorded as not voting.
- **The UK's departure.** Term 9 contains pre- and post-Brexit rosters (verified:
  `GBR` ballots are present in the data). Any per-country or per-term aggregate must
  handle a membership that changes size mid-term.

### Downstream consequence to flag, not solve here
PCA axes from independently-fitted per-term models are not comparable: sign and
rotation are arbitrary, so "moved left between terms" is meaningless without an
explicit alignment choice (joint fit across terms, or per-term fit plus Procrustes
alignment). That decision belongs to `CMP-MINING` in `PJ02`, but it constrains what the
store must retain — so record it here and settle it before mining is built.

## Outcome (2026-09-26)
Implemented in `pipeline/etl.py`:
- **Terms are explicit.** A `terms` table (T9 from 2019-07-02, T10 from 2024-07-16) plus
  a `votes.term` column, populated by join rather than re-derived by each caller. The
  ETL aborts if any vote falls outside all known terms, so extending to T11 fails loudly
  instead of silently mislabelling.
- **MEP identity is already unified upstream** — 1,279 MEPs across both terms under one
  `member_id`, so no cross-term reconciliation was needed.
- **Mandates and attendance denominators are solved by the source's shape.** The source
  emits a ballot row for every *sitting* MEP on every vote, including an explicit
  `DID_NOT_VOTE`. Verified: ballots per vote are 696-751 in T9 (751 seats pre-Brexit,
  705 after) and 717-719 in T10 (720 seats) — i.e. roster-sized. So an MEP's attendance
  denominator is simply the count of votes where they appear at all, and a mandate is
  inferable from first/last appearance. No separate mandate table was needed, and
  building one would have duplicated a fact the data already carries.
- **Group affiliation as-at the vote** is available two ways: `group_memberships`
  (term + start/end dates) and `group_code` denormalized onto each ballot.

## Acceptance criteria
- Store schema documents how terms, MEPs, mandates, and group affiliation over time are
  represented.
- Group affiliation is resolvable as-at the date of any given vote.
- Attendance denominators are computable per mandate, not per term.
- Term is an explicit, queryable column rather than derived ad hoc by each caller.
