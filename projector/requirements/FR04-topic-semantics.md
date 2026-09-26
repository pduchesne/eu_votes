---
id: FR04-topic-semantics
title: Machine-Derived Topic Semantics for Every Vote
status: planned
---
# FR04 — Machine-Derived Topic Semantics for Every Vote

Every vote should carry a semantic representation of **what it is about**, derived from
the corpus itself rather than borrowed from an official classification — a vector
embedding of the vote's text, a topic taxonomy induced from the whole history, or both.

This is deliberately separate from `FR05-authored-narrative`. Deriving what a vote is
about is a data-mining problem with a measurable answer; explaining why a vote mattered
is editorial work with an author. Blurring them would let interpretation masquerade as
computation, which is the opposite of what this platform claims.

## Why the current tagging is not this
Votes are presently tagged with Parliament's own Legislative Observatory subject codes.
That is useful and authoritative, but it is a *label applied by someone else*, and its
coverage makes it unusable as the basis for exploring the corpus:

| Term | Votes | Tagged |
|---|---|---|
| 8 (2014-2019) | 11,286 | **0 (0%)** |
| 9 (2019-2024) | 21,944 | 14,072 (64%) |
| 10 (2024- ) | 6,808 | 4,926 (72%) |

Seven top-level subjects for three decades of legislating is also too coarse to answer
"show me the votes about migration" with any precision, and the 8th term — the whole
reason `PJ04` existed — has no tags whatsoever.

## What this requires
- A semantic representation for **every verified vote in every term**, computed from the
  vote's own text (title, procedure reference, associated document references).
- A topic structure induced from the corpus, so the vocabulary reflects what Parliament
  actually voted on rather than a fixed list decided in advance.
- Similarity between votes as a first-class operation: "votes like this one" should be
  answerable without anyone having tagged either of them.

## Validation, not vibes
Roughly 19,000 votes carry official subject tags. Those are a held-out truth set: where
both exist, derived topics can be measured against Parliament's own classification, and
the agreement rate published. A topic model that cannot reproduce the official labels on
the votes that have them should not be trusted on the votes that do not.

This mirrors how the rest of the pipeline works — nothing is asserted that cannot be
checked against an independent record.

## Acceptance criteria
- Every verified vote, in all three terms, carries a derived semantic representation.
- Agreement with Parliament's subject tags is measured on the votes that have them, and
  the figure is published alongside the topics.
- Derived topics are never presented as Parliament's classification; where both exist,
  the interface distinguishes them.
- "Votes similar to this one" is answerable across the whole corpus.
- The method and its limits are described in plain language on the methodology page.
