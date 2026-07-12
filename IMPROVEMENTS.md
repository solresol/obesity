# IMPROVEMENTS.md

*Analysis date: 2026-07-11*

This repository holds reproducible analyses of whether obesity prevalence is
associated with residential altitude (Australia focal case; USA, Peru, NZ as
comparisons). It has migrated from a notebook-only workflow ("Join health
stats with altitude.ipynb") to a two-script pipeline
(`scripts/fetch_sources.py`, `scripts/run_analysis.py`) with outputs under
`data/processed/` and `outputs/`. The git history is only two commits, and
almost the entire current pipeline — `scripts/`, `data/`, `docs/`, `outputs/`,
`AGENTS.md`, `requirements.txt`, the `usa/` dataset, `existing-papers/` — is
sitting untracked in the working tree.

## Housekeeping (highest priority)

- **Commit the actual project.** `git status` shows `scripts/`, `docs/`,
  `data/`, `outputs/`, `AGENTS.md`, `requirements.txt`, `usa/`, `cite.txt`,
  and the notebook copy are all untracked, plus uncommitted edits to
  `README.md`, `.gitignore`, and the main notebook. One disk failure loses
  the whole pipeline. Stage and commit in logical chunks now.
- **Decide what belongs in git.** `AGENTS.md` says paper drafting belongs in
  `../papers`, yet `obesity-paper.docx` and `existing-papers/` (third-party
  PDFs, possible copyright/licensing issue in a public repo) sit at the root.
  Move the docx to `../papers`; either move the PDFs there or add
  `existing-papers/` to `.gitignore` and record citations in `cite.txt`/a
  BibTeX file instead.
- **Set up a remote.** There is no `origin`; the repo cannot be pushed or
  backed up.
- **Delete or ignore cruft:** `scripts/__pycache__/` (add `__pycache__/` is
  already in `.gitignore` — good, just don't commit it),
  `"Join health stats with altitude-Copy1.ipynb"` (a `-Copy1` checkpoint has
  no place in version control), and stale root-level artifacts from the
  notebook era (`altitudes.csv`, `chart-ready-data.csv`,
  `aust_health_tracker_data_lga.xlsx`, `lga-stats/`) that duplicate what the
  scripted pipeline now produces under `data/`.

## Modernization: migrate to uv

- Replace `requirements.txt` with a `pyproject.toml` managed by uv:
  `uv init`, then `uv add pandas numpy scipy statsmodels scikit-learn
  matplotlib seaborn requests openpyxl shapely curl_cffi`, commit
  `pyproject.toml` and `uv.lock`, delete `requirements.txt`.
- Update README/AGENTS commands to `uv run scripts/fetch_sources.py` and
  `uv run scripts/run_analysis.py`. Versions are currently unpinned, which
  undermines the "reproducible" claim; `uv.lock` fixes that for free.

## Code structure

- `scripts/fetch_sources.py` (1,815 lines) and `scripts/run_analysis.py`
  (1,912 lines) are monoliths. Split into a small package (e.g.
  `obesity_altitude/` with `au.py`, `us.py`, `peru.py`, `nz.py`,
  `elevation.py`, `models.py`) with thin CLI entry points, or at minimum add
  per-country subcommands (`fetch_sources.py --country au`) so a failed
  download for one country doesn't force re-running everything.
- Add resumable/cached fetching guarantees: document (or assert) that
  `fetch_sources.py` skips already-downloaded files in `data/raw/` and is
  polite to OpenTopoData/Open-Meteo rate limits (retry with backoff).
- Make `run_analysis.py` fail loudly with a clear message when
  `data/processed/` inputs are missing, pointing at `fetch_sources.py`.

## Testing

- No tests exist. Add a `tests/` directory with:
  - Unit tests for the pure transformation/join functions (LGA/PHA joins,
    elevation weighting, regression setup) using tiny fixture CSVs.
  - A schema/smoke test asserting each `data/processed/*.csv` has the
    expected columns and plausible ranges (obesity 0–100%, altitude
    -100–5,000 m), so silent upstream format changes are caught.
- Run via `uv run pytest`.

## Documentation

- README's output list is long and will drift; consider generating it, or
  trim to the key outputs and point to `outputs/reports/analysis_summary.md`.
- `docs/data-sources.md` exists — good. Add retrieval dates and exact URLs
  for every source (PHIDU, ABS ASGS 2021, CDC PLACES 2025, INEI ENDES 2024,
  NZ MoH 2026) since several are point-in-time releases.
- Document what `usa/contaminants_obesity_cleaned.csv` is and where it came
  from; it looks like an orphaned side analysis with no README mention.
- Add a short note on the two historical notebooks: kept for provenance,
  superseded by `scripts/`.

## Quick wins

- `git rm --cached`/ignore `.DS_Store` (already in `.gitignore` — verify none
  are tracked).
- Add a `Makefile` or `justfile`: `make fetch`, `make analysis`, `make test`.
- Pin the OpenTopoData datasets used per country in one constants module so
  the README and code can't disagree.
- Commit `outputs/tables/*.csv` and `outputs/reports/analysis_summary.md`
  (small, reviewable) but consider ignoring large regenerable PNGs, or use
  git-lfs if figure history matters.

## Security

- No credentials or API keys were found in the scripts or docs. All data
  sources appear to be public APIs. Keep it that way — if any keyed API is
  added later, read it from the environment, never the repo.
