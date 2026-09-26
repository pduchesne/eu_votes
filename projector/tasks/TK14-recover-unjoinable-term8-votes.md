---
id: TK14-recover-unjoinable-term8-votes
title: Recover Term-8 Votes That Cannot Be Joined by Identifier
status: done
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

## Outcome (2026-09-26)
Analysed term-8 coverage went from **5,398 to 10,112**; extracted is 10,253, within
Parliament's own 10,281 and above the 2019 analysis's 10,227.

The decisive discriminator turned out to be neither identifiers nor tallies but the
**vote's own reference**, which both sides record verbatim in the description. Validated
against 498 identifier-matched votes it agreed 498/498, and it bound 3,798 votes that
no identifier could reach. It should have been the first thing tried.

Matching, in order of confidence: identifier 6,375, title 3,798, tally 80. Nothing is
left ambiguous, and 1,033 duplicate records are flagged — a figure that now reconciles
exactly with Parliament's count (11,286 held − 1,033 = 10,253).

### The residual 141 are not a matching failure
Inspected individually: title and all three tallies agree exactly, but our source and
Parliament attribute one ballot to different members. These are genuine disagreements
about who voted how, which is precisely what verification exists to surface, and they
are excluded because publishing them would mean publishing figures that contradict
Parliament's record. The 2019 analysis included them only because it never checked.

**Closing the last 115 against the 2019 baseline therefore means resolving those
disagreements with Parliament's record, not admitting them.** That is a data question,
not a pipeline one, and is left open deliberately.

### Superseded approach, recorded because it cost something
An earlier ballot-agreement threshold (95%/5%) bound 503 votes, 141 of which then failed
verification — plausible matches to the *wrong* same-tally vote. Tightening to 99.5%/15%
kept only sound ones. Title matching later made ballot disambiguation unnecessary
entirely.

## Earlier status
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
