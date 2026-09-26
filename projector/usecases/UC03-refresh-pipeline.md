---
id: UC03-refresh-pipeline
title: Refresh Data Pipeline End-to-End
keywords: [fetch, etl, mining, publish, reproducibility, provenance]
scenario: SC03-maintainer-refreshes-pipeline
priority: 1
---
# UC03 — Refresh Data Pipeline End-to-End

A maintainer runs the fetch, normalize, mine, and publish stages as a single scripted,
documented, reproducible process, producing new published artifacts with provenance
metadata (source, fetch date, script commit) attached.

Split into two sub-use-cases because acquisition and analysis are delivered in separate
milestones: acquisition is the whole of `PJ01-data-extraction-foundation`, while mining
and publishing follow later. Keeping them separate lets the first milestone actually
reach completion instead of reading as permanently half-done.

## Sub-use-cases
- [UC03.01 — Acquire and Normalize Data](UC03-refresh-pipeline/UC03.01-acquire-data.md)
- [UC03.02 — Mine and Publish Results](UC03-refresh-pipeline/UC03.02-mine-and-publish.md)
