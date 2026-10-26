# What's published

This repository contains the analysis code, SQL, notebooks with aggregate outputs, charts, small aggregate exports, the Excel ROI specification, the Power BI project source and its PDF export.

Raw source files (RDS/RDA/CSV/Parquet), DuckDB databases, household-level exports, source-row candidate lists, the Excel workbook with household lookup data, embedded-data PBIX files and private documents stay local. The analysis can be rebuilt with `python scripts/run_all.py` from checksum-pinned sources.

Before publication, run `python scripts/prepare_publication.py`. It removes notebook outputs containing household, basket or source-row identifiers while preserving aggregate outputs, execution counts and original input hashes. Tests check that the tracked notebooks remain sanitized. The public checkout does not contain enough inputs to revalidate every historical notebook or database result; raw-data-dependent CI checks explicitly skip.

The grocery data comes from the [`completejourney`](https://github.com/bradleyboehmke/completejourney) R package, released under CC0. The email experiment comes from Kevin Hillstrom's public MineThatData challenge. Source URLs and checksums are in `source_manifest.json` and `hillstrom_source.json`.
