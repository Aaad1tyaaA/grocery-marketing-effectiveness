# Power BI dashboard

The latest editable report is **dashboard/final/Grocery Marketing Final.pbip**. It has four pages: Business health, Customers & marketing, Products & discounts, and Campaigns & email. Final native DAX, container and PDF checks are in [verification_final.json](dashboard/verification_final.json). The earlier source-only check is retained as historical evidence.

The review-date text block has been replaced by weekly shopping trips. Known-brand shares use bars; shelf versus paid sales use two lines; campaign designs use a compact four-row matrix; coupon engagement uses unique redeeming households divided by campaign audience. Read the [design review](docs/dashboard_design_review.md) for the purpose of each change.

**Save status: complete.** The original local handoff contains **dashboard/Grocery Marketing Final.pbix**, with embedded data, and the [native four-page PDF](dashboard/Grocery%20Marketing%20Final.pdf). The final PBIX passed 660 arithmetic, data-scope, navigation, container and presentation checks. All four PDF pages were reviewed; clipped email-table text, crowded explanatory notes and the campaign selector were corrected and re-exported. The preserved Polished PBIX is an earlier edition. Embedded-data PBIX files and model caches remain local.

In Desktop edit mode, **Ctrl+click** the top page buttons; the bottom page tabs also work. The PDF is a static snapshot: use the PBIX for filters, tooltips and navigation.

## Refresh

Rebuild the analysis and run `python scripts/export_dashboard_data.py`. Set the **DataFolder** Power Query parameter to the absolute generated `dashboard/data` folder before refreshing. The public model uses the placeholder `C:\GroceryMarketing\dashboard\data`. Public source does not contain a data cache; it needs a successful refresh before charts populate. The original local source cache supports immediate viewing on this computer.

## Scope

Annual grocery controls: **$4,185,055.64**, **141,063 baskets**, **2,467 active households**, **$29.67 average basket value**, **15.8% retailer discount depth**. Annual totals include partial source week 1; comparable weekly trends exclude it. The household dimension has 2,469 source households, including two without grocery purchases. All currency is source USD.

Department selection filters sales-related visuals, not independent campaign estimates or the separate email experiment. Campaign estimates remain observational and all three preferred intervals include zero. Coupon redemption is engagement, not proven lift. The email experiment concerns another retailer and is not a grocery ROI input.
