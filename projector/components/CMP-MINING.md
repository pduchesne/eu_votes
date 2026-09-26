---
id: CMP-MINING
title: Mining Pipeline
status: planned
node: Platform
uses:
  IF-DATASTORE: read normalized MEPs, votes, and ballots to compute the analysis layer
---
# CMP-MINING — Mining Pipeline

### Function
Computes the analytical layer: PCA-based political positioning, group-cohesion /
outlier scoring, and topic classification of votes. Evolves the existing
`DataMining.ipynb` (PCA + `ExtraTreesRegressor` feature importance) into scripted,
versioned functions; notebooks remain acceptable for exploration only, not as the
pipeline itself.

### Technology
Python, scikit-learn (PCA retained); topic classification via EP policy-area metadata
where available, else lightweight NLP/embedding clustering on vote titles/reports.

### Responsibilities
- Compute PCA components per time slice (as `eu_utils.compute_pcas` does today).
- Compute a per-MEP group-cohesion / loyalty score.
- Classify votes into topics to support UC04.
- Be callable as a scripted step producing deterministic, versioned output for
  CMP-PUBLISH.

### Data
Input: normalized store from CMP-ETL. Output: analysis artifacts (PCA coordinates,
cohesion scores, topic labels) consumed by CMP-PUBLISH.
