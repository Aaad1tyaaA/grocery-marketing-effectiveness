# Grocery Marketing Effectiveness handoff

Start with [README.md](README.md) for findings, reproduction and the public repository map. Analysis modules 1-6, the corrected local Excel ROI workbook and the one-page recommendation memo are complete.

- [Executive memo](docs/crm_recommendation_memo.pdf) and [evidence links](docs/memo.md).
- [Dashboard controls and current save status](POWER_BI_START_HERE.md): the latest four-page source is saved in `dashboard/final/Grocery Marketing Final.pbip`. The original local handoff now contains the final embedded-data `dashboard/Grocery Marketing Final.pbix` and native four-page `dashboard/Grocery Marketing Final.pdf`. The final report passed 660 checks; the PDF was visually reviewed and corrected before delivery.
- [Excel specification](excel/README.md) and `excel/campaign_roi_model_v3.xlsx` in the original local handoff; the workbook is excluded from GitHub because it contains household lookups.
- [Resume and interview walkthrough](docs/resume_and_walkthrough.md).

The original local handoff has nine source datasets, 123 database checks, 65 CSV comparisons and six executed notebooks. Its full regression suite passed 38 tests. Public CI uses synthetic and summary data and skips checks that require excluded raw files. Raw sources, reporting databases, cached report data and the private reference guide remain local. Public notebook outputs are cleared.

Run `python scripts/run_all.py` after installing `requirements-hillstrom.txt` and `requirements-tests.txt` to rebuild and validate the analysis on a new machine. Disconnect DBeaver before rebuilding reporting databases. Run `python scripts/export_dashboard_data.py` to generate Power BI refresh CSVs.
