from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Grocery Marketing Effectiveness", layout="wide")
D = Path(__file__).parent / "data"
load = lambda name: pd.read_csv(D / f"{name}.csv")

st.title("Does direct marketing actually grow customers?")
st.caption("2017 Complete Journey purchasing panel. Annual grocery KPIs include partial week 1; weekly trends use weeks 2-53. All monetary values are source USD. The Hillstrom email experiment is a separate retailer.")

required=['annual_kpis','weekly_kpis','category_discount','segments','trajectories','cohort_retention','promo_lift','campaign_estimates']
if any(not (D/f'{name}.csv').exists() for name in required):
    st.info("The completed-module preview needs its summary files. Run scripts/export_app_data.py in the project folder, then reload.")
    st.stop()

k = load("weekly_kpis")
a = load('annual_kpis').iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annual grocery sales", f"${a.sales / 1e6:.2f}M")
c2.metric("Active grocery households", f"{a.households:,.0f}")
c3.metric("Average basket value", f"${a.sales/a.baskets:.2f}")
c4.metric("Retailer discount depth", f"{a.retailer_discounts/a.shelf_value:.1%}")

t1, t2, t3, t4, t5 = st.tabs(["Business health", "Customers", "Promotions", "Campaigns", "ROI calculator"])

with t1:
    st.line_chart(k.set_index("week_start")[["sales"]])
    st.line_chart(k.set_index("week_start")[["discount_depth"]])
    st.subheader('Weekly shopping trips')
    st.line_chart(k.set_index('week_start')[['baskets']])
    st.dataframe(load("category_discount").head(15), hide_index=True)

with t2:
    a, b = st.columns(2)
    a.subheader("Share of spend by segment")
    a.bar_chart(load("segments").set_index("segment")["value_share"])
    b.subheader("Households by spend trajectory")
    b.bar_chart(load("trajectories").set_index("trajectory")["households"])
    st.subheader("Monthly cohort retention")
    r = load("cohort_retention").pivot(index="cohort", columns="months_since_first", values="retention")
    st.dataframe(r.style.background_gradient(cmap="Blues", vmin=0, vmax=1).format("{:.0%}", na_rep=""))

with t3:
    st.subheader("Units sold vs each product-store's own baseline")
    st.bar_chart(load("promo_lift").set_index("condition")["lift_index"])
    st.caption("Descriptive associations, not causal lift. Missing promotion records are treated as no recorded display/mailer; prices and seasonality are uncontrolled.")

with t4:
    st.subheader("Campaign lift: four estimates, from naive to defensible ($ per household per week)")
    st.dataframe(load("campaign_estimates"), hide_index=True)
    st.info("The estimates are observational; inspect placebo checks and confidence intervals before drawing causal conclusions.")
    st.subheader("Randomized benchmark: Hillstrom email test")
    if (D/'hillstrom_readout.csv').exists():
        st.dataframe(load("hillstrom_readout"), hide_index=True)
        st.caption("Separate retailer experiment: two-week outcomes per assigned customer. Cell targeting is provisional because the second split did not confirm its strong gain. This lift must not be used as grocery campaign ROI.")
        if (D/'email_head_to_head.csv').exists():
            st.subheader("Men's version minus Women's version")
            st.dataframe(load('email_head_to_head'), hide_index=True)
    else:
        st.info("The Module 6 randomized experiment has not been built yet.")

with t5:
    st.subheader("At what lift does a campaign pay for itself?")
    st.info("Illustrative scenario only. Campaign lift is uncertain; margin, funding share and distribution costs are assumptions. The global coupon-line average is a proxy, not observed cost per campaign redemption.")
    a, b = st.columns(2)
    hh = a.number_input("Households targeted", 100, 100_000, 1133, 100)
    weeks = a.number_input("Campaign length (weeks)", 1, 52, 8)
    lift = a.slider("Incremental spend per household per week ($)", -2.0, 10.0, 2.95, 0.05)
    margin = a.slider("Gross margin (assumption)", 0.10, 0.50, 0.30, 0.01)
    redemptions = b.number_input("Coupon redemptions", 0, 100_000, 653, 10)
    coupon = b.number_input("Coupon cost per redemption ($, assumed proxy)", 0.0, 20.0, 1.05, 0.05)
    retailer_share = b.slider("Additional retailer coupon funding share (assumption)", 0.0, 1.0, 0.0, 0.05)
    dist = b.number_input("Print and distribution cost per household ($, assumption)", 0.0, 20.0, 0.75, 0.05)
    profit = hh * weeks * lift * margin
    cost = redemptions * coupon * retailer_share + hh * dist
    m1, m2, m3 = st.columns(3)
    m1.metric("Incremental gross profit", f"${profit:,.0f}")
    m2.metric("Net profit", f"${profit - cost:,.0f}")
    m3.metric("Break-even lift", f"${cost / (hh * weeks * margin):.2f} per household per week")
    st.caption("Illustrative inputs, not established causal lift. Replace defaults with verified estimates from your own analysis.")
