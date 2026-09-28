---
id: TK16-axis-interpretation
title: Compute Per-Vote Component Coefficients and Axis Interpretation
status: done
component: CMP-MINING
---
# TK16 — Compute Per-Vote Component Coefficients and Axis Interpretation

## Scope
The pipeline computes where MEPs sit in the political space but not **what the axes
mean**. The 2019 analysis did: `attic/computed/votes_pcs_coefficients.json` holds a
coefficient per vote per component for all 10,227 term-8 votes, and
`DataMining.ipynb` ranked votes by influence using `ExtraTreesRegressor`. That is what
let the old report say a component was about fraud amendments, refugees or gender
mainstreaming.

Without it, the 3D landscape (`UC02`) is a cloud a user can navigate but not read, and
topic stories (`UC04`) lose their strongest device: the ability to say *these specific
votes are what separates these groups*. Recovering it is `FR03`'s insight-parity half.

Mechanically straightforward — PCA already exposes `components_`, so the coefficients
are available at fit time and need only be retained, joined to vote titles, and
published.

Also in scope, a smaller regression: the old `temporal_slice` could fit positions for
any date window, while the current pipeline fits whole terms only. Restoring windowed
analysis is what makes "how did this group move during the pandemic" answerable.

Presentation caveat that belongs with the numbers: a component's sign and rotation are
arbitrary, so a coefficient indicates *how strongly a vote separates MEPs along an
axis*, never a direction on a left-right scale. Interpretation must be offered as
"votes that most distinguish this axis", not as a political label we assert.

## Status (2026-09-26)
Per-vote component coefficients are computed and stored for every analysed term
(35,128 votes). The PCA already produced them; they were simply being discarded.

They are interpretable, which was the point: T10's first component is defined by
enlargement reports on Albania and Bosnia, its second by the ECB annual report, CFSP
implementation and the defence white paper.

Term-8 coefficient count (10,112) is bounded by analysed coverage, not by this task.

Windowed analysis is restored too: `mine --window 2020-03-01:2021-06-30` fits positions
for any date range over verified votes and rotates them into the reference term's frame,
so a window is comparable with everything else instead of floating in its own arbitrary
orientation.

Sanity-checked on the pandemic window: 715 MEPs, group ordering identical to the full
term (ID/ECR at one end, Greens/S&D at the other) with compressed magnitudes, which is
what a correctly aligned shorter window should look like.

## Acceptance criteria
- Per-vote component coefficients computed for every analysed term and published.
- Top distinguishing votes per component are derivable from published data, with titles
  and EP citations attached.
- Positions can be computed for an arbitrary date window, not only whole terms.
- Published output states that component direction is arbitrary wherever coefficients
  are surfaced.

## Decomposing an axis by subject (2026-09-28)
The axis cards named the votes that most define each axis, which is useful but is a list
of dossiers rather than an account of what the axis is about. The axes now also decompose
into Parliament's own subjects.

This needs no model. A member's score on an axis is a sum over every vote of their
centred ballot times that vote's loading; votes belong to subjects, so the sum groups by
subject and the axis falls apart into named parts whose shares add to one. Verified as an
identity, not a fit: shares summed to 1.001. Votes tagged with several subjects split
evenly between them; untagged votes are their own bucket rather than dropped.

**The raw share is nearly useless and was very nearly shipped.** It mostly measures how
many votes a subject has, so the first run reported all three axes as "Budget + CFSP +
untagged" — the three busiest. Dividing by each subject's own size gives the lift, and
the axes separate immediately. For the 10th term: axis 1 is carried by public health
(1.88x), employment (1.43x) and fundamental rights (1.29x); axis 2 by commercial policy
(1.37x), monetary union (1.30x) and consumers (1.25x); axis 3 by treaties (1.30x). The
first named reading these axes have had that rests on Parliament's classification rather
than on keywords from titles.

The same machinery takes any direction, not only a principal axis, so "which subjects
carry the split between The Left and the EPP" is one call with a different vector — it
answers social policy 1.51x, public health 1.50x, and Treaties at **0.12x**, a twelfth of
what its size predicts. That is the arithmetic behind the earlier geometric finding that
the contrast sits 77° from the Treaties axis.

Honest limit: lifts run 1.2x to 1.9x, not 5x. No subject dominates any axis, which is the
same recurring result — the main cleavage runs through everything.
