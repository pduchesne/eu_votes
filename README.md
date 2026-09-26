# EU Parliament votes

Fetches European Parliament roll-call votes, normalizes them, and (in progress) mines
them to show how MEPs and political groups actually vote.

Where the data comes from, what was rejected and why: [docs/data-source.md](docs/data-source.md).
Project plan, architecture and milestones: [`projector/`](projector/).

## Pipeline

Requires Python 3.12+ and a virtualenv:

```
$> python3 -m venv venv
$> ./venv/bin/pip install -r pipeline/requirements.txt
```

Run the whole thing, or any stage on its own:

```
$> ./venv/bin/python -m pipeline all        # fetch + etl + validate
$> ./venv/bin/python -m pipeline fetch      # download a source release
$> ./venv/bin/python -m pipeline etl        # load into data/eu_votes.duckdb
$> ./venv/bin/python -m pipeline validate   # sanity-check the store
```

`fetch` defaults to the latest weekly source release and records which one it used.
To reproduce an earlier build, pin the release explicitly — `latest` moves every week:

```
$> ./venv/bin/python -m pipeline fetch --tag 2026-09-26
```

Everything lands under `data/` (gitignored): raw release files with a `provenance.json`
recording the release tag, per-file checksums and the script commit, and the normalized
DuckDB store built from them.

The store currently holds 25,204 roll-call votes and 17.9M individual ballots covering
the 9th term (2019-2024) and the 10th (2024- ) to date. `validate` checks it against
known seat counts and the source's own published tallies, and exits non-zero on any
violation.

## Legacy (2014-2019)

The notebooks in the repository root (`FinalResults.ipynb`, `DataMining.ipynb`,
`ep_*_extract.ipynb`), `eu_utils.py`, `computed/`, `output/` and `viz_tests/` are the
original 2019 analysis of the 2014-2019 term. They are superseded by the pipeline above
and are **not** maintained — `ep_meps_extract.ipynb` is Python 2 and no longer runs at
all, and the old `requirements.txt` describes that stack rather than this one.

Their fate is an open decision tracked in
[`TK08`](projector/tasks/TK08-retire-legacy-pipeline.md): the 2014-2019 term is not
available from the current data source, so keeping that history would mean maintaining
a second source.
