---
id: TK15-restore-mep-attributes
title: Restore the Full MEP Attribute Set
status: todo
component: CMP-ETL
---
# TK15 — Restore the Full MEP Attribute Set

## Scope
The 2019 analysis carried, for every MEP: name, country, group, constituency, gender,
birthdate, photo, European Parliament homepage and email. The current store keeps name
and country; birthdate is present for 289 of 855 term-8 MEPs and email for 125, and
only because those MEPs also served after 2019.

This is a plain regression under `FR03`, and a cheap one to fix: every missing field is
already in the parltrack dump the pipeline downloads (`Photo`, `Gender`, `Birth`,
`Constituencies`, `Mail`, `meta.url`), and the equivalent fields exist for terms 9-10 in
the primary source. The term-8 ingest simply never read them.

Beyond parity, these fields are what make an MEP page recognisable to a citizen rather
than a row in a table (`UC01`): a photo, a constituency, a link to their official page.

## Acceptance criteria
- MEP records carry at least the 2019 field set, for every term.
- Fields genuinely absent from a source are NULL and identified as such, not
  back-filled by guesswork.
- Published `meps.json` exposes them, with attention to size: a photo is referenced by
  URL, never embedded.
- Personal data is limited to what Parliament itself publishes about MEPs acting in
  their public role.
