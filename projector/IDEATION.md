# Ideation

## Problem statement
Citizens have almost no accessible way to see how their MEPs actually vote and how
that compares to their political group. The only artifact this project currently
produces is a single static, PCA-heavy Jupyter HTML export covering one stale EU term
(2014-2019), built through a fragile, partly-broken, partly-undocumented notebook
pipeline that only the repo owner can operate. For the result to serve its democratic
purpose, both the data (how it was obtained) and the derived analysis (how it was
computed) must be transparent and reproducible by others.

## Target users
- **Citizen/voter**: wants to look up "their" MEP(s) and understand voting behavior in
  plain language, not PCA plots.
- **Journalist/researcher**: wants to explore group cohesion, defections, and
  topic-level voting patterns to find and support stories.
- **Data maintainer** (repo owner): wants a low-effort, repeatable, documented way to
  refresh data as new terms/votes happen, without hand-running notebooks in a fragile
  order.

## Scenarios
- [SC01 — Citizen Looks Up Their MEP](scenarios/SC01-citizen-looks-up-mep.md)
- [SC02 — Journalist Explores Political Landscape](scenarios/SC02-journalist-explores-landscape.md)
- [SC03 — Maintainer Refreshes Pipeline](scenarios/SC03-maintainer-refreshes-pipeline.md)
- [SC04 — Citizen Browses Topic Stories](scenarios/SC04-citizen-browses-stories.md)

## Cross-cutting requirement
Transparency and reproducibility apply across all scenarios rather than belonging to
one: see [FR01 — End-to-End Provenance & Reproducibility Chain](requirements/FR01-provenance-chain.md)
and [UC05 — Inspect Data Provenance and Methodology](usecases/UC05-inspect-methodology.md).

A second cross-cutting commitment: the rewrite must not deliver less than what it
replaces. The 2014-2019 term is covered by both the original 2019 analysis and the
current pipeline, making it the one place parity can be measured rather than asserted —
see [FR03 — No Regression Against the 2019 Analysis](requirements/FR03-term8-parity.md)
and its milestone [PJ04](projects/PJ04-term8-parity.md).
