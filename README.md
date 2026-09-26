# EU Parliament votes

Fetches European Parliament roll-call votes, normalizes them, mines them for how MEPs
and political groups actually vote, and publishes the result as data a dashboard can
consume.

- **Parliament is the reference of record.** Every ballot is verified against the EP's
  own roll-call XML, and every published vote cites the document it came from.
- Where the data comes from, and what was rejected: [docs/data-source.md](docs/data-source.md)
- What we may republish and what we owe: [docs/licensing.md](docs/licensing.md)
- Plan, architecture and milestones: [`projector/`](projector/)

## Setup

Python 3.12+:

```
$> python3 -m venv venv
$> ./venv/bin/pip install -r pipeline/requirements.txt
$> ./venv/bin/playwright install chromium     # needed by the `archive` stage
```

## Pipeline

```
$> ./venv/bin/python -m pipeline all
```

Or any stage on its own, in order:

| Stage | What it does |
|---|---|
| `fetch` | Download a source release (terms 9-10) and pin its tag |
| `term8` | Ingest the 2014-2019 term from its separate source |
| `etl` | Load everything into `data/eu_votes.duckdb` |
| `validate` | Sanity-check the store against seat counts and published tallies |
| `archive` | Download Parliament's roll-call XML for every sitting |
| `verify` | Compare every ballot against that archive |
| `mine` | PCA positions, group cohesion, topics |
| `publish` | Emit the JSON bundles the UI consumes |
| `site` | Assemble `site/` — interface plus data, ready to upload |

`fetch` defaults to the latest weekly release and records which one it used. Pin it to
reproduce an earlier build, since `latest` moves every week:

```
$> ./venv/bin/python -m pipeline fetch --tag 2026-09-26
```

Everything lands under `data/` (gitignored): raw releases with a `provenance.json`
recording release tag, checksums and the script commit; the DuckDB store; the archived
EP record; and the published bundles.

## Deploying

```
$> ./venv/bin/python -m pipeline site
```

Produces a self-contained `site/` directory — the interface, the published bundles and
their licence — that can be uploaded to any static host. No build step, no server-side
anything. See [ui/README.md](ui/README.md).

### A note on `archive`

Parliament's roll-call documents are public and need no account, but sit behind an AWS
WAF JavaScript challenge — plain HTTP clients get an empty `HTTP 202` that looks
exactly like the file not existing. The stage drives headless Chromium to solve the
challenge, then reuses the resulting short-lived token for as many sittings as it
lasts. It is incremental and append-only: these documents never change once published,
so a re-run fetches only what is missing.

## What's in the store

Roll-call votes and individual ballots for the 8th (2014-2019), 9th (2019-2024) and
10th (2024- ) terms, with MEPs reconciled to a single identity across all three.

Terms are not equivalent, and the pipeline does not pretend otherwise: the 8th term
comes from a different source that records only MEPs who actually voted, carries no
main-vote flag and no subject tags. Those fields are NULL for that term rather than
guessed, and figures derived from them cover 2019 onwards only.

## Legacy

The original 2019 analysis of the 2014-2019 term lives in [`attic/`](attic/) —
retained for reference, not maintained, and not runnable. See `attic/README.md`.
