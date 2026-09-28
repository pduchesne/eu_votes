---
id: TK21-topic-axes
title: Fit One Axis Per Subject and Frame the Landscape With Them
status: done
component: CMP-MINING
---
# TK21 — Fit One Axis Per Subject and Frame the Landscape With Them

## Scope
The global components separate members better than anything else three numbers could, and
that is exactly why nobody can name them. `UC02.01` needs axes a citizen already holds an
opinion about, so the same computation runs again per theme: a one-component PCA over the
votes Parliament classified under that theme alone.

Mechanically small; the care is all in what it is allowed to claim.

## What it must not become
A "for or against migration" score. Restrictive and permissive proposals both come to a
vote, so counting yes-votes puts the backers of opposing texts at the same end. The signed
loading is what separates them, and the pipeline keeps the naive reading alongside as a
published diagnostic (`support_correlation`) rather than dropping it silently: on social
policy the two agree at +0.90, on foreign and security policy the yes-count inverts at
−0.43.

## Method as built
- Themes with at least 40 verified votes and 100 members voting; 93 axes across the three
  terms, thinner themes skipped rather than fitted badly.
- Ballots encode as the rest of the pipeline does: FOR +1, AGAINST −1, anything else 0.
- Orientation, which PCA leaves arbitrary: aligned with the term's first global component
  so subjects are comparable with each other and across terms; where |r| < 0.1 the
  subject's most influential vote is made positive instead, so the sign is at least
  reproducible between runs. Neither rule asserts a political direction, and the interface
  says so.
- Each end carries the votes pulling hardest towards it, with the FOR-share of the group
  at each extreme on every one of those votes. That pairing is the evidence that the ends
  are opposed positions rather than two piles of yes-votes.
- Stored in `topic_axes`, `topic_positions`, `topic_axis_votes`; published as
  `topic-axes.json` with raw member scores, because the reader chooses the three framing
  subjects and every such choice needs the same numbers.

## Side effect worth recording
Adding 74,000 rows to the mining stage exposed that its inserts went one statement per
row. Batched into 500-row statements, the whole `mine` stage dropped from over 13 minutes
to **1m26s**, topic axes included — so the new work costs less than the old bookkeeping
did.

## Frame selection (added after review)
Each topic axis is also placed as a direction in the main three-component space, by least
squares rather than three marginal correlations — the components are uncorrelated over a
whole term but not over the subset of members who voted on one subject.

The default frame is then the triple of those directions coming closest to perpendicular,
exhaustively over subjects with at least `FRAME_MIN_VOTES` (150) verified votes. Greedy
selection down the components was tried and is worse — on the 8th term worse than not
choosing at all — and the search is only a few thousand triples.

Span (|det| of the three unit directions) rose from 0.31 / 0.01 / 0.07 to 0.47 / 0.45 /
0.19 for terms 8 / 9 / 10.

## Finding
One cleavage runs through almost every subject. In the 9th term 33 of 38 subjects lie
closest to the first main axis, five to the second, **none** to the third. The third axis
is therefore not any policy area's internal disagreement, and no choice of subjects can
frame it — which bounds what this view can ever be, and is stated on the methodology page
rather than left for a reader to infer from a thin-looking cloud.

## Acceptance criteria
- One axis per sufficiently-attested theme per term, with member scores published.
- Agreement with the naive yes-count published per subject, and surfaced in the interface
  wherever the axis is shown.
- Both ends described by the texts that anchor them, each citing Parliament's document.
- Orientation rule stated on the methodology page, along with the fact that it asserts no
  political direction.

## Second divisions (added 2026-09-28)
One component per subject was not enough, and the frame-span numbers said so: first
components alone spanned 0.47 / 0.45 / **0.19** of the main space for terms 8 / 9 / 10,
because a theme's first component is almost always the chamber's usual cleavage again.

Each subject now carries two. The second is perpendicular to the first by construction,
so it is where the subject's own argument lives rather than the chamber's. Measured on
the 10th term before building it: social policy's second division sits **89° from the
Treaties axis** and separates The Left from the EPP at d = −4.1, and CFSP's is 12° from
the Left-versus-EPP contrast. Those are the axes the 3D view was missing.

Frame span, first components only → both available:

| Term | Before | After |
|---|---|---|
| 8 | 0.47 | **0.83** |
| 9 | 0.45 | **0.82** |
| 10 | 0.19 | **0.70** |

Constraints that came out of building it:
- **A subject may not supply two of the three frame slots.** Its own two divisions are
  perpendicular by construction, so a frame taking both would score near-perfectly while
  showing one subject three-quarters of the time.
- **Each component is oriented against the global component of the same rank**, so a
  second division is read the same way round as the chamber's second axis.
- **Standouts stay on first divisions.** "Where does this member stand out" wants a
  subject's main argument, not its residual one.
- Second divisions explain 4-19% against 26-53% for first ones, and their two ends are
  more often opposed amendments to a single report — which the existing "also at the
  other end" badge already handles.
