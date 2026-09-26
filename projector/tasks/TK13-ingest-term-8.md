---
id: TK13-ingest-term-8
title: Ingest the 2014-2019 Term from a Second Source
status: done
component: CMP-FETCH
---
# TK13 — Ingest the 2014-2019 Term from a Second Source

## Scope
Decided in `TK08`: bring the 8th term (2014-2019) into the new pipeline so the platform
can tell decade-long stories rather than starting its history in 2019.

The primary ingest source starts at the 9th term, so this needs a second path.
**Parltrack** is that path. It was rejected in `TK01` for the current terms on
freshness — its votes dump ran roughly six months behind — but that objection does not
apply to a term that closed in 2019: the record is static, so lag is irrelevant. This
is a case where the earlier rejection was about a property of the source that only
matters for live data.

Identity reconciles cleanly, which was the main risk: parltrack's `UserID`/`mepid` is
the European Parliament's own MEP identifier, the same one the store already uses as
`member_id` (confirmed from the profile and photo URLs it embeds). An MEP serving in
both the 8th and 9th terms is therefore one person with no matching heuristics.

## What this term cannot carry
Recorded as NULLs, never as guesses, and never to be presented as equivalent to terms
9 and 10:

- **No "did not vote" records.** Parltrack lists only MEPs who voted, so participation
  and attendance figures cannot be computed for this term the way they are elsewhere.
- **No `is_main` flag**, so substantive votes cannot be separated from amendments, and
  main-vote cohesion is unavailable.
- **No EuroVoc or OEIL subject tags**, so topic stories do not reach this term.
- **Verification is weaker.** The EP's roll-call XML for this era carries only the
  internal `MepId`, with no `PersId` to join on, so ballot-level verification depends
  on an identity bridge that cannot reach MEPs who left before the schema changed.
  Tally-level verification still applies in full.

4,408 of the term's votes carry non-numeric parltrack identifiers (strings such as
`2017-12-12 00:00:00-1.`). Rather than drop them, they receive deterministic negative
ids that cannot collide with real ones.

## Outcome (2026-09-26)
11,286 votes and 7,303,183 ballots ingested; 855 MEPs and 1,304 group spells, all
reconciled to existing `member_id`s with no matching heuristics.

Two source limitations, both measured rather than estimated:
- **13,638 ballots (0.19%) name an MEP parltrack could not resolve**, recording an
  `obscure_id` placeholder instead of an identity. They are excluded, counted, and
  recorded per vote so verification can tell this known gap apart from a genuine
  disagreement with Parliament.
- **4,408 votes carry non-numeric source identifiers** and receive deterministic
  synthetic ids. Those cannot be joined to Parliament's record, so they remain
  unverified and are excluded from published figures.

## Acceptance criteria
- Term 8 votes, ballots, MEPs and group spells load into the same store as terms 9-10.
- An MEP serving across terms resolves to one `member_id`.
- Gaps above are NULL and documented, and `validate` applies term-appropriate checks
  rather than failing term 8 for lacking fields it never had.
- The roll-call archive and verification extend to term 8, with its lower ballot-level
  coverage measured and reported rather than hidden.
