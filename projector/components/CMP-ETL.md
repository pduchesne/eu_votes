---
id: CMP-ETL
title: Normalize & Load
status: done
node: Platform
---
# CMP-ETL — Normalize & Load

### Function
Parses raw dumps into a normalized, queryable store, replacing the current
`ep_meps_extract.ipynb` / `ep_votes_extract.ipynb` notebooks (one of which no longer
runs, being stuck on Python 2 syntax) and the loose `computed/*.json` + 70MB CSV
outputs.

### Technology
Python script; normalized store as DuckDB or Parquet rather than a single wide CSV.

### Responsibilities
- Parse raw MEP and vote dumps into normalized tables (MEPs, votes, individual
  ballots).
- Carry forward provenance metadata from CMP-FETCH.
- Be runnable as a single scripted step, independent of manual notebook ordering.

### Data
Input: raw dumps from CMP-FETCH. Output: normalized DuckDB/Parquet store consumed by
CMP-MINING.
