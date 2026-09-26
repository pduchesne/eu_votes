# Retired — the original 2019 analysis

Everything in this directory is the project's first incarnation: a Jupyter-based
analysis of the **2014-2019 (8th) parliamentary term**, published as a static HTML
export. It is kept for reference and provenance, **not maintained, and not run**.

It is superseded by the pipeline in `../pipeline/` — see the top-level `README.md`.

Do not run anything here expecting current results:

- `ep_meps_extract.ipynb` is Python 2 and does not execute at all.
- `ep_votes_extract.ipynb` contains a leftover `if idx > 10: break` debug guard that
  silently truncates extraction.
- `eu_utils.py:51-52` says it selects MEPs voting in "at least 40%" of votes while the
  code filters on 10% — the kind of drift that went unnoticed because nothing checked.
- The notebooks expect raw dumps to appear in a `tmp/` directory by hand, from a source
  that was never documented.
- `FinalResults.ipynb` renders through `plotly.plotly`, the retired chart-studio cloud
  API.

`computed/` and `output/` hold the derived artifacts of that pipeline, including the
70MB `meps_votes.csv` and the 6.8MB exported report. `viz_tests/` holds abandoned
experiments with Altair, Vega, D3 and Plotly — their conclusion is recorded in the
`CMP-UI-3DVIEW` component decision.

`requirements.txt` here describes that old stack (jupyterlab 1.0a3, plotly 3.8,
`sklearn>=0.0`). The current pipeline's dependencies are in `../pipeline/requirements.txt`.

The 2014-2019 term itself is *not* abandoned — it is being brought into the new
pipeline from a properly documented source (`TK13`), so these results will eventually
be reproducible rather than merely archived.
