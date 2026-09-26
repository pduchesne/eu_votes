---
id: UC02-explore-political-landscape
title: Explore Political Landscape in 3D
keywords: [pca, 3d, navigation, political space, outliers, cohesion]
scenario: SC02-journalist-explores-landscape
priority: 1
requires:
  - CMP-PUBLISH
  - CMP-UI-3DVIEW
  - IF-PUBLISHED-DATA
  - FR03-term8-parity
---
# UC02 — Explore Political Landscape in 3D

A user navigates a 3D point cloud where each point is an MEP, positioned by the
PCA-derived political space. The user can orbit/zoom/pan, filter by group, country, or
time slice, and click a point to open that MEP's record (UC01).
