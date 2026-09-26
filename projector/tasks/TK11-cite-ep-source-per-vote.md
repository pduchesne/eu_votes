---
id: TK11-cite-ep-source-per-vote
title: Cite Parliament's Document on Every Published Vote
status: todo
component: CMP-PUBLISH
---
# TK11 — Cite Parliament's Document on Every Published Vote

## Scope
The user-visible half of `FR02-primary-record-verification`. The platform's authority
is europarl.europa.eu, so what a citizen sees must point there — not at our ingest
supplier, and not at our own database.

Every published vote carries a link to its EP source document and its verification
status, so a reader can go from a claim on a chart to Parliament's own record in one
step. This is what makes `UC05` more than a methodology page: the citation is per-vote
and specific, rather than a general statement about where data comes from.

Wording matters here and is part of the task, not decoration:
- Figures derived from ballots are *roll-call* figures. `DID_NOT_VOTE` is not published
  by Parliament — it is inferred from the sitting roster — so attendance must be
  described as roll-call participation rather than attendance in general.
- Votes whose ballots could not be verified must say so, rather than being silently
  presented alongside verified ones.

## Acceptance criteria
- Each vote in `IF-PUBLISHED-DATA` carries its EP document reference and a
  verification flag.
- The UI links from any vote to Parliament's own record.
- Unverified or partially verified votes are visibly marked as such.
- Attendance-style figures are labelled as roll-call participation wherever they appear.
