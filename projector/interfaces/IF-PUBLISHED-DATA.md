---
id: IF-PUBLISHED-DATA
title: Published Data Bundle
status: auto
required: false
implementedBy: CMP-PUBLISH
---
# IF-PUBLISHED-DATA — Published Data Bundle

### Purpose
The versioned JSON contract between the mining pipeline and the UI. It is the sole
boundary the UI depends on, so mining internals (algorithms, libraries, topic
classification approach) can change without requiring UI changes, and vice versa.

### Key capabilities / Conformance classes
- Per-MEP summary (voting record, attendance, group-cohesion score).
- PCA coordinates per MEP per time slice, for the 3D landscape view.
- Topic-classified vote groupings, for topic stories.
- Provenance metadata on every bundle: source, fetch date, script commit.

### Key endpoints
Static JSON files at build time (no live API in the current scope); may grow a thin
query API later if a scenario requires live filtering beyond what static bundles
support.
