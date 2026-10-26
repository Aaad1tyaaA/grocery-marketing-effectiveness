# AI implementation log

## Phase 1 — 25 October 2026

Request: build the clean grocery data foundation and supply reviewable files using the local guide and repaired kit.

Produced: source profiling SQL, the core model, an explicit household/campaign bridge, anomaly queries, verification SQL, a fresh-database builder, DBeaver inspection queries, measured reports, and regression checks.

Decisions verified:
- The original database was locked by DBeaver. Built a separate self-contained phase-1 file from Parquet, verifying source counts and fingerprints before and after modelling.
- Did not copy the guide's independent maximum-code selection for promotion duplicates: source profiling showed 12,785 conflicting keys. Used MULTIPLE labels and preserved exposure flags/source row counts.
- Made non-grocery classification non-null even when product metadata fields are missing. A synthetic regression tests that case.
- Preserved UTC time and added explicit Eastern local time. A synthetic regression verifies a winter conversion.
- Added zero-MAD protection to anomaly scoring and kept anomaly flags separate from deletion rules.
- Did not repeat the guide's missing-date/store-closure claim as an observed fact.

Validation: 24 database checks; a synthetic model regression; six compact-reader regressions. Later statistical and business conclusions remain to be implemented and validated.


## Final evidence and presentation review - 26 October 2026

This is an AI-assisted project. The following are actual corrections or checks from this build, not fabricated business outcomes.

1. **Promotion duplicates:** 12,785 conflicting keys made independent maximum display/mailer codes unsafe. Preserved MULTIPLE labels and exposure flags instead.
2. **Metric scope:** separated $4.596M clean all-department sales from $4.185M grocery sales, and 2,469 source households from 2,467 grocery spenders.
3. **Missing products:** retained the 17 absent product IDs through the unknown-product dimension rather than dropping their sales.
4. **AOV grain:** validated sales / distinct basket count. The final app uses the annual ratio, not a simple average of weekly AOVs.
5. **Week boundaries:** preserved source weeks and Monday boundaries; excluded partial week 1 from comparable trends while retaining annual totals.
6. **Campaign selection:** did not repeat the raw targeted gap as causal lift; compared four designs and exposed intervals crossing zero.
7. **Coupon accounting:** kept manufacturer coupon amounts separate from retailer-funded discount cost. Additional coupon funding in the app defaults to zero; cost assumptions are labelled.
8. **Randomized outcomes:** used all assigned email customers including zeros. Shared control is counted once in the 64,000 total.
9. **Targeting instability:** reported the second split that weakened the apparent gain instead of selecting the favorable split as the conclusion.
10. **Presentation QA:** corrected clipped text and zero-million labels, replaced the review-date block with basket trends, removed a misleading mixed-grain redemption comparison, and kept grocery and email evidence separate. Native DAX results were checked against saved source aggregates; the latest native PBIX/PDF export remains pending after desktop control was disabled.

The original module log above is historical. Excel is a complete local artifact. Power BI has a verified earlier PBIX and saved improved source; the final source-to-PBIX/PDF export remains pending. See verification files for exact checks. Public CI omits raw-data-dependent tests and does not claim an independent full rebuild.

11. **Empty-text brands:** the final source share measure checks trimmed text length, since empty strings are not DAX BLANK values. A query-scoped measure was reconciled without changing the open desktop model. The final source must be reopened/refreshed before exporting the latest PBIX/PDF.
