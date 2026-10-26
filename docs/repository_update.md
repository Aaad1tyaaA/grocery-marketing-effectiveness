# Repository fixes and verification

The supplied `repo-fixes.bundle` was based on dashboard publication commit `67e093230490fbfe8a03a34fb263a704f4a97a63` and ended at `0df8873a1e3c0708fd21d0cc5e0e003663728d06`. Its changes were applied and reviewed before publication. The published update consolidates the reviewed final state so notebook row samples from the bundle are not introduced into public commit history.

## Changes applied

- Rewrote the README around the CRM decision and simplified the analysis explanations.
- Added `requirements.txt` as the entry point for the existing pinned analysis and test requirements, and updated CI to use it.
- Added the documentation map and Power BI refresh instructions.
- Retained the regenerated aggregate exports and aggregate notebook outputs. Removed obsolete local launcher references and automatic module ZIP packaging.
- Preserved the AI log when regenerating phase-one documentation.

## Repairs made during review

- Replaced the missing Excel download link with the workbook specification. The workbook contains household lookup data and remains a local deliverable.
- Removed notebook outputs containing household, basket or source-row identifiers while retaining aggregate outputs, execution counts and original input hashes. `scripts/prepare_publication.py` makes this repeatable.
- Removed a documentation-map reference to the deleted publication manifest.
- Clarified that the $34.77 Campaign 18 gap is from the staged common-support comparison, and that the Eastern reporting convention does not independently establish every store's physical time zone.
- Added regression checks for notebook sanitization, preservation of execution provenance and handoff links.

## Verification performed

The revised public checkout passed **30 tests**, with **13 expected raw-data-dependent skips** and no failures. All nine changed CSV exports were compared with the prior published version: headers, row counts and nonnumeric values agree, and changed numbers agree within floating-point tolerance (`rtol=1e-10`, `atol=1e-8`). Core findings and business recommendations did not change.

The dashboard PDF is unchanged, with SHA-256 `1e073aa364a53de4b1f2621b41ef988873750ae5f4b7272926acf728d8cc08e8`. This update did not repeat the complete source download and raw-data rebuild or re-export the native Excel and Power BI files. Earlier full-data and native-artifact verification records remain historical evidence rather than newly executed checks.
