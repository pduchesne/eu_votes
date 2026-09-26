---
id: CMP-ORCH
title: Pipeline Orchestrator
status: planned
node: Platform
---
# CMP-ORCH — Pipeline Orchestrator

### Function
Owns the "one documented command" promise of SC03/UC03: chains
`CMP-FETCH` → `CMP-ETL` → `CMP-MINING` → `CMP-PUBLISH` into a reproducible
end-to-end run, with each stage individually invocable. Without this, the
reproducibility claim has no home — four scripts and a README are not a pipeline.

### Technology
Deliberately minimal: a Makefile or a thin Python CLI. No workflow engine (Airflow,
Dagster, Prefect) — the dataset is small and the stage count is four; heavyweight
orchestration would add operational burden without buying anything, and would work
against the goal of a pipeline an outsider can read and re-run.

### Responsibilities
- Expose one command to run the full pipeline, and one per individual stage.
- Make stage ordering and inputs/outputs explicit and inspectable.
- Fail loudly on a missing or stale prerequisite rather than silently producing
  partial output.
- Record which script versions ran, feeding `FR01-provenance-chain`.

### Data
No data of its own; coordinates the stages and their declared inputs/outputs.
