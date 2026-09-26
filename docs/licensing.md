# Licensing of ingested and republished data

What we may do with the data we load, and what we owe in return. This is a reading of
the licences, not legal advice; where it matters commercially, get a lawyer.

Task: `projector/tasks/TK12-review-data-licensing.md`. Reviewed 2026-09-26.

## What we ingest

| Source | Licence | What it covers |
|---|---|---|
| [HowTheyVote dataset](https://github.com/HowTheyVote/data) | Open Database License (ODbL) 1.0 | The CSV release we load |
| European Parliament documents & API | EU reuse terms (see below) | Roll-call XML we archive; the underlying record |

## ODbL: which of our outputs is which

ODbL draws a line that decides everything here:

- A **Derivative Database** is "a database based upon the Database… any translation,
  adaptation, arrangement, modification, or any other alteration". Publishing one
  triggers **share-alike** (§4.4a) — it must be released under ODbL or a compatible
  licence — plus the full licence notice (§4.2).
- A **Produced Work** is "a work (such as an image, audiovisual material, text, or
  sounds) resulting from using… the Contents". Publishing one triggers **no
  share-alike** (§4.5b), only a notice making viewers aware the content came from the
  Database (§4.3).

Applied to what this project emits:

- **`data/published/*.json` (`IF-PUBLISHED-DATA`) is a Derivative Database.** It is
  structured data restructured from theirs — MEP records, vote records, ballots
  aggregated. Share-alike applies.
  → **Published under ODbL, with attribution to HowTheyVote and to Parliament.**
- **The dashboard, its charts, and topic stories are Produced Works.** Pages, figures
  and narrative built by querying the data.
  → Attribution notice required; the site's own code and prose are ours to license as
  we choose.

The PCA coordinates and cohesion scores are our own computation rather than their
content, which arguably makes them a Produced Work even though they travel in a
database. We do not rely on that distinction: the bundles ship as ODbL regardless,
which is the conservative reading and costs us nothing we wanted.

## European Parliament reuse terms

Reuse of EU-owned content marked "© European Union — Source: European Parliament" is
authorised **for personal and commercial purposes**, on conditions:

- the **entire item** is reproduced and the **source acknowledged**, citing the
  complete URL;
- indications of author or source must not be deleted or altered;
- trademarks and logos (europarl®, Parlamentarium® and similar) need prior consent;
- some datasets may carry different conditions, and third-party content within EP
  documents is not covered.

Our archive of roll-call XML (`TK09`) reproduces entire documents unaltered, which is
what these terms ask for. If the archive is ever republished rather than kept as local
evidence, each document must carry its source notice and original URL.

## What this obliges us to do

1. Publish `IF-PUBLISHED-DATA` bundles under **ODbL 1.0**, with the licence URI
   included.
2. Attribute both sources wherever data is shown: the **European Parliament** as the
   source of record, and the **HowTheyVote dataset** as the ingest path, per ODbL §4.3.
3. Preserve source notices on anything derived from EP documents; never strip
   attribution from archived material.
4. Keep the platform's own code and written content on a separate licence of our
   choosing — share-alike reaches the database, not the site.

## Open point

Whether to republish the EP roll-call archive itself (rather than keeping it as local
verification evidence) is undecided. It would strengthen the transparency claim — a
reader could re-run our verification without re-crawling Parliament — but it means
redistributing ~1GB of EP documents under their reuse terms, so it needs a deliberate
decision rather than drifting into it.
