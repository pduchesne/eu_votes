---
id: TK14-recover-unjoinable-term8-votes
title: Recover Term-8 Votes That Cannot Be Joined by Identifier
status: in-progress
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

## Status (2026-09-26)
Term-8 analysed coverage went from **5,398 to 10,112** votes, against the 2019
analysis's 10,227 and Parliament's 10,281. Extracted coverage is 10,756, ahead of the
old pipeline.

Matching, in order of confidence — 10,112 of Parliament's 10,281 results bound:
- **identifier** 6,375, all verified (100%)
- **tally signature** 3,375, all verified (100%)
- **ballot agreement** 362, where tallies collide within a sitting

Verification caught a real mistake here and is worth recording. A first ballot
threshold (95% agreement, 5% margin) bound 503 votes, of which 141 then failed
verification — they were plausible-looking matches to the *wrong* same-tally vote.
Tightening to 99.5% agreement and a 15% margin kept exactly the 362 sound ones and
dropped every bad one. Coverage bought with wrong bindings is worse than no coverage.

530 duplicate records flagged and excluded from published output: sittings the source
records both with times and without.

**Outstanding:**
- 644 votes remain unmatched — tally collisions within a sitting where ballot
  agreement cannot separate the candidates safely. Closing the last 115 against the
  2019 baseline means resolving these, not loosening the threshold.
- Extracted count (10,756) still exceeds Parliament's 10,281, so roughly 475 further
  duplicates are likely present beyond the 530 already found.

## Acceptance criteria
- Analysed term-8 votes reach at least 10,227 (`FR03`), or the residual is explained
  vote by vote.
- Every recovered vote is verified against Parliament's record by ballots, not merely
  by tallies, wherever the document permits it.
- Duplicates removed; `votes-t8.json` no longer ships them.
- Ambiguous cases remain unverified and excluded rather than being guessed.
