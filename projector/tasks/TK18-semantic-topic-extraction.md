---
id: TK18-semantic-topic-extraction
title: Derive Topic Semantics for Every Vote
status: todo
component: CMP-MINING
---
# TK18 — Derive Topic Semantics for Every Vote

## Progress (2026-09-27)
The prerequisite turned out to be data, not modelling. The 8th term had no procedure
titles at all — nothing to derive a topic *from* — and `pipeline/dossiers.py` now
resolves them from parltrack's dossier dump at 97% coverage, bringing Parliament's own
subject codes with them. Topic coverage went from 0% to 97% for the 8th term, and from
roughly two-thirds to ~95% for the others. Browsing uses the 414 leaf subject codes
rather than seven top-level areas.

That removes coverage as the motivation. What is left to build, and why:
- **Similarity** — "votes like this one" across the whole corpus, which no taxonomy
  provides.
- **Sub-procedure resolution** — official subjects describe the dossier, so every
  amendment in a procedure inherits one label. Distinguishing them needs the vote's own
  text.
- **The ~9,300 votes with no procedure reference**, which no amount of dossier data
  reaches.

Measure before modelling still applies, and the validation set is now much larger: ~27k
votes carry official subjects to check derived topics against.

## Original scope
Give every verified vote a semantic representation computed from its own text, so the
corpus can be explored by subject without depending on who happened to tag what
(`FR04`). Two complementary outputs:

- **An embedding per vote**, from the title, procedure reference and related document
  references. This is what makes "votes like this one" answerable at all, and it covers
  the 8th term, which has no official tags whatsoever.
- **A topic structure induced from the whole history** — clusters over those embeddings,
  labelled from their most characteristic terms — so there is a vocabulary to browse
  rather than only a similarity function.

### What the text actually is
Worth knowing before choosing a method: titles are short and formulaic
(`"A8-0175/2015 - Bernd Lange - Am 77"`, `"2023 and 2024 reports on Albania"`). Many
amendment votes carry almost no subject matter in their own title and only make sense
through the report they amend. So the unit of meaning is often the *procedure*, not the
individual vote, and votes should likely inherit semantics from their procedure where
their own text is uninformative. Establish this empirically before modelling.

### Method, deliberately unfixed
Sentence embeddings from a small multilingual model would suit; so might TF-IDF over
procedure titles with classical clustering, which is far cheaper and may be sufficient
given how formulaic the text is. Pick after measuring, not before — and prefer the
simpler method that passes the validation below.

## Validation
About 19,000 votes carry Parliament's own subject tags. They are a held-out truth set:
measure how well derived topics reproduce the official ones where both exist, and
publish that agreement rate. A model that cannot recover the official labels on tagged
votes has not earned trust on the 8th term, where nothing can be checked.

## Acceptance criteria
- Every verified vote in all three terms carries an embedding and a derived topic.
- Agreement with official subject tags is measured and published.
- "Votes similar to this one" works across the whole corpus, including across terms.
- Derived topics are stored and published distinctly from official tags — never merged
  into one field that hides which is which.
- Published bundles stay within a size a browser can load; embeddings themselves need
  not ship in full if similarity is precomputed.
