---
id: CMP-FETCH
title: Raw Data Fetcher
status: done
node: Platform
uses:
  IF-RAW-SOURCE: pull raw MEP and vote dumps from the EP data source
---
# CMP-FETCH — Raw Data Fetcher

### Function
Scripted retrieval of raw EP vote and MEP data, replacing the current undocumented
manual step of dropping dated JSON dumps into `tmp/`.

### Technology
Python script (e.g. `requests`/`httpx`), invoked via CLI, no notebook dependency.

### Responsibilities
- Pull raw MEP and vote data from the documented source (`IF-RAW-SOURCE`).
- Record provenance for each fetch: source URL, fetch timestamp, dump identifier.
- Write raw dumps to a versioned location so CMP-ETL has a stable, dated input.

### Data
Output: raw dated JSON dumps (successor to `tmp/ep_meps_current.<date>.json` and
`tmp/ep_votes.<date>.json`) plus a provenance record (source, timestamp).
