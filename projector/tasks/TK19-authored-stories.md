---
id: TK19-authored-stories
title: Authored Stories as Versioned Content
status: todo
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

## Acceptance criteria
- A story attaches to a vote, topic or term and renders with author and date.
- Authored and computed content are visually distinct wherever they appear together.
- Cited figures are generated from published data at build time.
- Every vote named in a story links to Parliament's own document.
- Stories are versioned in the repository, so their history is as auditable as the data's.
