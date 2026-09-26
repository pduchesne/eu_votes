---
id: IF-RAW-SOURCE
title: EP Raw Data Source (HowTheyVote dataset)
status: provided
required: true
---
# IF-RAW-SOURCE — EP Raw Data Source

### Purpose
The external source of raw MEP and roll-call ballot data consumed by `CMP-FETCH`.
Selected in `TK01` after comparing three candidates; see `docs/data-source.md` for the
full comparison and rationale.

**Selected: the HowTheyVote.eu dataset** — weekly CSV releases published at
`https://github.com/HowTheyVote/data/releases`, under the Open Database License
(ODbL), derived by HowTheyVote from the EP's own plenary minutes and Legislative
Observatory.

**Primary record for verification: the EP's DOCEO roll-call XML**, published per
sitting as part of the plenary minutes
(`europarl.europa.eu/doceo/document/PV-{term}-{date}-RCV_EN.xml`). Because the selected
source is a third-party derivation, `TK06` spot-checks published figures against this
primary record.

### Key capabilities / Conformance classes
Verified directly against the 2026-09-26 release:
- `member_votes.csv` — **individual ballots**: `vote_id, member_id, position, country_code, group_code`,
  where position is `FOR | AGAINST | ABSTENTION | DID_NOT_VOTE`. Note that
  "did not vote" is recorded explicitly rather than inferred from absence, which the
  old CSV could not distinguish.
- `votes.csv` — 25,204 votes, 2019-07-15 to 2026-09-17, with timestamp, title,
  procedure reference/type/stage, aggregate counts, result, and `is_main`
  (2,462 main votes vs 22,742 amendment/procedural).
- `members.csv` — 1,279 MEPs across both terms, under **one stable `member_id`**.
- `group_memberships.csv` — `member_id, group_code, term, start_date, end_date`:
  affiliation over time, not a flattened "current group".
- `eurovoc_concept_votes.csv`, `oeil_subject_votes.csv`, `geo_area_votes.csv`,
  `responsible_committee_votes.csv` — authoritative subject tags per vote.

### Coverage and limits
- Starts at the **9th term (2019)**. The 2014-2019 term is *not* available here — see
  `TK08`, whose "keep three terms" option would require a second, different source.
- HowTheyVote state that collection is fully automated and they "cannot rule out that
  individual votes are missing or contain errors" — the reason `TK06` validation is a
  milestone gate rather than a nicety.
- Roll-call votes only. Votes by show of hands or secret ballot are not recorded by
  anyone, including the EP, so they are out of reach by nature.

### Key endpoints
Stable latest-release links, verified returning HTTP 200:
`https://github.com/HowTheyVote/data/releases/latest/download/<table>.csv.gz`
(`member_votes` 68.5MB, `votes` 784KB, `members` 39KB, `group_memberships` 9.5KB, plus
the subject-tag tables; `export.zip` bundles all at 70MB).
