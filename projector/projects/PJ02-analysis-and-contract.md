---
id: PJ02-analysis-and-contract
title: Analysis & Published-Data Contract
status: planning
members:
  - UC03.02-mine-and-publish
  - CMP-MINING
  - CMP-PUBLISH
  - CMP-ORCH
  - IF-PUBLISHED-DATA
  - FR01-provenance-chain
  - FR02-primary-record-verification
  - TK09-archive-ep-rollcall-record
  - TK10-verify-all-ballots
  - TK12-review-data-licensing
  - TK08-retire-legacy-pipeline
---
# PJ02 — Analysis & Published-Data Contract

Second milestone: turn the normalized store from `PJ01` into the analysis layer and
freeze the `IF-PUBLISHED-DATA` contract the UI will consume. Delivers
`UC03.02-mine-and-publish`.

Scope:
- PCA political positioning (carried over from the existing `DataMining.ipynb`
  approach, but as scripted pipeline code).
- Per-MEP group-cohesion / loyalty scoring — new, and the figure most directly useful
  to `UC01` and `UC02`.
- Topic classification of votes — new, and the prerequisite for `UC04`'s topic
  stories; absent from the current codebase entirely.
- Emit versioned, provenance-tagged JSON bundles sized for browser consumption.

Two decisions land here:
1. **Cross-term PCA comparability** (raised in `TK07`) — joint fit across terms, or
   per-term fit plus Procrustes alignment. Determines whether the 3D view can
   meaningfully show movement between terms, so decide before `PJ03` designs the
   navigation.
2. **The published contract itself** — once `PJ03` builds against it, changing its
   shape costs UI rework, so it is worth stabilising deliberately at the end of this
   milestone.

`TK08` (retiring the legacy pipeline) sits here rather than in `PJ01`, because until
this milestone publishes something, the old static report is the only output the
project has.

`TK09`/`TK10` (archiving Parliament's roll-call record and verifying every ballot
against it) also sit here rather than in `PJ01`, even though they are data-layer work.
The reason is sequencing, not category: `FR02` requires that a figure cannot be
published unless its ballots are verified, so full verification has to be in place by
the time this milestone first publishes anything. `TK12` (licensing) belongs here for
the same reason — it constrains what the published bundles may contain and under what
terms.

No deadline set yet.
