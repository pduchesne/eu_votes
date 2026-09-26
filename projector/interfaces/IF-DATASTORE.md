---
id: IF-DATASTORE
title: Normalized Vote Store
status: auto
required: false
implementedBy: CMP-ETL
---
# IF-DATASTORE — Normalized Vote Store

### Purpose
The queryable store of normalized EP data — MEPs, votes, and individual ballots —
produced by `CMP-ETL` and consumed by `CMP-MINING` (and by `CMP-PUBLISH` for
descriptive fields). This is the contract that defines "extracted and ready to
process", and therefore the deliverable of `PJ01-data-extraction-foundation`.

Replaces today's loose `computed/*.json` files plus the single wide 70MB
`meps_votes.csv` (MEPs × votes), which is neither queryable nor incrementally
updatable.

### Key capabilities / Conformance classes
- MEP roster per term, including mid-term arrivals/departures.
- Votes with title, date, and source reference.
- Individual ballots (For/Against/Abstain/absent) per MEP per vote.
- Term as a first-class dimension, so multiple terms coexist without collision
  (see `TK07-handle-term-boundaries`).
- Provenance fields traceable back to the source dump/fetch (see
  `FR01-provenance-chain`).

### Key endpoints
Local store (DuckDB or Parquet); accessed in-process by the pipeline steps, not over
a network protocol.
