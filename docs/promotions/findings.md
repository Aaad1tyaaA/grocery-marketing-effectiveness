# Promotion associations

Completed **Steps 1.4.1–1.4.4**. Units are purchases by the panel households, not total store sales. These indices compare observed units with a pair-specific baseline; they are not randomized treatment effects.

## Three findings

1. Display plus mailer pair-weeks have **3.14×** baseline panel units, versus **2.31×** for mailer only and **1.59×** for display only. This ranks observed promotion packages, not the isolated causal effect of a display or mailer. An index of 3.14 means 214% above baseline, not a 314% increase.
2. The week after a single-week promotion has **1.11×** baseline units; after multiple consecutive promoted weeks, **1.19×**. The guide-style comparison does not show a dip below baseline. It cannot determine whether discounts continued, demand was seasonal, or purchases were pulled forward.
3. Metadata is absent for **953,843 of 1,184,352 pair-weeks**. All explicitly listed eligible records indicate a display or mailer, so an observed-metadata-only baseline is **not estimable**: it has no explicitly observed nonpromotion controls. The primary result follows the guide's convention that an absent row means no recorded display/mailer; that convention cannot be independently validated from explicit nonpromotion records in this source.

## Primary results

| Condition | Pair-weeks with usable baseline | Unit index |
|---|---:|---:|
| Display + mailer | 39,165 | 3.14× |
| Mailer only | 108,992 | 2.31× |
| Display only | 55,369 | 1.59× |
| Week after a promotion | 115,419 | 1.13× |
| No promotion | 834,571 | 1.00× |

## Universe and coverage

- **22,776 product/store pairs** purchased in at least eight source weeks; 52 weeks per pair gives **1,184,352 panel rows**.
- **22,183 pairs** have at least four baseline weeks (not promoted and not directly after a promotion).
- **19.5%** of the full eligible panel has recorded promotion flags.
- **587 eligible pair-weeks** contain conflicting placement codes. Flags use any nonzero code; labels use MULTIPLE instead of selecting an arbitrary maximum. Placement-specific values may therefore differ from the guide's maximum-code method.
- **534 pairs** have zero average baseline units. The primary result uses a ratio-of-totals definition; the positive-baseline-only export shows a sensitivity excluding these pairs.
- Missing purchase rows are zero-filled within this panel, meaning no observed panel purchase. This does not prove no store sales or product availability.

## Observed-metadata sensitivity

| Condition | Primary definition | Observed-current-and-prior metadata only |
|---|---:|---:|
| Display + mailer | 3.14× | Not estimable |
| Mailer only | 2.31× | Not estimable |
| Display only | 1.59× | Not estimable |
| Week after a promotion | 1.13× | Not estimable |
| No promotion | 1.00× | Not estimable |

The stricter sample has 0 usable baseline pairs. Its CSV intentionally contains headers and no estimates. This is a support limitation, not a zero effect or a failed query. It excludes boundary week 2 and missing-metadata transitions. Primary lag indicators default to no previous promotion at the left boundary as in the guide; boundary-history counts are exported for the post-promotion comparison.

The positive-baseline sensitivity remains estimable: excluding 534 zero-baseline pairs changes the Display + mailer index to 2.91×, Mailer only to 2.24×, and Display only to 1.42×. These are alternate descriptive estimates, not corrected causal effects. The complete base amounts and counts are exported.

Placement-code definitions follow the [official completejourney documentation](https://github.com/bradleyboehmke/completejourney/blob/master/man/promotions_sample.Rd). The event-style support limitation above is an observation from this full dataset, not a claim that the documentation independently proves missing-record coverage.

## Interpretation and verification

Price discounts can accompany display and mailer exposure. Seasonality, selection of products into promotion, availability, and other confounders remain uncontrolled. Small placement groups (<100 pair-weeks) are flagged and omitted from the placement chart; the full CSV retains them. This threshold is a descriptive display rule, not a statistical significance test. No confidence intervals or profit/ROI claims are made.

**18 full-data checks passed**, covering panel grain, zero filling, baseline support, condition totals, coverage, and ratios. Source fingerprints were verified before analysis. The raw data, user SQL scripts, and open databases were not modified.

Files: `exports/promotions/`, `sql/04_promo.sql`, `04_promotions.ipynb`, three PNG charts, and `grocery_promotions.duckdb` (summary/check tables only).
