---
id: TK02-implement-fetch-script
title: Implement Raw Data Fetch Script
status: todo
component: CMP-FETCH
---
# TK02 — Implement Raw Data Fetch Script

## Scope
Build the CMP-FETCH script. Scope narrowed considerably by `TK01`'s outcome: the
selected source (`IF-RAW-SOURCE`) publishes complete, stable-link CSV releases, so this
is a download-and-pin step rather than the paginated API harvest we would have needed
against an API.

Download the release tables to a versioned local location and record what was fetched:
release tag, per-file checksum, and fetch timestamp. Pinning the **release tag** — not
just "latest" — is the part that matters for `FR01-provenance-chain`: an artifact that
says "built from latest" is not reproducible, because `latest` moves every week.

Tables to fetch: `member_votes`, `votes`, `members`, `group_memberships`, plus the
subject-tag tables (`eurovoc_concept_votes`, `oeil_subject_votes`,
`geo_area_votes`, `responsible_committee_votes`) that `CMP-MINING` needs for topics.

## Acceptance criteria
- Single documented command fetches a full release; defaults to latest but accepts an
  explicit tag for reproducing a past build.
- Records release tag, file checksums, and fetch timestamp alongside the data.
- Re-fetching an already-pinned tag is idempotent (no redownload if checksums match).
- Fails loudly if an expected table is missing from the release, rather than silently
  producing a partial dataset.
