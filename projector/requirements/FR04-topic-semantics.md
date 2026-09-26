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

## Revised after the dossier ingest (2026-09-27)
The original justification was mostly about coverage, and that argument is now largely
spent. Parltrack's dossier dump supplied procedure titles for the 8th term — which had
none at all — and with them Parliament's own subject codes, from the same taxonomy the
later terms use:

| Term | Subject-tagged before | After |
|---|---|---|
| 8 | 0% | **97%** |
| 9 | 64% | **95%** |
| 10 | 72% | **96%** |

The taxonomy also turned out to be far richer than it appeared: 414 subject codes in
use, not the seven top-level areas the interface was collapsing everything into. The
8th term alone now browses across 147 subjects.

**So what remains for derived semantics is narrower and should be judged on its own
merits, not on the coverage argument below:**
- Roughly 9,300 votes (25%) still carry no subject at all — those with no procedure
  reference to inherit from.
- "Votes similar to this one" is still unanswerable; an official taxonomy gives
  membership, not similarity.
- Official subjects describe the *procedure*. Every vote on a dossier inherits the same
  label, so amendments within one procedure are indistinguishable by subject even when
  they concern quite different things.

The third point is the strongest remaining case, and it is about resolution rather than
coverage.

## Why the current tagging is not this
Votes are presently tagged with Parliament's own Legislative Observatory subject codes.
That is useful and authoritative, but it is a *label applied by someone else*, and its
coverage makes it unusable as the basis for exploring the corpus:

| Term | Votes | Tagged (at the time) |
|---|---|---|
| 8 (2014-2019) | 11,286 | **0 (0%)** |
| 9 (2019-2024) | 21,944 | 14,072 (64%) |
| 10 (2024- ) | 6,808 | 4,926 (72%) |

*(Superseded — see above. Kept because it records why this requirement was raised.)*

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
