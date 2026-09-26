---
id: PJ02-analysis-and-contract
title: Analysis & Published-Data Contract
status: done
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
  - TK13-ingest-term-8
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

`TK13` brings the 2014-2019 term into the pipeline from a second source, following the
decision recorded in `TK08`. It lands in this milestone because the mining and
published contract must be shaped for three terms from the start rather than retrofitted.

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

## Delivered (2026-09-26)
`python -m pipeline all` now runs fetch → term8 → etl → validate → archive → verify →
mine → publish, and emits the `IF-PUBLISHED-DATA` bundles:

| Bundle | Size | Contents |
|---|---|---|
| `meps.json` | 558 KB | 1,279+ MEPs: groups, terms, loyalty, 3D positions |
| `groups.json` | 4 KB | per-term group cohesion, all votes and main votes |
| `topics.json` | 15 KB | per-topic group support, from EP subject codes |
| `votes-t8/9/10.json` | 4.9 / 8.4 / 2.6 MB | per-vote record, EP citation, verification flag |
| `meta.json` | 2 KB | provenance, verification coverage, caveats |

Three terms (2014-2029), 36,490 votes, 25.2M ballots. 577 EP roll-call documents
archived; 30,414 votes (83.3%) verified against Parliament's own record, and figures
are built from verified ballots only.

Both decisions this milestone owed are taken:
1. **Cross-term comparability** — per-term PCA fits rotated into one frame by
   orthogonal Procrustes on shared MEPs (307 for T8, 337 for T10), with T9 as reference
   since it is the only term overlapping both others. A joint fit was rejected: the
   vote sets are disjoint, so the leading component would merely encode which term.
2. **The published contract** — frozen as the bundles above. `PJ03` builds against it.

Analysis sanity, which matters more than the pipeline running: results are politically
recognisable. Mainstream groups sit at 94-96% cohesion, non-attached members at 66%,
and PC1 orders ESN/PFE/ECR → EPP → RENEW → S&D/Greens — the EP's documented
pro/anti-integration axis, recovered rather than imposed.

Carried into `PJ03`: `TK11`'s UI half (linking each vote to Parliament's record and
marking unverified ones), and the wording discipline that participation figures are
*roll-call* participation, since Parliament does not publish non-voting at all.

No deadline was set.
