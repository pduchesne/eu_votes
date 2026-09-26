---
id: TK02-implement-fetch-script
title: Implement Raw Data Fetch Script
status: todo
component: CMP-FETCH
---
# TK02 — Implement Raw Data Fetch Script

## Scope
Build the CMP-FETCH script: given a term (or date range), download the raw MEP and
vote dumps from the source identified in TK01, and write them to a versioned location
with a provenance record (source, fetch timestamp, dump identifier). Replaces the
current manual placement of files into `tmp/`.

## Acceptance criteria
- Single documented command fetches raw data for a given term/date.
- Output includes a provenance record (source URL, fetch timestamp).
- No manual file placement required.
