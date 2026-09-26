---
id: FR01-provenance-chain
title: End-to-End Provenance & Reproducibility Chain
status: planned
---
# FR01 — End-to-End Provenance & Reproducibility Chain

Every figure the project publishes must be traceable back to raw source data, and the
derivation must be re-runnable by someone outside the project. This is a cross-cutting
capability spanning `CMP-FETCH`, `CMP-ETL`, `CMP-MINING`, `CMP-PUBLISH` and
`CMP-ORCH` — which is why it is tracked as a requirement rather than owned by any
single component.

It exists because the project's purpose is democratic transparency: a claim about how
an MEP voted is only as credible as the auditable chain behind it. The current
codebase fails this on both counts — the raw data source is undocumented (dumps
appear in `tmp/` from nowhere), and the derivation lives in notebooks that must be run
in an undocumented order, one of which no longer executes at all.

## Acceptance criteria
- Every published artifact carries: source identifier/URL, dump or fetch date, and the
  git commit of the scripts that produced it.
- The normalized store (`IF-DATASTORE`) retains provenance fields, so lineage survives
  the fetch → normalize → mine → publish chain rather than being attached only at the
  end.
- A plain-language methodology document explains each derived figure (e.g. what a
  group-cohesion score means, how PCA axes are computed and why their orientation is
  arbitrary), versioned alongside the code.
- The UI can link any chart or number to its provenance and methodology (`UC05`).
- A third party can reproduce published artifacts from raw source using only the
  documented commands.
