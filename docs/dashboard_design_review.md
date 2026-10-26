# Dashboard decision and design review

Reviewed 26 October 2026 against [Microsoft dashboard design guidance](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips), [visual selection guidance](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-types-for-reports-and-q-and-a), and [report accessibility guidance](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports).

| Change | Business purpose |
|---|---|
| Removed the flagged-review-dates text block | Detailed review dates are not a primary executive decision view. Anomaly audit outputs remain in the analysis. |
| Added weekly shopping trips | Read alongside sales to distinguish changes in basket volume from spend per basket; partial week 1 is excluded. |
| Replaced donut with known-brand share bars | Compare National and Private brand shares on a common baseline. Missing-brand sales are excluded from this share denominator and retained in annual totals. |
| Replaced filled shelf/sales area with two lines | Avoid suggesting that shelf value and paid sales should be added. |
| Replaced mixed audience/redemption counts with household redemption rate | Compare unique redeeming households / campaign audience, rather than different event grains. Engagement does not establish incrementality. |
| Replaced 12 small campaign columns with a four-design matrix | Make adjustment differences and negative estimates readable. The separate earlier-match interval table preserves uncertainty. |
| Added a zero-excluding-interval count | Shows that none of the three preferred observational intervals excludes zero. It is not a test of equivalence or proof of no effect. |
| Removed redundant bar numeric axes | Direct bold values and category labels preserve meaning while leaving room for all visible categories. |

Four pages retain a consistent font hierarchy, contrasting navy headers, restrained chart accents, zero-based bar scales and ordered categories. The six-month activity matrix is labelled as observed activity, not acquisition retention. The separate retailer experiment is labelled throughout. Native page navigators use Ctrl+click in Desktop edit mode. Essential results are visible without relying solely on hover; tooltips add context.

Accessibility review covers text contrast, alt descriptions and logical navigation order. A dedicated screen-reader/high-contrast assistive-technology audit and every device size have not been independently tested. Full category names can still require hover or the accessible data table in narrow panels.
