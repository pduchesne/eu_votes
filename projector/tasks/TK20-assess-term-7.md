---
id: TK20-assess-term-7
title: Extend to the 7th Term (2009-2014)
status: todo
component: CMP-FETCH
---
# TK20 — Extend to the 7th Term (2009-2014)

## Feasibility, measured 2026-09-27
**It is possible, and the work differs from the 8th term in kind rather than degree.**

### Parliament has the record; the ingest source does not
Roll-call documents exist for the 7th term under the same RegData scheme, with `P7` in
place of `P8`. Six dates spanning 2009 to 2014 were fetched and all returned real XML,
structurally identical to the 8th term's: `RollCallVote.Result` elements with an
`Identifier`, a description carrying the vote's reference, and For/Against/Abstention
lists grouped by political group. **The existing parser reads them unchanged.**

Parltrack, which supplies the 8th term, is not usable as the ingest here:

| | Sittings | Votes |
|---|---|---|
| 8th term (parltrack) | 230 | 11,286 |
| **7th term (parltrack)** | **59** | **4,371** |

Coverage is also uneven across the term — 74 votes in 2009 and 440 in 2010 against
1,440 in 2013 — which looks like a source that improved over time rather than one with a
uniform gap.

So the roles invert. For the 9th and 10th terms a third party is the ingest and
Parliament the check; for the 7th, **Parliament would have to be the ingest**, with
parltrack as partial corroboration. The archiver, parser and reconciliation machinery
already exist; what changes is which way round they point.

### Two obstacles, one solved on paper
**Identity.** Term-7 documents name members by internal `MepId` only — 11,239 member
entries in a single sitting, not one `PersId`. The existing bridge is learned from 2023
onwards and will not reach members who left in 2014.

This is solvable from the overlap rather than by guesswork. On the 59 sittings both
sources cover, the same votes appear with `MepId` on one side and the EP's stable
identifier on the other, partitioned into identical (position, group) buckets. Across
roughly 150 votes per sitting each member has an effectively unique sequence of
positions, so matching those signatures determines the mapping and heavily
over-determines it — millions of paired observations for some 750 members.

**Sitting enumeration is the real unknown.** The EP Open Data API returns **HTTP 204 No
Content** for 2013; it does not cover this term, so the sitting list cannot come from
there. Parltrack knows only 59 of them. Options, none yet tested: derive dates from
parltrack's MEP activity dump, read Parliament's plenary minutes index, or probe the
deterministic URL pattern across candidate days — the last being ~1,300 requests for
weekdays over five years, which conflicts with crawling politely and should be a last
resort.

### Incidental finding
Parliament's servers occasionally answer with an HTML error page under **HTTP 200**. One
fetch of a document that had just succeeded returned a styled error page instead. The
archiver already validates that content starts with `<?xml` rather than trusting the
status code, but it aborts rather than retrying; a transient failure mid-crawl would
stop the run.

## What this would cost
Roughly a milestone: a `P7` URL pattern, sitting enumeration, signature-based identity
inference, ingest-from-XML (rather than from a dump), then the existing verify, mine and
publish stages unchanged. Term-7 votes would arrive without the procedure metadata the
later terms carry, though the dossier dump should supply titles and subjects as it did
for the 8th.

## The question this really raises
Whether a fourth term is worth it at all. The platform now covers 2014 onwards with
every ballot verified. Adding 2009-2014 buys a fifteen-year view and would make
`FR04`'s "derived semantics across the whole history" genuinely long-range — against a
source that is thinner, an identity problem that needs inference rather than a join, and
a sitting list nobody publishes in machine-readable form. That is a judgement about what
the platform is for, not a technical blocker.
