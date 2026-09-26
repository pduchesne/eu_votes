---
id: FR05-authored-narrative
title: Authored Narrative, Visibly Distinct From Computation
status: in-development
---
# FR05 — Authored Narrative, Visibly Distinct From Computation

A person writes about a vote or a topic: what was at stake, who broke with their group,
why it mattered. This is editorial work with an author and a date, and the platform must
carry it — but must never let it be mistaken for something the data computed.

The original 2019 analysis did exactly this, and it was the half that made the numbers
mean anything. It observed that "many of us are still looking at politics through an
obsolete, one-dimensional lens", explained what the principal components appeared to
correspond to, and walked through specific amendments — naming, for instance, four
amendments proposed by S&D and backed by ECR, with links to the documents.

**None of that survived the rewrite.** `FR03` did not catch it, because parity was
measured in vote coverage, positions, coefficients and attributes — all computed things.
A rewrite can hit every numerical target and still lose the reason anyone would read it.

## The rule that matters
Derived and authored claims must be distinguishable **by looking**, not by knowing.
A reader should never have to guess whether "the Greens and S&D voted together on
migration" is a measured fact or an editorial reading. The platform's whole argument is
that its figures are checkable against Parliament's record; prose that borrows that
authority without being checkable undermines it.

Concretely: authored text is attributed and dated, visually distinct from computed
figures, and never rendered as though it were a caption on a chart.

## Scope
- Narrative attached to a **specific vote** ("what this amendment actually did"), and to
  a **topic or period** ("how the Parliament handled migration in this term").
- Stored as content in the repository, versioned with everything else, so a story's
  history is as auditable as a figure's.
- Published through `IF-PUBLISHED-DATA` alongside the data it refers to, so the site
  remains a static reader of published bundles.
- Figures quoted inside a story should be generated from the data rather than typed by
  hand, so prose cannot silently drift from the numbers it describes.

## Acceptance criteria
- A story can be attached to a vote, a topic, or a term, and renders with author and
  date.
- Authored and computed content are visually distinct wherever they appear together.
- Stories live in version control and are published as data, not hard-coded in the site.
- Any figure cited in a story is derived from the published bundles at build time.
- A story about a vote links to Parliament's document for it, like every other reference
  to a vote.
