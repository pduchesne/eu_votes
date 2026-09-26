---
id: TK14-recover-unjoinable-term8-votes
title: Recover Term-8 Votes That Cannot Be Joined by Identifier
status: todo
component: CMP-ETL
---
# TK14 — Recover Term-8 Votes That Cannot Be Joined by Identifier

## Scope
Roughly half the 8th term is held but not analysed: 4,408 of 11,286 votes carry a
placeholder identifier and a midnight timestamp because the source dump records them
with a date but no time. They cannot be joined to Parliament's record by identifier, so
they fail verification, and `FR02` rightly excludes unverified votes from every figure.
The result is 5,398 analysed votes against the 2019 analysis's 10,227 — the gap `FR03`
exists to close.

**82 entire sittings exist only in this form**, so this is not a rounding error and the
votes are not duplicates of anything: 137 sittings are timed-only, 82 midnight-only,
and 11 mixed. Only the mixed sittings contain apparent duplicates (~1,033).

### Approach
Join on what the two sides actually share instead of on an identifier:
1. **Date plus tally signature** (for/against/abstention). Tested on 2018-12-12: all
   323 votes matched uniquely this way.
2. **Ballot-set comparison** where several votes in a sitting share a tally signature.
   We hold the individual ballots and so does Parliament's document, so this is
   near-definitive rather than a heuristic.
3. Anything still ambiguous stays unverified. Recovering coverage must not come at the
   cost of matching the wrong vote — a mismatched join would corrupt exactly the
   figures this project exists to make trustworthy.

Deduplicate the ~1,033 mixed-sitting records in the same pass, keeping the timed
record, since it carries the identifier and the precise timestamp.

## Acceptance criteria
- Analysed term-8 votes reach at least 10,227 (`FR03`), or the residual is explained
  vote by vote.
- Every recovered vote is verified against Parliament's record by ballots, not merely
  by tallies, wherever the document permits it.
- Duplicates removed; `votes-t8.json` no longer ships them.
- Ambiguous cases remain unverified and excluded rather than being guessed.
