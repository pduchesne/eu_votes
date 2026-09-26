---
id: TK03-implement-etl-normalize
title: Implement ETL Normalization Script
status: done
component: CMP-ETL
---
# TK03 — Implement ETL Normalization Script

## Scope
Build the CMP-ETL script: parse raw dumps (from CMP-FETCH) into a normalized,
queryable store (DuckDB or Parquet) covering MEPs, votes, and individual ballots.
Replaces `ep_meps_extract.ipynb`/`ep_votes_extract.ipynb` (one of which no longer runs,
being stuck on Python 2 syntax) and the current loose `computed/*.json` + 70MB CSV
outputs. Carries forward provenance metadata from CMP-FETCH.

Gated by two decisions: `TK01` (which source, hence which input format) and `TK07`
(how terms, MEP identity, and mid-term affiliation changes are represented). Both are
expensive to retrofit once two terms of data exist, so settle them first.

## Acceptance criteria
- Single documented command normalizes a raw dump set into the store.
- Store replaces the wide `meps_votes.csv` with a queryable, versionable format, and
  conforms to `IF-DATASTORE`.
- Provenance metadata is preserved end-to-end from fetch to normalized store.
