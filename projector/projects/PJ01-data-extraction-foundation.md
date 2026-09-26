---
id: PJ01-data-extraction-foundation
title: Data Extraction Foundation
status: done
members:
  - UC03.01-acquire-data
  - CMP-FETCH
  - CMP-ETL
  - CMP-ORCH
  - IF-RAW-SOURCE
  - IF-DATASTORE
  - FR01-provenance-chain
  - TK01-identify-document-raw-source
  - TK07-handle-term-boundaries
  - TK02-implement-fetch-script
  - TK03-implement-etl-normalize
  - TK04-extract-previous-term
  - TK05-extract-current-term
  - TK06-validate-extracted-data
---
# PJ01 — Data Extraction Foundation

First milestone: have EP vote and MEP data for the current term (2024-2029, to date)
and the previous term (2019-2024) fetched, documented, and normalized into a
queryable store — ready for the mining pipeline (`CMP-MINING`), but not yet mined or
published. Delivers `UC03.01-acquire-data`; `UC03.02-mine-and-publish` is explicitly
out of scope.

Scope is deliberately narrow: no mining, no UI. Success is a reproducible,
documented, provenance-tagged fetch → normalize step whose output is *verified*
(`TK06`), replacing today's manual `tmp/*.json` placement and the fragile, partly
Python-2-broken extraction notebooks.

## Sequencing
Two decisions gate the build and should be settled first:
1. `TK01` — which source (official EP open data portal vs parltrack). Determines
   whether fetch is bulk-download or incremental API harvest.
2. `TK07` — how terms, MEP identity, and mid-term affiliation changes are modelled.
   Determines the store schema.

Then `TK02`/`TK03` (build), `TK04`/`TK05` (run for each term), and `TK06` (validate)
— with `TK06` as the actual definition of done for the milestone, since "ready to
process" is otherwise an untested claim.

## Delivered (2026-09-26)
`python -m pipeline fetch|etl|validate|spotcheck|all` produces a provenance-tagged
DuckDB store holding **25,204 roll-call votes and 17.9M ballots** across T9 and T10.

"Ready to process" is a checked claim, not an assertion: 13 automated checks pass, and
628 votes across four sittings were verified against Parliament's own roll-call XML
with zero discrepancies — including every individual ballot on the two sittings whose
XML permits it.

Carried into `PJ02`: `DID_NOT_VOTE` is derived rather than published, so attendance
figures must be described as roll-call participation; and 90% of rows are
amendment/procedural votes, so `is_main` has to be respected in any aggregate.

No deadline was set.
