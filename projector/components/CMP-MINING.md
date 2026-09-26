---
id: CMP-MINING
title: Mining Pipeline
status: done
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
Python, scikit-learn (PCA retained). Topic classification uses the EuroVoc and
Legislative Observatory subject tags that `IF-RAW-SOURCE` already carries per vote
(`eurovoc_concept_votes`, `oeil_subject_votes`) — authoritative labels from the
Parliament itself, rather than topics we infer. NLP/embedding clustering is a
fallback for gaps, not the primary mechanism.

### Responsibilities
- Compute PCA components per time slice (as `eu_utils.compute_pcas` does today).
- Compute a per-MEP group-cohesion / loyalty score.
- Classify votes into topics to support UC04.
- Respect the `is_main` distinction: 90% of rows are amendment/procedural votes, so any
  aggregate computed over all votes indiscriminately measures procedural noise rather
  than substantive position. The original notebooks did exactly that.
- Be callable as a scripted step producing deterministic, versioned output for
  CMP-PUBLISH.

### Data
Input: normalized store from CMP-ETL. Output: analysis artifacts (PCA coordinates,
cohesion scores, topic labels) consumed by CMP-PUBLISH.
