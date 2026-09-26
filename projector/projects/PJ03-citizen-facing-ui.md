---
id: PJ03-citizen-facing-ui
title: Citizen-Facing UI
status: in-progress
members:
  - UC01-lookup-mep
  - UC02-explore-political-landscape
  - UC04-browse-stories
  - UC05-inspect-methodology
  - CMP-UI
  - CMP-UI-3DVIEW
  - IF-PUBLISHED-DATA
  - FR01-provenance-chain
  - FR02-primary-record-verification
  - TK11-cite-ep-source-per-vote
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

## Progress (2026-09-27)
A working static site in `ui/`: no build step, no bundler, reading the published
bundles directly, so deploying it is copying a directory.

| View | Use case | State |
|---|---|---|
| Political landscape | `UC02` | Done — deck.gl point cloud, orbit/zoom, colour by group or country, highlight a group, click through to a member. Below it, the votes that most define each axis. |
| Members | `UC01` | Done — search by name, country or group; per-term participation and group loyalty. |
| Topics | `UC04` | Partial — a subject-by-group support table, not yet the curated narrative stories `SC04` describes. |
| How this is made | `UC05` | Done — provenance, verification coverage, how positions are computed, and what the figures are not. |

Verified in a browser rather than assumed: the landscape renders 738 members for the
10th term and the political topology is immediately recognisable — EPP and Renew
adjacent, S&D and the Greens beside them, ECR and the hard-right groups opposite,
non-attached members scattered between. Console is clean.

### Deliberate choices
- **Groups are coloured by identity, never by position.** Colouring a point by where it
  sits would invent a left-right axis the analysis does not claim to have found.
- **The site cannot outrun the pipeline**: it reads `IF-PUBLISHED-DATA` and nothing
  else, so it can only show what was verified against Parliament's record.
- **deck.gl is pinned and loaded from a CDN**; if it fails, the 3D view says so and the
  rest of the site still works.

### Outstanding
- `UC04` narrative stories: the topics table answers "how did each group vote on this
  subject", but not "here is what happened on migration, told as a story".
- No per-vote browser: votes appear only where the axes name them.
- Not deployed anywhere; `TK12`'s attribution requirements are documented but not yet
  rendered in the footer.

No deadline set yet.
