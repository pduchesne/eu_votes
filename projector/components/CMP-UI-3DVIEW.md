---
id: CMP-UI-3DVIEW
title: 3D Political Landscape View
status: planned
node: Browser
uses:
  IF-PUBLISHED-DATA: read PCA coordinates and MEP metadata to render the point cloud
---
# CMP-UI-3DVIEW — 3D Political Landscape View

### Function
A navigable 3D point cloud of the political landscape: each point is an MEP,
positioned by PCA output from CMP-MINING. Lets a user directly verify the topology
(clusters, outliers, inter-group distance) is grounded in real vote data rather than a
fixed, pre-composed image.

### Technology
deck.gl (`OrbitView` + `ScatterplotLayer`) — WebGL-based, purpose-built for
data-driven point-cloud rendering with orbit/zoom/pan and picking, avoiding the
camera-control and hit-testing boilerplate a raw three.js build would need for ~750
points. Falls back to three.js primitives only if a fully custom (non-point-based)
visual is wanted later.

### Responsibilities
- Render the PCA point cloud with orbit/zoom/pan navigation.
- Filter points by group, country, or time slice.
- Click-to-select a point, opening that MEP's record (UC01).

### Data
Reads PCA coordinates and MEP metadata from `IF-PUBLISHED-DATA`.
