# Power BI dashboard

Four pages: **Business health**, **Customers & marketing**, **Products & discounts** and **Campaigns & email**. A static export is in [`dashboard/Grocery Marketing Final.pdf`](../dashboard/Grocery%20Marketing%20Final.pdf); the editable project is `dashboard/final/Grocery Marketing Final.pbip`.

## Refresh it yourself

1. Rebuild the analysis: `python scripts/run_all.py`.
2. Export the report tables: `python scripts/export_dashboard_data.py`. This writes `dashboard/data/`.
3. Open `dashboard/final/Grocery Marketing Final.pbip` in Power BI Desktop.
4. Set the **DataFolder** Power Query parameter to the full path of your `dashboard/data` folder (the project ships with the placeholder `C:\GroceryMarketing\dashboard\data`), then **Refresh**.
5. In Desktop edit mode, **Ctrl+click** the buttons at the top to move between pages.

## Controls it should match

Annual grocery sales **$4,185,055.64**, **141,063 baskets**, **2,467 active households**, average basket value **$29.67**, retailer discount depth **15.8%**. Annual totals include the partial week 1; weekly trends exclude it. Measure checks are recorded in [`dashboard/verification_final.json`](../dashboard/verification_final.json).

## Reading it correctly

- The department slicer filters sales visuals only, not the campaign estimates or the email experiment.
- Campaign estimates are observational; all three preferred intervals include zero.
- Coupon redemption shows engagement, not proven lift.
- The email experiment is a different retailer and isn't an input to grocery ROI.

Design choices for each visual are explained in [dashboard_design_review.md](dashboard_design_review.md).
