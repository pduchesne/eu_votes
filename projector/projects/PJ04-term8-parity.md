---
id: PJ04-term8-parity
title: Parity With the 2019 Analysis
status: in-progress
members:
  - FR03-term8-parity
  - CMP-ETL
  - CMP-MINING
  - CMP-ORCH
  - TK14-recover-unjoinable-term8-votes
  - TK15-restore-mep-attributes
  - TK16-axis-interpretation
  - TK17-parity-check
---
# PJ04 — Parity With the 2019 Analysis

Close the gap between what this pipeline delivers on the 8th term and what the
analysis it replaces already delivered, per `FR03-term8-parity`.

This milestone exists because the comparison was actually made rather than assumed. The
8th term is the only term both pipelines cover, and on it the new one is currently
behind in three specific ways: it analyses 5,398 votes where the old analysed 10,227;
it carries two MEP attributes where the old carried nine; and it computes no per-vote
component coefficients where the old computed 10,227 — losing the ability to say what
an axis means, which is the interpretive half of the whole exercise.

None of that invalidates what has been published. Unverified votes were excluded from
mining, so existing figures are sound — they simply rest on half the available
evidence, and `votes-t8.json` ships around a thousand duplicate rows.

## Sequencing
`TK17` first, or close to it: the parity check turns the target into something the
build enforces, and it is better to have the measure in place before moving the number.
Then `TK14` (coverage, the largest gap), `TK15` (MEP attributes, the cheapest), and
`TK16` (axis interpretation, the most valuable to `PJ03`).

## Relationship to PJ03
`TK16` is a prerequisite for the user-facing ambition rather than a nicety: without
per-vote coefficients the 3D landscape is a cloud a citizen can navigate but not read,
and topic stories lose the device of naming the specific votes that separate groups. If
`PJ03` starts first, this should land before its storytelling work does.

A constraint worth restating: coverage must be earned by verifying votes against
Parliament's record, never by relaxing `FR02`. Parity and verification are not in
tension — the point is to verify more, not to check less.

## Progress (2026-09-26)

| Measure | 2019 analysis | Now | |
|---|---|---|---|
| Term-8 votes **extracted** | 10,227 | **10,756** | ahead |
| Term-8 votes **analysed** (verified) | 10,227 | 10,112 | 115 short |
| MEPs with positions | 824 | 854 | ahead |
| Per-vote coefficients | 10,227 | 10,112 | bounded by coverage |
| MEP attributes | 9 fields | all fields, fill rates met | at parity |

`TK15` and `TK17` are done. `TK14` took analysed coverage from 5,398 to 10,112 and
`TK16` restored axis interpretation.

The check now measures **extraction and analysis separately**, because they are
different claims: the old pipeline verified nothing against Parliament's record, so
its 10,227 are ingested votes, and on that like-for-like basis we are ahead. Analysed
coverage applies the stricter standard this project chose, and is the one still short.

## What closing the last 115 requires
Not loosening anything. 644 term-8 votes remain unbound because several votes in the
same sitting share a tally and ballot agreement cannot separate them safely — a lesson
learned the hard way, since a looser threshold bound 141 votes to the *wrong*
same-tally vote before verification caught it. Closing the gap means finding a further
discriminator (vote order within the sitting, or the description text), not relaxing
the criterion.

Also outstanding: extracted count exceeds Parliament's own 10,281 by ~475, so more
duplicate records remain beyond the 530 found. And `TK16` still fits whole terms only,
so arbitrary date-window analysis is not yet restored.

No deadline set.
