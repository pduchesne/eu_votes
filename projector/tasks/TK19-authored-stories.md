---
id: TK19-authored-stories
title: Authored Stories as Versioned Content
status: done
component: CMP-PUBLISH
---
# TK19 — Authored Stories as Versioned Content

## Scope
Restore the capability the rewrite lost: a person writing about a vote or a topic, with
that writing treated as content rather than markup (`FR05`).

The 2019 analysis had it. It explained what the components appeared to mean, and walked
through specific amendments — naming four proposed by S&D and backed by ECR, with links
to the documents. That is the half that made the numbers worth reading, and none of it
survived.

### Shape
- Stories live in the repository as markdown with front-matter: author, date, and what
  the story is about (a vote id, a topic, a term).
- `CMP-PUBLISH` emits them into `IF-PUBLISHED-DATA` alongside the data they reference,
  so the site stays a static reader of published bundles.
- Figures cited in prose are **resolved from the data at publish time**, not typed by
  hand. A story that says "voted with their group 62% of the time" should get that
  number from the store, so prose cannot drift from the figures it describes.
- Rendering makes authorship visible: attributed, dated, and styled so nobody mistakes
  an argument for a measurement.

### The trap to avoid
A story is persuasive in a way a table is not, and it borrows the credibility the
verification work built. That credibility is only warranted for claims traceable to
Parliament's record. So: every vote a story names links to the EP document, every figure
it quotes is generated, and the reader can always see where the measurement ends and the
argument begins.

## Outcome (2026-09-27)
Stories live in `stories/` as markdown with front matter, are published into
`IF-PUBLISHED-DATA` by `pipeline/stories.py`, and render in the site's Stories view.

The mechanism that matters: **a story never contains its own numbers.** Figures are
declared in front matter as structured specifications — never SQL, so an author cannot
reach past the published data — resolved against the verified store at publish time, and
substituted into the prose on render. A story citing an undeclared figure fails the
build rather than showing a reader a raw token.

Each rendered figure carries what it was counted over ("computed from 27 votes"), so the
basis of any number is visible without leaving the prose.

The first story, on asylum votes in the 9th term, exists partly to prove the mechanism
and partly because the data had something genuinely non-obvious in it: support came from
the centre (S&D and Renew both 92.6%, EPP 85.2%) while opposition came from *both* ends —
ECR 29.6% and ID 25.9%, but also the Left at 48.1% and the Greens at 59.3%. All ten
figures were cross-checked against independent queries before the story was written.

That story also demonstrates the boundary this requirement exists to protect: the
numbers are computed, and the reading — that a vote against a text can oppose its
existence or its inadequacy, and a roll-call record cannot tell them apart — is argument,
marked as such and attributed.

## Acceptance criteria
- A story attaches to a vote, topic or term and renders with author and date.
- Authored and computed content are visually distinct wherever they appear together.
- Cited figures are generated from published data at build time.
- Every vote named in a story links to Parliament's own document.
- Stories are versioned in the repository, so their history is as auditable as the data's.
