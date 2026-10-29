# report: final report (BCE497J)

Sources and tooling for the final project report. One report is generated per
team member from the same content.

| Path | Contents |
|------|----------|
| `content/` | Chapters `ch01` to `ch10` as Markdown, `facts.json` (every number with its source), `references.json`, recorded test results (`unit_test_results.json`, `api_test_results.json`, `pipeline_results.json`). Format: `content/README_CONTENT_FORMAT.md` |
| `figures/` | Diagrams, charts, UI screenshots and `overlays/` (mask overlays of the sample images) |
| `build/` | Scripts that build the DOCX and PDF, make figures and run the tests |
| `output/` | Built DOCX and PDF reports |
| `OPEN_ITEMS.md` | Values and measurements still missing |

## Build scripts

| Script | Purpose |
|--------|---------|
| `build_report.py` | Builds the DOCX files from `content/` and `figures/` |
| `docx_helpers.py` | Helpers used by `build_report.py` |
| `make_diagrams.py`, `diagram_lib.py` | Draws the architecture and flow diagrams |
| `make_montage.py` | Sample-image montage |
| `make_ui_screenshots.py` | Screenshots of the running web UI (needs Microsoft Edge and a running `app/server.py`) |
| `run_unit_tests.py`, `run_api_tests.py`, `run_pipeline_test.py` | Produce the JSON result files in `content/` |

## Build

The scripts were written for Windows and use `pywin32` and `pymupdf`.

```powershell
python -m venv .venv-report
.venv-report\Scripts\Activate.ps1
pip install -r report/build/requirements.txt
python report/build/build_report.py
```

`run_pipeline_test.py` and `run_api_tests.py` also need the app dependencies
(`pip install -r app/requirements.txt`) and the model files from `git lfs pull`.
The DOCX output follows the VIT BCE497J report template, which is not included
in this repository.

Back to the [main README](../README.md).