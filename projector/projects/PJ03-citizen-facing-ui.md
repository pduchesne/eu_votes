---
id: PJ03-citizen-facing-ui
title: Citizen-Facing UI
status: planning
members:
  - UC01-lookup-mep
  - UC02-explore-political-landscape
  - UC04-browse-stories
  - UC05-inspect-methodology
  - CMP-UI
  - CMP-UI-3DVIEW
  - IF-PUBLISHED-DATA
  - FR01-provenance-chain
---
# PJ03 — Citizen-Facing UI

Third milestone: replace the static `nbconvert` HTML export with the actual
citizen-facing product — MEP lookup (`UC01`), the navigable 3D political landscape
(`UC02`), topic stories (`UC04`), and provenance/methodology surfacing (`UC05`).

Recorded decisions carried in from design discussion:
- **3D rendering: deck.gl** (`OrbitView` + `ScatterplotLayer`) rather than raw three.js
  — it is purpose-built for data-driven point clouds with orbit navigation and picking,
  which is exactly this view's need, and avoids hand-rolling camera controls and
  hit-testing for ~750 points. three.js primitives remain the fallback if a fully
  custom, non-point-based visual (terrain-style landscape) is wanted later.
- **No chart-studio / hosted plotly.** The old report rendered through the
  `plotly.plotly` cloud API; the replacement renders client-side with no external
  service dependency, which also matters for `FR01` — a figure that can only be
  reproduced by calling someone else's service is not reproducible.
- **Static-first delivery.** The UI reads pre-built `IF-PUBLISHED-DATA` bundles rather
  than querying a backend. A thin query API is deferred until a scenario genuinely
  needs live filtering that bundle-size limits cannot serve — the 3D view's
  interactivity is client-side and does not require one.

Dependency note: the 3D view's ability to show movement *between* terms depends on the
cross-term PCA alignment decision taken in `PJ02`. Design the navigation after that is
settled.

No deadline set yet.
