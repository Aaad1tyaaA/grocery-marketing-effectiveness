# Customer value and retention

Completed Steps **1.3.1–1.3.5**. These segments describe observed behaviour; they are not validated predictions of future value or proof of marketing effects.

## Three findings

1. **416 Champions generate 44.7% of grocery spend.** The top 20% by spend (rounded up to 494 households) account for **53.6%**. This identifies a concentrated customer base for service and retention investigation; it does not establish future lifetime value.
2. **755 households have declining spend**, using a 20% decline threshold. Their spend moves from **$699,334.10** in H1 to **$379,860.61** in H2, an observed reduction of **$319,473.49**. This is not a forecast of revenue that a retention campaign can recover.
3. Households with demographics have median annual grocery spend of **$2,407.66**, versus **$682.53** without demographics. Income comparisons therefore describe a selective subset and should not be generalized to all households or treated as causal effects.

## Value segments

| Segment | Households | Annual grocery spend | Spend share |
|---|---:|---:|---:|
| Champions | 416 | $1,870,445.11 | 44.7% |
| Loyal regulars | 804 | $1,683,639.31 | 40.2% |
| Light regulars | 800 | $504,643.04 | 12.1% |
| Occasional | 225 | $48,106.18 | 1.1% |
| Lapsed | 222 | $78,222.00 | 1.9% |

## Spend trajectories

| Trajectory | Households | Household share | H1 spend | H2 spend |
|---|---:|---:|---:|---:|
| Growing | 866 | 35.1% | $476,545.46 | $818,773.30 |
| Declining | 755 | 30.6% | $699,334.10 | $379,860.61 |
| Stable | 709 | 28.7% | $892,462.14 | $882,928.88 |
| New in H2 | 78 | 3.2% | $0.00 | $18,835.28 |
| Gone in H2 | 59 | 2.4% | $6,209.02 | $0.00 |

H1 uses source weeks 2–27; H2 uses weeks 28–53. Partial week 1 is excluded from that comparison but retained in annual spend. Growing means at least +20%; Declining means at least -20%; New/Gone labels mean no recorded positive spend in the other half, not proven acquisition/churn. No-spend-in-both-halves cases have an explicit label instead of being misclassified as new.

## Retention and demographics

The cohort model uses the **all-clean-purchase** scope: 2,469 households, including two non-grocery-only households. Segments use **grocery purchases**: 2,467 households. Do not mix those denominators.

January is the first observed month for **1,983 households**. This panel starts in January; first observation does not prove those shoppers were newly acquired. Elapsed months without purchases are zero retention; future months are omitted/masked, never zero-filled. Monthly activity is nonconsecutive retention, so a household may return after a missed month.

Income-band comparisons include household counts and a small-group flag (<30). The flag is a descriptive caution, not a formal significance threshold. Missing attributes are not imputed. The deal-driven flag uses a rounded discount-share upper quartile; ties mean it need not identify exactly 25% of households.

## Verification and files

**18 full-data checks passed**, plus source fingerprint/model checks. The main outputs are `exports/customers/`, four chart PNGs, `03_customers.ipynb`, and `sql/03_customers.sql`. Exported retention rates retain full precision; the guide rounds them to three decimals. Segment/trajectory counts are computed from the actual data rather than forced to match the guide.

The reporting database `grocery_customers.duckdb` contains customer tables and checks, not raw purchases.
