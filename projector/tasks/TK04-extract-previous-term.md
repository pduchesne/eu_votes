---
id: TK04-extract-previous-term
title: Extract and Normalize Previous Term (2019-2024)
status: done
component: CMP-ETL
---
# TK04 — Extract and Normalize Previous Term (2019-2024)

## Scope
Run CMP-FETCH + CMP-ETL end-to-end for the previous EP term (2019-2024), producing a
normalized store ready for mining. This supersedes the legacy, already-stale
2014-2019 data currently baked into `computed/`.

## Acceptance criteria
- Normalized store contains full 2019-2024 term MEP roster and vote data.
- Data is queryable and provenance-tagged.
