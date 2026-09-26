---
id: CMP-UI
title: Dashboard Shell
status: planned
node: Browser
uses:
  IF-PUBLISHED-DATA: read MEP records, topic stories, and provenance for display
---
# CMP-UI — Dashboard Shell

### Function
The citizen-facing web app: MEP lookup, topic stories, and the provenance/methodology
panel (UC05). Replaces the static `nbconvert` HTML export of `FinalResults.ipynb`.

### Technology
Static site (build-time read of `IF-PUBLISHED-DATA` JSON), lightweight client-side
charting (no chart-studio/cloud dependency, unlike the current `plotly.plotly` usage).

### Responsibilities
- MEP search and profile pages (UC01).
- Topic story pages (UC04).
- Provenance/methodology display for any chart or figure (UC05).
- Host/embed CMP-UI-3DVIEW.

### Data
Reads `IF-PUBLISHED-DATA` bundles only — never touches raw vote data directly.
