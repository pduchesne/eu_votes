---
id: TK01-identify-document-raw-source
title: Select and Document the Raw EP Data Source
status: done
component: CMP-FETCH
---
# TK01 — Select and Document the Raw EP Data Source

## Outcome (2026-09-26)
**Selected: the HowTheyVote.eu dataset** (weekly ODbL CSV releases), with the EP's own
DOCEO roll-call XML as the primary record for verification. Full comparison and
rationale: `docs/data-source.md`; source contract: `IF-RAW-SOURCE`.

The decisive finding: **the official EP Open Data API exposes only aggregate vote
tallies, not individual ballots** — so the authoritative-source-first instinct does not
survive contact with what the API actually serves. Individual ballots are published by
the Parliament only as XML attached to each sitting's minutes. Parltrack was rejected
on freshness (votes dump six months stale at time of checking, versus HowTheyVote's
weekly cadence).

Consequences recorded against other tasks:
- `TK02` shrinks to downloading stable-link CSVs and pinning a release tag — no
  paginated API harvest.
- `TK07` shrinks substantially: the source already carries term-scoped group
  memberships with start/end dates, and a single stable `member_id` across terms.
- `CMP-MINING`'s topic classification is largely pre-solved by the EuroVoc and OEIL
  subject tables (see `PJ02`).
- `TK08`'s "keep 2014-2019" option now carries a real cost: that term is not in this
  source and would require a second one (parltrack).
- `TK06` matters more, not less: we ingest a third-party derivation whose authors
  state it is automated and may contain errors.

## Scope
This is a fork in the road, not a formality: the chosen source determines whether
`CMP-FETCH` is a bulk-dump downloader or an incremental paginated API harvester with a
local cache, which in turn changes `TK02`'s and `TK03`'s acceptance criteria. Do this
before building either.

The repo has no documented source today — `tmp/ep_meps_current.<date>.json` and
`tmp/ep_votes.<date>.json` simply appear. Field names in the existing extraction
notebooks (`UserID`, `Groups`, `Constituencies`, `meta.url`, per-group `votes` with
`ep_id`) match parltrack.org's dump format, which is the incumbent candidate.

Since 2019 the European Parliament also runs an official open data portal
(`data.europarl.europa.eu`). For a project whose stated purpose is democratic
transparency, an authoritative, citable primary source is preferable on exactly the
axis that matters — so evaluate it seriously rather than defaulting to the incumbent.

Compare the candidates on:
- **Ballot-level completeness** — the decisive criterion. Aggregate roll-call results
  are useless here; the project needs each MEP's individual For/Against/Abstain per
  vote. Verify this directly rather than assuming; historically the hard part with
  official EP sources has been that individual ballots are published as documents
  rather than clean structured data, which is precisely the normalization parltrack
  already did.
- **Licence and citability** — can published figures cite a stable, referenceable
  source?
- **Stability and availability** — update cadence, and the risk of the source going
  away (a third-party mirror is a single point of failure for the whole project).
- **Parse cost** — pre-normalized JSON versus documents needing extraction.

Recording *why* the loser was rejected matters as much as the choice: that rationale is
part of the transparency story (`FR01-provenance-chain`).

## Acceptance criteria
- `IF-RAW-SOURCE` updated with the selected source, its endpoint(s)/dump URL(s), and
  format.
- The comparison and its rationale are written down (e.g. `docs/data-source.md`), in
  plain language, including why the alternative was not chosen.
- Confirmed by inspection that the selected source exposes individual MEP ballots, not
  just aggregate results, for both terms in `PJ01` scope.
- If the outcome changes the fetch model (bulk vs incremental), `TK02` and `TK03` are
  updated accordingly before implementation starts.
