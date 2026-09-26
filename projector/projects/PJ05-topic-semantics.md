---
id: PJ05-topic-semantics
title: Topic Semantics
status: planning
members:
  - UC04.01-explore-topics
  - FR04-topic-semantics
  - CMP-MINING
  - CMP-PUBLISH
  - TK18-semantic-topic-extraction
---
# PJ05 — Topic Semantics

Derive what each vote is *about* from the corpus itself, so the record can be explored
by subject rather than only by member or by term.

The milestone exists because what the platform currently calls "topics" is Parliament's
Legislative Observatory classification — authoritative, but covering **none of the 8th
term**, about two-thirds of the rest, and only seven top-level subjects. It cannot
answer "show me the votes about migration" with any precision, and it cannot answer it
at all for 2014-2019.

Deliberately scoped to computation. Authored storytelling is `FR05`/`TK19` in `PJ03`:
different capability, different failure modes, and the reader must be able to tell them
apart.

## What would make this succeed
Not a topic model that looks plausible in a demo, but one whose derived labels can be
checked. Roughly 19,000 votes carry official tags; those are a truth set, and the
agreement rate belongs in the published output next to the topics themselves — the same
posture the pipeline takes everywhere else.

A likely finding worth anticipating: most amendment votes carry no subject matter in
their own title and only mean something through the procedure they belong to. If so, the
unit of semantics is the procedure and votes inherit from it. Establish that before
choosing a model.

No deadline set.
