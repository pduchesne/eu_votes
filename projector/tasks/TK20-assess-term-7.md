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

**Sitting enumeration was the real unknown. It is now solved — see below.**

### Incidental finding
Parliament's servers occasionally answer with an HTML error page under **HTTP 200**. One
fetch of a document that had just succeeded returned a styled error page instead. The
archiver already validates that content starts with `<?xml` rather than trusting the
status code, but it aborts rather than retrying; a transient failure mid-crawl would
stop the run.

## Enumeration and identity, measured 2026-09-27 (second pass)

### Enumeration: solved, and cheap
Every route that could have published the list was tested and none does. The Open Data
API answers **204** for 2009-2013 and **200 from 2014**; RegData answers **403** to any
directory request; no plenary-minutes work type exists in the API for 2013 (only
`REPORT_PLENARY`, `ERRATUM`, `AMENDMENT_LIST`); doceo answers **202**, the WAF challenge,
for `PV-7-*` URLs.

What does work is probing the RegData pattern, and far more cheaply than the 1,300
requests feared. `HEAD` distinguishes a hit (200, `text/xml`) from a miss (404, HTML)
without downloading the 1.2 MB body. Sittings cluster into part-sessions that always
include a Tuesday, so probing Tuesdays and expanding only around hits finds everything:

> **2013: 37 sitting days found in 101 requests.** 12 of 53 Tuesdays hit; the result is
> the EP calendar exactly — twelve part-sessions of Tue/Wed/Thu, October's second
> session, November's extra Monday. Weekday spread Mon 1, Tue 12, Wed 12, Thu 12, Fri 0.

Extrapolating, the whole term costs roughly **500 requests, about four minutes**. A
Wednesday safety pass (~40 requests a year) should be added in case a Brussels
mini-session ever sat without a Tuesday; none did in 2013.

Two-thirds of a year comes free: the Open Data API covers 2014, listing **22 term-7
sitting days** before the July handover.

### Identity: better than feared, and only half a problem
`MepId` is **one stable namespace across terms**, which the first pass did not establish.
Of the 693 MepIds in the 2013-01-15 sitting:

| Route | Term-7 members reached |
|---|---|
| Already in the `id_bridge` learned from 2023+ documents | 109 (16%) |
| Also present in term-8 documents (names agree 322/332, 97%) | 332 (48%) |
| In neither — left Parliament in 2014 | **353 (51%)** |

The ten name disagreements are rendering variants of the same person — "Le Pen
Jean-Marie" against "Le Pen", "Mato Adrover" against "Mato" — which corroborate the join
rather than undermine it.

So roughly half the term needs no inference at all. For the other half, parltrack's
`ep_meps.json.zst` is already on disk and carries **441 term-7 MEPs** with `UserID` (the
EP's own person identifier, the one our `member_id` uses) and a `Name.aliases` list
holding exactly the surname forms the XML uses. Matching on alias plus political group,
cross-checked against the 59 sittings both sources cover, should close it — and the
signature approach described above remains as the fallback where it does not.

## What this would cost
Roughly a milestone: a `P7` URL pattern, sitting enumeration, signature-based identity
inference, ingest-from-XML (rather than from a dump), then the existing verify, mine and
publish stages unchanged. Term-7 votes would arrive without the procedure metadata the
later terms carry, though the dossier dump should supply titles and subjects as it did
for the 8th.

## What is actually left
1. **Ingest from Parliament's own XML** — a `P7` URL pattern plus a loader, because there
   is no dump to load from. This is the bulk of the work.
2. **Identity for the ~51%** who left in 2014, by alias matching against the parltrack
   MEP dump already on disk.
3. **Verification loses its independent check.** This is the real methodological cost and
   the reason to hesitate. For 2014 onwards a third party supplies the ballots and
   Parliament checks them; for the 7th term Parliament would be the only source, so
   "verified against the record" becomes "is the record". Parltrack corroborates 59 of
   roughly 180 sittings and nothing corroborates the rest. The platform's central claim
   would hold for three terms and not the fourth, and the interface would have to say so
   per term rather than in a footnote.
4. **Retry on Parliament's HTML-under-200 error** before a five-year crawl, since the
   archiver currently aborts.
5. **Procedure titles and subjects** from the dossier dump, as for the 8th term — its
   term-7 coverage is not yet measured.

## The question this really raises
Whether a fourth term is worth it at all. The platform now covers 2014 onwards with
every ballot verified. Adding 2009-2014 buys a fifteen-year view and would make
`FR04`'s "derived semantics across the whole history" genuinely long-range — against a
source that is thinner, an identity problem that needs inference rather than a join, and
a sitting list nobody publishes in machine-readable form. That is a judgement about what
the platform is for, not a technical blocker.
