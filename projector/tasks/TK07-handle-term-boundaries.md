---
id: TK07-handle-term-boundaries
title: Handle Terms and MEP Identity in the Store Schema
status: todo
component: CMP-ETL
---
# TK07 — Handle Terms and MEP Identity in the Store Schema

## Scope
Decide and implement how the normalized store (`IF-DATASTORE`) represents terms and MEP
identity. This gates `TK03`: it is a schema decision, and schema decisions are
expensive to revisit once two terms of data and downstream mining depend on them.

The old code never faced this — it handled a single term with a flat "current group"
per MEP and time slices within that term. Holding two terms at once breaks those
assumptions:

- **Term as a first-class dimension.** Votes and rosters must be term-scoped so the two
  terms coexist without collision.
- **MEP identity across terms.** Verify whether MEP identifiers are stable across
  terms, and model an MEP serving in multiple terms as one person with multiple
  mandates — not two unrelated rows — otherwise per-person history is impossible.
- **Mid-term roster changes.** MEPs arrive and leave mid-term (resignations,
  replacements, deaths). The 2019-2024 term also contains the UK's departure and the
  resulting seat redistribution, so "the roster" is not constant within that term.
  Group affiliation also changes mid-term, which the old single `current_group` field
  simply flattened away — losing the ability to say who an MEP sat with at the time of
  a given vote.
- **Attendance denominators.** With a changing roster, "votes an MEP could have voted
  in" is per-mandate, not per-term. Getting this wrong quietly distorts every
  attendance and cohesion figure.

### Downstream consequence to flag, not solve here
PCA axes from independently-fitted per-term models are not comparable: sign and
rotation are arbitrary, so "moved left between terms" is meaningless without an
explicit alignment choice (joint fit across terms, or per-term fit plus Procrustes
alignment). That decision belongs to `CMP-MINING`, but it constrains what the store must
retain — so record the requirement here and decide it before mining is built.

## Acceptance criteria
- Store schema documents how terms, MEPs, mandates, and group affiliations over time are
  represented.
- An MEP serving in both in-scope terms resolves to a single person with two mandates.
- Group affiliation is resolvable as-at the date of any given vote.
- Attendance denominators are computable per mandate, not per term.
