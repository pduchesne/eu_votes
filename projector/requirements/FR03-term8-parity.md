---
id: FR03-term8-parity
title: No Regression Against the 2019 Analysis on the 8th Term
status: planned
---
# FR03 — No Regression Against the 2019 Analysis on the 8th Term

The 8th term (2014-2019) is the one term both the original 2019 analysis and the
current pipeline cover. It is therefore the only place where the new solution can be
held to an objective standard rather than judged on its own terms: **on term 8, the new
pipeline must be at least as good as the one it replaces** — in the data it extracts
and in the insight it infers.

This exists because a rewrite that quietly delivers less than what it replaced is a
regression regardless of how much better its engineering is. The old analysis is
archived in `attic/`, so the comparison is concrete and can be checked rather than
asserted.

## The baseline, measured

From `attic/computed/` (the 2019 pipeline's own output) and from Parliament's archived
record:

| Measure | Parliament's record | 2019 analysis | Current pipeline |
|---|---|---|---|
| Term-8 roll-call votes | **10,281** | 10,227 | 11,286 held, **5,398 analysed** |
| MEPs with computed positions | — | 824 | 855 |
| Per-vote component coefficients | — | **10,227** | **0** |
| MEP attributes | — | name, country, group, constituency, gender, birthdate, photo, homepage, email | name, country (birthdate/email only for MEPs also serving post-2019) |
| Arbitrary time-window analysis | — | yes (`temporal_slice`) | no — whole terms only |

## What parity requires

**Data parity**
- Analysed term-8 vote coverage at least matches the 2019 analysis (10,227), measured
  against Parliament's 10,281. Votes excluded for failing verification count as *not*
  analysed — coverage must be earned by verifying, not by relaxing `FR02`.
- Duplicate records (the ~1,033 arising from sittings present in the source both with
  and without times) are removed rather than inflating counts.
- MEP detail at least matches the old field set. Those fields exist in the source dump
  already being downloaded.

**Insight parity**
- Per-MEP PCA positions — already met.
- **Axis interpretation** — per-vote component coefficients, so the platform can say
  *what a component means* rather than only where MEPs sit on it. This is what made the
  old report's narrative possible ("this axis is about fraud amendments, refugees,
  gender mainstreaming") and it is the half currently missing. `UC02` and `UC04` both
  depend on it.
- Analysis over arbitrary date windows, not only whole terms.

## How this is enforced
Parity is not a one-off review. The baseline above is extracted from `attic/computed/`
into a fixture, and a pipeline check compares current output against it, so a
regression fails the build rather than waiting to be noticed (`TK17`).

## Acceptance criteria
- Automated parity check runs in the pipeline and fails on regression against the
  recorded baseline.
- Analysed term-8 votes ≥ 10,227, with the shortfall against Parliament's 10,281
  stated.
- MEP records carry at least the 2019 field set.
- Per-vote component coefficients are computed and published for every analysed term.
- Positions can be computed for an arbitrary date window.
