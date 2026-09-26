---
id: TK08-retire-legacy-pipeline
title: Retire the Legacy Pipeline and Decide the 2014-2019 Data's Fate
status: done
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
  trend storytelling possible (`SC04`) — but note `TK01`'s finding that the selected
  source starts at 2019, so this means adopting and maintaining a *second* source
  (parltrack) purely for the 8th term, on top of the cross-term PCA comparability
  problem from `TK07`; or
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

## Decisions taken (2026-09-26)

**The 2014-2019 term is being brought into the new pipeline**, not dropped — see
`TK13`. Parltrack supplies it: rejected in `TK01` on freshness, which is a property
that only matters for a live term, and this one closed in 2019.

**The legacy files moved to `attic/`**, where they remain tracked in git rather than
deleted, with `attic/README.md` recording why each is unsafe to run. Note the original
intent was for `/attic` to be gitignored; because the files were already tracked, `git
mv` preserved them as renames, so history follows them and they stay visible. The
`/attic` entry was therefore removed from `.gitignore`, since an ignore rule over
tracked content is only confusing.

Moved: the five notebooks, `eu_utils.py`, `jupyter_utils.py`, `custom_template.tpl`,
`d3_utils.js`, the old root `requirements.txt` (it described the 2019 stack), plus
`computed/`, `output/` and `viz_tests/`.

**Repo weight was left alone.** The ~77MB of CSV and HTML remains in git history; the
move renames blobs rather than adding them. Rewriting history to reclaim that space was
considered and rejected as not worth rewriting shared history for.

## Acceptance criteria
- A recorded decision on the 2014-2019 data, with rationale.
- Superseded files removed or moved to a clearly-marked `attic/`, with the README
  pointing only at the new pipeline.
- An explicit, recorded decision on whether to rewrite history for repo weight.
