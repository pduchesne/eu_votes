---
id: TK05-extract-current-term
title: Extract and Normalize Current Term (2024-2029, to date)
status: done
component: CMP-ETL
---
# TK05 — Extract and Normalize Current Term (2024-2029, to date)

## Scope
Run CMP-FETCH + CMP-ETL end-to-end for the current, ongoing EP term (2024-2029),
producing a normalized store covering all votes cast to date. Since the term is
ongoing, this task also validates that a later re-run (TK02/TK03 scripts) can pick up
new votes incrementally.

## Acceptance criteria
- Normalized store contains 2024-2029 term MEP roster and all votes cast to date.
- Re-running the fetch/ETL scripts later picks up new votes without manual
  intervention.
