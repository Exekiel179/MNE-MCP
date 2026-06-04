# Contributing to MNE-MCP

Thanks for your interest in improving MNE-MCP. This guide covers the dev setup, the test/lint
workflow, and how the project is released.

## Development setup

```bash
git clone https://github.com/Exekiel179/MNE-MCP.git
cd MNE-MCP
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[ica,dev]"                        # or ".[full,dev]" for the advanced tools
```

`status` confirms the environment:

```bash
mne-mcp status
```

## Tests

```bash
pytest -q                                          # fast unit tests (synthetic data, no downloads)
pytest -q --cov=mne_mcp --cov-report=term-missing  # with coverage
python tests/smoke_pipeline.py                     # synthetic end-to-end smoke
python tests/smoke_eegbci.py                       # REAL-data smoke (downloads PhysioNet eegbci)
```

- Unit tests must stay fast and **offline** (synthetic data only).
- The real-data smoke (`smoke_eegbci.py`) downloads a small public dataset; it **skips cleanly** if
  the network is unavailable so it never flakes CI.
- Advanced tools (connectivity, source, decoding) need the `[full]` extra; tests that require an
  optional package guard it with `pytest.importorskip(...)`.

## Lint / formatting

The project uses **black** (line length 88) and **isort** (black profile). CI checks both:

```bash
black src tests
isort --profile black src tests
```

## Adding an analysis skill

Analysis skills live in `skills/` and follow the suite contract documented in
`skills/MNE_ANALYSIS_SUITE.md`: a three-phase **GRILL → ANALYZE → CRITIC** workflow, with
methodology review delegated to `mne-methodology-critic`. Use `mne-spectral` as the template, keep
each skill self-contained (it is installed per-folder by `mne-mcp setup`), and add the skill name to
`SKILL_NAMES` in `src/mne_mcp/claude_config.py`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **unit** — Linux/macOS/Windows × Python 3.10/3.12 (with coverage)
- **numpy-compat** — NumPy 1.x and 2.x
- **real-data-smoke** — the eegbci Berger-effect end-to-end
- **lint** — black + isort

All jobs must be green to merge.

## Releasing

1. Update `CHANGELOG.md` and bump `src/mne_mcp/_version.py`.
2. Tag the release: `git tag v0.x.y && git push --tags`.
3. `.github/workflows/release.yml` builds the sdist/wheel and publishes to PyPI via
   [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (configure the PyPI publisher for
   this repo once, no stored token needed).

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`. For analysis bugs, include the recording
format, the `mne_check_status` output, and the failing tool call.
