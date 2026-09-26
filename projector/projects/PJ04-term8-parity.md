---
id: PJ04-term8-parity
title: Parity With the 2019 Analysis
status: planning
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

No deadline set.
