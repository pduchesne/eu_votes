---
id: TK08-retire-legacy-pipeline
title: Retire the Legacy Pipeline and Decide the 2014-2019 Data's Fate
status: todo
---
# TK08 — Retire the Legacy Pipeline and Decide the 2014-2019 Data's Fate

## Scope
Two related decisions, deliberately scheduled *after* the new pipeline produces
published output — retiring the old one earlier would leave the project with nothing
published at all, since `output/FinalResults.html` is currently the only citizen-facing
artifact that exists.

**The 2014-2019 data.** It is the only data currently in the repo, but it is two terms
stale and sits outside `PJ01`'s scope (current + previous term). Decide whether to:
- re-extract it through the new pipeline, giving three terms and making genuine
  trend storytelling possible (`SC04`), at the cost of the cross-term PCA comparability
  problem noted in `TK07` applying across a wider span; or
- drop it, accepting that the published history starts at 2019.

This is a product decision about what stories the project wants to tell, not a
technical one.

**The legacy artifacts.** Once superseded, retire:
- `DataExtraction.ipynb`, `DataMining.ipynb`, `ep_meps_extract.ipynb` (Python 2, no
  longer runs), `ep_votes_extract.ipynb`, `FinalResults.ipynb`
- `eu_utils.py`, `jupyter_utils.py`, `custom_template.tpl`, `d3_utils.js`
- `viz_tests/` — the abandoned altair/vega/d3/plotly experiments; their conclusion is
  already captured in the `CMP-UI-3DVIEW` technology decision
- `computed/` (incl. the 70MB `meps_votes.csv`) and `output/FinalResults.html` (6.8MB)

Note the repo-weight angle: those two files alone are ~77MB of git history. Deleting
them from the working tree does not reclaim that, so decide explicitly whether history
rewriting is worth it or whether the weight is simply accepted. Do not rewrite shared
history without agreement.

Leaving both pipelines alive is the outcome to avoid — it invites someone running the
stale one and publishing 2019 figures as current.

## Acceptance criteria
- A recorded decision on the 2014-2019 data, with rationale.
- Superseded files removed or moved to a clearly-marked `attic/`, with the README
  pointing only at the new pipeline.
- An explicit, recorded decision on whether to rewrite history for repo weight.
