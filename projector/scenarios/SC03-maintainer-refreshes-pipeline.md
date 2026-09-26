---
id: SC03-maintainer-refreshes-pipeline
title: Maintainer Refreshes Pipeline
user: Data maintainer
---
# SC03 — Maintainer Refreshes Pipeline

**Situation:** A new batch of EP votes (or a new term) needs to be reflected in the
published dashboard.
**Goal:** Run the fetch → normalize → mine → publish pipeline end-to-end, reproducibly,
without manually placing files or re-running notebooks in a specific fragile order.
**Pain point:** Today, raw data fetch is undocumented and manual (someone drops JSON
dumps into `tmp/`); `ep_meps_extract.ipynb` is even stuck on Python 2 syntax and no
longer runs; there is no single documented command to go from "new raw data" to
"published result."

## Details
Directly serves the transparency/reproducibility requirement: every stage must be a
scripted, versioned step, and published artifacts must carry provenance (source,
fetch date, script commit) so the whole chain is auditable by someone outside the
project, not just re-runnable by the maintainer.
