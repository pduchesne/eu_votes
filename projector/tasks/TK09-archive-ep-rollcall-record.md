---
id: TK09-archive-ep-rollcall-record
title: Archive Parliament's Roll-Call Record for Every Sitting
status: done
component: CMP-FETCH
---
# TK09 — Archive Parliament's Roll-Call Record for Every Sitting

## Scope
Build the crawler that gives `FR02-primary-record-verification` something to verify
against: Parliament's roll-call XML for every sitting in scope (T9 and T10), stored
locally as our own evidence archive rather than as links we hope remain live.

Known mechanics, already established in `TK06`:
- Sitting dates are enumerable from the official Open Data API (`/api/v2/meetings`,
  confirmed working and returning parliamentary term and sitting identifiers).
- Documents live at
  `europarl.europa.eu/doceo/document/PV-{term}-{date}-RCV_EN.xml`.
- **Retrieval needs a browser.** The EP fronts these with an AWS WAF JavaScript
  challenge; plain HTTP clients get an empty `HTTP 202`, which reads exactly like the
  document not existing. A real browser solves the challenge and yields an
  `aws-waf-token` cookie that plain `curl` can then reuse — but the token expires in
  minutes, so the crawler must mint fresh ones as it goes.
- Roughly 400+ sittings, individual files ranging from ~1.4MB to ~17MB.

Crawl politely: this is a public institution's infrastructure and the WAF exists
because of bulk scraping. Fetch incrementally, cache permanently (these documents do
not change once published), and only ever fetch a sitting once.

## Outcome (2026-09-26)
**577 sittings archived, ~2.4GB**, covering all three terms. Incremental and
append-only; a re-run fetches only what is missing.

Two things only contact with the real thing revealed:
- **The 8th term predates the doceo scheme entirely.** Its documents live under
  `RegData/seance_pleniere/proces_verbal/{year}/{md}/liste_presence/P8_PV(...)`. A first
  run built doceo URLs for term 8, got 404 for all 230 sittings and recorded them as
  "absent" — which would have permanently poisoned the archive index had it not been
  caught and cleared.
- **Only doceo paths trigger the WAF.** The token must therefore be minted against a
  doceo URL even when the document being fetched lives elsewhere; minting against a
  RegData URL yields no token at all.

2 sittings have votes in our store but no roll-call document, recorded as `absent` so
they are neither retried forever nor mistaken for failures.

## Acceptance criteria
- Every sitting in T9 and T10 with roll-call votes has its XML archived locally.
- Archive is incremental and idempotent: a re-run fetches only sittings not yet held.
- Token acquisition and renewal are automatic; a challenge failure is reported clearly
  rather than being mistaken for a missing document.
- Each archived file records its retrieval date and source URL, feeding
  `FR01-provenance-chain`.
- A sitting that genuinely has no roll-call XML is recorded as such, so it is not
  retried forever and is not confused with a fetch failure.
