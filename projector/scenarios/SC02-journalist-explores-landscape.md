---
id: SC02-journalist-explores-landscape
title: Journalist Explores Political Landscape
user: Journalist/researcher
---
# SC02 — Journalist Explores Political Landscape

**Situation:** A journalist or researcher wants to find and substantiate a story about
group cohesion, defections, or realignments — with an objective, data-grounded view
rather than anecdote.
**Goal:** Interactively navigate the PCA-derived "political space" of MEPs in 3D,
filter by group/country/time slice, and identify outliers or cohesion patterns worth
writing about.
**Pain point:** The current PCA scatter plot is a single static chart embedded in a
Jupyter HTML export (via the old plotly chart-studio service) — no filtering, no live
navigation, no way to click a point and drill into who it represents.

## Details
This is the scenario behind the explicit requirement that the 3D point cloud be
navigable (orbit/zoom/pan), not just viewable: the topology itself — clusters,
outliers, distances between groups — is the story-generating artifact, so the ability
to explore it directly and verify it's grounded in real vote data (not a fixed,
pre-composed image) is core to the value.
