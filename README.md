# Does direct marketing actually grow customers?

[![Regression checks](https://github.com/Aaad1tyaaA/grocery-marketing-effectiveness/actions/workflows/ci.yml/badge.svg)](https://github.com/Aaad1tyaaA/grocery-marketing-effectiveness/actions/workflows/ci.yml)

**Recommendation for the Head of CRM:** don't scale grocery campaigns on today's evidence; run a randomized holdout first. In the staged common-support comparison, Campaign 18's targeted households spent **$34.77 more per week** than controls, but earlier-window matching reduces the estimate to **$2.95 (95% CI −$0.74 to $6.64)**. All three preferred campaign estimates have intervals that include zero.

[Decision memo (PDF)](docs/crm_recommendation_memo.pdf) · [Power BI dashboard (PDF)](dashboard/Grocery%20Marketing%20Final.pdf) · [Excel ROI specification](excel/README.md) · [Experiment readout](docs/experiment_readout.md) · [Metric glossary](docs/metric_glossary.md) · [Cleaning log](docs/cleaning_log.md)

![How the campaign estimate changes as the comparison improves](charts/campaign_estimate_path.png)

![Business health dashboard page](charts/dashboard_business_health.png)

## What I found

| Question | Finding | What it means |
|---|---|---|
| Who creates value? | 416 "Champion" households (17%) account for 44.7% of grocery spend. | Protect these relationships; test retention offers rather than blanket discounts. |
| Where is spend slipping? | 755 declining households fell from $699K in H1 to $380K in H2. | A place to investigate, not a forecast of recoverable revenue. |
| Do campaigns add sales? | Raw gap $34.77/week; matched on an earlier window, $0.39 to $2.95/week, every interval includes zero. | Run a randomized holdout before claiming incremental profit. |
| Do displays and mailers work? | Products on display and in the mailer sell 3.14× their usual units. | A strong association worth testing; price and selection aren't controlled. |
| What does a real experiment say? | In a separate randomized email test (64,000 customers), the Men's email adds $0.77 per customer over two weeks (95% CI $0.48 to $1.04). | Shows how to read an experiment; it's a different retailer, so it doesn't validate the grocery numbers. |

## How I got there

1. **Data model:** 1.47M transaction line items, 20.9M promotion records and 27 campaigns, modelled into a star schema in DuckDB with a [cleaning log](docs/cleaning_log.md) of every rule and its row count.
2. **Business health:** weekly KPIs, discount depth and category discount dependence.
3. **Customers:** RFM-style segments, H1-vs-H2 spend trajectories and monthly cohorts.
4. **Promotions:** unit lift by display and mailer placement against each product-store's own baseline.
5. **Campaigns:** four designs, from a naive gap to difference-in-differences matched on an earlier window, with fake-start placebo tests. The pre-period-matched estimate looked significant, but a placebo test found a similar "lift" before the campaign started, so I didn't trust it.
6. **Randomized benchmark:** the Hillstrom email experiment, with sample-ratio checks, bootstrap intervals and Holm correction.
7. **Decision tools:** an Excel ROI and break-even model (Data Table, Goal Seek, holdout sizing), a four-page Power BI report, a Streamlit summary app and a one-page memo.

## Reproduce it

```text
python -m pip install -r requirements.txt
python scripts/run_all.py
python -m pytest -q tests
```

`run_all.py` downloads the checksum-pinned sources, builds the DuckDB databases, executes the six notebooks and verifies their outputs against the saved models. The raw files and databases aren't committed; the first run needs a few GB of disk and some time. The SQL lives in `sql/`. Public notebooks retain aggregate outputs; outputs containing household, basket or source-row identifiers are removed with `python scripts/prepare_publication.py` before publication. A local rebuild restores the complete outputs.

**App:** `python -m pip install -r app/requirements.txt`, then `python -m streamlit run app/streamlit_app.py`. It runs on the small summary files in `app/data/`, so it works without the raw data.

**Power BI:** open `dashboard/final/Grocery Marketing Final.pbip`, run `python scripts/export_dashboard_data.py`, point the `DataFolder` parameter at the generated `dashboard/data` folder and refresh. See [docs/power_bi.md](docs/power_bi.md).

## Repository map

| Folder | Contents |
|---|---|
| `sql/` | Modelling and analysis queries; `sql/learning/` holds step-by-step exploration queries |
| `scripts/` | Ingestion, module builders, exports and verification |
| `01_*.ipynb` to `06_*.ipynb` | One notebook per module, with aggregate outputs |
| `tests/` | Data checks, synthetic regression tests and an app smoke test (run in CI) |
| `app/` | Streamlit summary app and its aggregate data |
| `dashboard/` | Power BI project source and the four-page PDF |
| `excel/` | Campaign ROI specification; the workbook with household lookup data stays local |
| `docs/` | Memo, readouts, glossary, cleaning log, AI log and [verification records](docs/README.md) |

## Data and limits

- **Grocery data:** 84.51° Complete Journey 2.0, via the [`completejourney`](https://github.com/bradleyboehmke/completejourney) R package (CC0), pinned to a commit. 2,469 households, 2017, US dollars. It's a household purchase panel, not total store sales.
- **Email experiment:** [Kevin Hillstrom's MineThatData challenge](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html), a different retailer, analysed as a separate study.
- **Limits:** campaign effects are observational and rest on stated assumptions (comparable groups, parallel pre-trends). Margin, coupon funding and distribution costs in the ROI model are assumptions. Demographics cover only 801 households, who shop more than average.

This project was built with AI assistance; the [AI log](docs/ai_log.md) records what it did and what was checked.
