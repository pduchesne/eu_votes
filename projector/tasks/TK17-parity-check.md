---
id: TK17-parity-check
title: Automated Parity Check Against the 2019 Baseline
status: todo
component: CMP-ORCH
---
# TK17 — Automated Parity Check Against the 2019 Baseline

## Scope
Make `FR03` enforceable rather than aspirational. A parity claim that lives in a
document decays; one that fails the build does not.

Extract the 2019 analysis's own output in `attic/` into a small, committed baseline
fixture — term-8 vote count, MEPs with positions, per-vote coefficient count, the MEP
field set — and add a pipeline check comparing current output against it. Parliament's
archived record supplies the absolute ceiling (10,281 term-8 roll-call results), so the
check reports against both: the old pipeline and the record itself.

Keep the fixture rather than reading `attic/` at runtime: the archived directory may
eventually be pruned, and the baseline should survive that. It is a handful of numbers.

The check belongs with `validate`, reporting a regression as a failure and a genuine
improvement as an improvement, so the direction of travel is visible in the output.

## Acceptance criteria
- Baseline fixture committed, with a note recording how it was derived from `attic/`.
- `validate` compares analysed vote coverage, MEP attribute completeness, position
  coverage and coefficient coverage against it.
- A regression fails the pipeline; the message names the measure and both numbers.
- The check survives removal of `attic/`.
