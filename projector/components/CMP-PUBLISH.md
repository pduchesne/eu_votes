---
id: CMP-PUBLISH
title: Publish Bundles
status: done
node: Platform
uses:
  IF-DATASTORE: read the normalized store for artifacts that need raw-vote context
---
# CMP-PUBLISH — Publish Bundles

### Function
Transforms mining output into small, purpose-built JSON artifacts sized for a
browser (per-MEP summaries, PCA coordinates, topic/story data) instead of shipping
the raw vote matrix. This is the transparency boundary: every published artifact
carries provenance (source, fetch date, script commit) and a reference to the
methodology documentation, and is the sole contract the UI depends on — so mining
internals can change freely without touching the UI.

### Technology
Python script producing static JSON files (no live API required for the current
scope).

### Responsibilities
- Shape mining output into `IF-PUBLISHED-DATA` bundles.
- Attach provenance metadata to every bundle.
- Keep bundle size bounded for client-side/browser consumption.

### Data
Input: analysis artifacts from CMP-MINING, plus descriptive fields (MEP names, vote
titles, provenance) read from `IF-DATASTORE`. Output: `IF-PUBLISHED-DATA` JSON bundles.
