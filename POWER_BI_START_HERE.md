# Power BI dashboard

The latest editable report is **dashboard/final/Grocery Marketing Final.pbip**. It has four pages: Business health, Customers & marketing, Products & discounts, and Campaigns & email. Source and captured native DAX checks are in [verification_source_final.json](dashboard/verification_source_final.json).

The review-date text block has been replaced by weekly shopping trips. Known-brand shares use bars; shelf versus paid sales use two lines; campaign designs use a compact four-row matrix; coupon engagement uses unique redeeming households divided by campaign audience. Read the [design review](docs/dashboard_design_review.md) for the purpose of each change.

**Save status:** the latest source and measures are saved. A new Final PBIX and native four-page PDF have not been exported. Desktop control was disabled at the user's request. In the original local handoff, `dashboard/Grocery Marketing Polished.pbix` is the earlier, separately verified embedded-data report; it still contains the previous review-date block. Neither PBIX nor cached data is uploaded to GitHub.

To finish the native handoff manually, open the Final PBIP, then use **File > Save as** to save a separate `Grocery Marketing Final.pbix`. Use **File > Export > PDF** for its four-page PDF. In Desktop edit mode, **Ctrl+click** the top page buttons; the bottom page tabs also work.

## Refresh

Rebuild the analysis and run `python scripts/export_dashboard_data.py`. Set the **DataFolder** Power Query parameter to the absolute generated `dashboard/data` folder before refreshing. The public model uses the placeholder `C:\GroceryMarketing\dashboard\data`. Public source does not contain a data cache; it needs a successful refresh before charts populate. The original local source cache supports immediate viewing on this computer.

## Scope

Annual grocery controls: **$4,185,055.64**, **141,063 baskets**, **2,467 active households**, **$29.67 average basket value**, **15.8% retailer discount depth**. Annual totals include partial source week 1; comparable weekly trends exclude it. The household dimension has 2,469 source households, including two without grocery purchases. All currency is source USD.

Department selection filters sales-related visuals, not independent campaign estimates or the separate email experiment. Campaign estimates remain observational and all three preferred intervals include zero. Coupon redemption is engagement, not proven lift. The email experiment concerns another retailer and is not a grocery ROI input.
