# Where this project's data comes from

This project makes claims about how Members of the European Parliament voted. A claim
like that is only as good as the chain behind it, so this document records where the
data comes from, what was considered and rejected, and what the known limits are.

Decision date: 2026-09-26. Task: `projector/tasks/TK01-identify-document-raw-source.md`.

## The short version

| | |
|---|---|
| **Data we ingest** | The [HowTheyVote.eu dataset](https://github.com/HowTheyVote/data), weekly CSV releases |
| **Licence** | Open Database License (ODbL) |
| **Coverage** | 9th term onwards (2019-07-15 →), 25,204 roll-call votes, 1,279 MEPs |
| **Primary record we verify against** | The European Parliament's own roll-call XML, published per sitting in the plenary minutes |

We deliberately ingest a third-party derivation rather than the Parliament's own API.
The reason is specific and worth stating plainly: **the EP's official Open Data API
publishes only aggregate vote tallies — how many voted for, against, abstained — not
how each individual MEP voted.** Individual ballots are published by the Parliament,
but as roll-call XML attached to each sitting's minutes, not through the API.

## What was compared

### 1. European Parliament Open Data Portal — `data.europarl.europa.eu`

The authoritative, official source, and the one we would prefer on principle. Its API
v2 is live and mature (verified: a `/api/v2/meetings` query returns well-formed
JSON-LD with parliamentary term, attendance and document linkage).

Rejected as the ingest path because its vote endpoints return aggregate counts only —
`votesFor`, `votesAgainst`, `abstentions`, `result` — with no per-MEP breakdown. A
dataset of aggregate tallies cannot answer any question this project exists to answer;
every use case depends on attributing a ballot to a named MEP.

We have since inspected the Parliament's roll-call XML directly and confirmed what it
does and does not contain — see *Verification* below.

*A note on retrieval:* these documents are public and need no account, but the
Parliament fronts them with an AWS WAF JavaScript challenge (`x-amzn-waf-action:
challenge`). Plain HTTP clients — curl, scripted fetchers — receive an empty `HTTP 202`
rather than the file, which can easily be mistaken for the document being unavailable.
A real browser passes the challenge transparently. The files used below were retrieved
by driving a browser and reusing the resulting `aws-waf-token`.

### 2. Parltrack — `parltrack.org`

The source the original 2019 version of this project used (the old notebooks expect
`ep_meps_current.<date>.json` and `ep_votes.<date>.json`, which match parltrack's dump
format). Still alive and still publishing.

Rejected on freshness. At the time of checking, `ep_votes.json.zst` was last modified
**28 March 2026** — roughly six months stale — while `ep_meps.json.zst` was current to
24 July 2026. For a project whose whole point is showing what Parliament is doing
*now*, ingesting a six-month-old vote record would mean publishing a stale picture and
calling it current.

Parltrack remains relevant for one thing: it covers terms before 2019, which
HowTheyVote does not. If the 2014-2019 term is ever brought back in (`TK08`), this is
where it would come from.

### 3. HowTheyVote.eu — **selected**

An independent transparency project that parses the Parliament's plenary minutes and
Legislative Observatory, and republishes the result as clean, weekly CSV releases.

What it gives us, verified against the 2026-09-26 release rather than taken on trust:

- **`member_votes.csv`** — the thing that matters: one row per MEP per vote, with
  position `FOR` / `AGAINST` / `ABSTENTION` / `DID_NOT_VOTE`. Note that "did not vote"
  is recorded explicitly. The old pipeline could only infer absence from a missing
  value, which silently conflated "was there and abstained from voting" with "we have
  no data" — and that distinction biases every attendance figure.
- **`votes.csv`** — 25,204 votes from 2019-07-15 to 2026-09-17, with procedure
  references, subject metadata, and an `is_main` flag separating 2,462 substantive
  final votes from 22,742 amendment and procedural votes. The original analysis
  treated all votes as equivalent; this flag makes it possible not to.
- **`group_memberships.csv`** — political group affiliation with `start_date` /
  `end_date` per term, so an MEP's group *at the time of a given vote* is recoverable.
  The old pipeline stored a single `current_group` per MEP, which quietly erased every
  mid-term defection and reassignment.
- **`members.csv`** — 1,279 MEPs across both terms under one stable identifier, so a
  person serving in both terms is one person rather than two rows.
- **`eurovoc_concept_votes.csv`**, `oeil_subject_votes.csv`, `geo_area_votes.csv` —
  official EuroVoc and Legislative Observatory subject tags per vote, i.e. topic
  labels sourced from the Parliament itself rather than inferred by us.

Licence is ODbL, releases are tagged by date and retrievable by stable URL, which
means any figure we publish can cite the exact release it came from.

## Verification

`python -m pipeline spotcheck` compares our store against Parliament's own roll-call
XML. Across four sittings — 2019-10-10 and 2020-01-15 (pre-Brexit), 2023-11-22
(post-Brexit) and 2026-09-17 (current term) — **all 628 votes agree, with no
discrepancies.** On the two sittings whose XML identifies members in a form we can
match, every individual ballot agrees too, not merely the totals.

This is the check that matters most, because it is the only one that does not rely on
the source vouching for itself.

It also established two things about the primary record:

- **Parliament publishes only For / Against / Abstention.** There is no "did not vote"
  list. Our `DID_NOT_VOTE` figures are derived by HowTheyVote from the sitting roster,
  so they are an inference — a well-founded one, but not something Parliament states.
- **The XML is not flawless.** In vote 161290, the abstention count is replaced by a
  multilingual "corrections and voting intentions" heading. Our checker reports such
  cases as defects in the EP record rather than silently attributing them to our data.

## Known limits

These are properties of the data, and they apply no matter how careful the code is:

1. **We ingest a derivation, not the primary record.** HowTheyVote state their
   collection is fully automated and that they cannot rule out missing or erroneous
   individual votes. We therefore treat them as an ingest convenience, not an
   authority: `TK06` spot-checks our published figures against the Parliament's own
   roll-call record, per term.
2. **Roll-call votes only.** Votes taken by show of hands or by secret ballot are not
   recorded per-MEP by anyone, the Parliament included. Any statement we make about an
   MEP's record is a statement about their *roll-call* record, and should say so.
3. **History starts in 2019.** The 8th term (2014-2019) is out of scope, and the
   analysis this repository previously published covered exactly that term — so the
   old published figures are not comparable to the new ones.
4. **Amendment votes dominate by count.** 90% of rows are amendment or procedural
   votes. Any aggregate computed without regard to `is_main` is dominated by
   procedural noise rather than substantive positions.

## Reproducing the ingest

The stable links below always resolve to the latest release; a specific release can be
pinned by replacing `latest/download` with `download/<tag>`:

```
https://github.com/HowTheyVote/data/releases/latest/download/member_votes.csv.gz
https://github.com/HowTheyVote/data/releases/latest/download/votes.csv.gz
https://github.com/HowTheyVote/data/releases/latest/download/members.csv.gz
https://github.com/HowTheyVote/data/releases/latest/download/group_memberships.csv.gz
```

Every artifact this project publishes records which release tag it was built from, so
a reader can retrieve the same inputs and re-run the pipeline. See
`projector/requirements/FR01-provenance-chain.md`.
