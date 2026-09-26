---
id: TK16-axis-interpretation
title: Compute Per-Vote Component Coefficients and Axis Interpretation
status: todo
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

## Acceptance criteria
- Per-vote component coefficients computed for every analysed term and published.
- Top distinguishing votes per component are derivable from published data, with titles
  and EP citations attached.
- Positions can be computed for an arbitrary date window, not only whole terms.
- Published output states that component direction is arbitrary wherever coefficients
  are surfaced.
