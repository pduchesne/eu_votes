---
id: SC04-citizen-browses-stories
title: Citizen Browses Topic Stories
user: Citizen/voter
---
# SC04 — Citizen Browses Topic Stories

**Situation:** A citizen without the background to read a PCA scatter plot still wants
to engage with what the EU Parliament has been doing on topics they care about (e.g.
climate, migration).
**Goal:** Browse short, curated narrative "stories" per topic, backed by real vote
data and visualizations, without needing to understand the underlying statistics.
**Pain point:** The current report is a list of "top votes" plus PCA plots with no
narrative framing — informative to an analyst, inaccessible to a general citizen.

## Details
Depends on topic classification existing in the mining stage (currently absent — only
PCA + feature importance are computed today), so this scenario is also what motivates
adding topic classification to the mining pipeline.
