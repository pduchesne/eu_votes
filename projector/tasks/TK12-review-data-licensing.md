---
id: TK12-review-data-licensing
title: Review Licensing of Ingested and Republished Data
status: done
---
# TK12 — Review Licensing of Ingested and Republished Data

## Scope
Establish what we are permitted and obliged to do when republishing derived data.
Flagged when the reference-data posture was decided and deliberately left unresolved,
because it is a legal question rather than an engineering one and should not be
settled by an assumption.

Two questions:
- **ODbL share-alike.** The HowTheyVote dataset is Open Database Licence. Our published
  bundles (`IF-PUBLISHED-DATA`) are a derived database. Determine what ODbL requires of
  them — attribution, share-alike licensing of the derived database, or neither, given
  how much of the output is our own computation rather than their data.
- **European Parliament reuse terms.** Determine the conditions attached to reusing
  Parliament's documents and API data, including the archived roll-call XML
  (`TK09`), and what attribution is required.

Both answers feed the public-facing methodology page (`UC05`) and may influence how
much the platform leans on each source — a share-alike obligation that we are content
to honour is fine; one discovered after launch is not.

## Outcome (2026-09-26)
Settled in `docs/licensing.md`. The decisive ODbL distinction: our published bundles
are a **Derivative Database** (share-alike applies, so they ship under ODbL), while the
dashboard, its charts and topic stories are **Produced Works** (share-alike does not
reach them, only an attribution notice). EP reuse terms permit commercial and
non-commercial reuse provided entire items are reproduced with source acknowledged.

Open and deliberately undecided: whether to republish the EP roll-call archive itself
rather than keep it as local verification evidence.

## Acceptance criteria
- A written statement of the licence applying to each ingested source, and the
  obligations it places on our published data.
- A chosen licence for the platform's own published bundles, consistent with those
  obligations.
- Required attributions appear in the published output and the UI.
