---
id: FR02-primary-record-verification
title: Every Ballot Verified Against Parliament's Published Record
status: planned
---
# FR02 — Every Ballot Verified Against Parliament's Published Record

The platform's reference of record is **europarl.europa.eu**. The HowTheyVote dataset
is an ingest path, not an authority: convenient, verified, and replaceable. Every
ballot we publish must be checked against Parliament's own roll-call XML, and every
vote shown to a citizen must cite the EP document it came from.

Decided 2026-09-26 after weighing four postures (secondary-only with sampling;
secondary ingest with complete verification; primary-only; primary with secondary as
cross-check). The reasoning: credibility comes from verifiability rather than from
provenance alone. A pipeline that ingests a derivation and continuously proves it
matches Parliament is more trustworthy than one that ingests primary data and never
checks itself — the first has an error-detection mechanism, the second only has a
better story. Rebuilding the ingest from primary sources would mean reimplementing
what HowTheyVote already does correctly, with our own fresh bugs and nothing
independent left to check them against.

This supersedes `TK06`'s sampling posture, which covered 628 votes (2.5%). Sampling
catches systematic mis-parsing well and sparse, localised errors poorly — and the
source itself disclaims that individual votes may be missing or wrong.

## Scope limit, stated honestly
Parliament's roll-call XML contains **only** ballots (For/Against/Abstention). It does
not contain vote titles, procedure references, `is_main`, or EuroVoc topics — those
come from the Open Data API and the Legislative Observatory — and it does not contain
`DID_NOT_VOTE` at all, which our source derives from the sitting roster.

So "fully verified" means *every ballot*. Metadata and non-voting figures remain
unverified against the primary record under this requirement, and must not be
described as though they were. Closing that gap would require integrating two further
official sources and deriving attendance ourselves — the cost that ruled out a
primary-only ingest.

## Acceptance criteria
- Parliament's roll-call XML is archived locally for every sitting in scope, as
  evidence we control rather than a link we hope stays live.
- Every ballot in the store is compared against that archive, not a sample, and the
  comparison re-runs as new sittings arrive.
- Coverage is reported as a figure the platform can publish — what fraction of ballots
  are verified, and what is not covered and why.
- Each published vote carries a citation to its EP source document.
- A failure to verify blocks publication of the affected figures rather than being
  logged and passed over.
