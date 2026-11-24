# Customer, Product & Profitability Performance Analysis in Supply Chain Operations
# Streamlit dashboard for APL_Logistics.csv
# Run: pip install -r requirements.txt && streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Supply Chain Profitability Intelligence", page_icon="📦", layout="wide")

# ----------------------------- Configuration -----------------------------
DATA_FILE = Path(__file__).parent / "APL_Logistics.csv"

NUMERIC_COLS = [
    "Days for shipping (real)", "Days for shipment (scheduled)", "Benefit per order",
    "Sales per customer", "Late_delivery_risk", "Category Id", "Customer Id",
    "Department Id", "Latitude", "Longitude", "Order Customer Id",
    "Order Item Discount", "Order Item Discount Rate", "Order Item Product Price",
    "Order Item Profit Ratio", "Order Item Quantity", "Sales", "Order Item Total",
    "Order Profit Per Order", "Product Price", "Customer Zipcode"
]

@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding="cp1252")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding="latin1")
    else:
        if not DATA_FILE.exists():
            return None
        try:
            df = pd.read_csv(DATA_FILE, encoding="cp1252")
        except UnicodeDecodeError:
            df = pd.read_csv(DATA_FILE, encoding="latin1")

    df.columns = df.columns.str.strip()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["Customer Segment", "Category Name", "Product Name", "Market",
                "Order Region", "Order Country", "Shipping Mode", "Delivery Status",
                "Order Status", "Department Name", "Type"]:
        if col in df.columns:
            df[col] = df[col].astype("string").fillna("Unknown").str.strip()
    # A row represents an order item. Keep financial fields at row/item grain.
    df["Revenue"] = df["Sales"].fillna(df["Order Item Total"])
    df["Profit"] = df["Order Profit Per Order"].fillna(df["Benefit per order"])
    df["Discount"] = df["Order Item Discount"].fillna(0)
    df["Discount Rate"] = df["Order Item Discount Rate"].fillna(0)
    df["Quantity"] = df["Order Item Quantity"].fillna(0)
    df["Gross Item Value"] = df["Order Item Product Price"].fillna(df["Product Price"]) * df["Quantity"]
    df["Profit Margin"] = np.where(df["Revenue"].ne(0), df["Profit"] / df["Revenue"] * 100, np.nan)
    df["Customer ID"] = df["Customer Id"].fillna(df["Order Customer Id"]).astype("Int64")
    return df

def money(v):
    return f"${v:,.2f}"

def pct(v):
    return f"{v:,.2f}%"

# ----------------------------- Header -----------------------------
st.title("📦 Supply Chain Profitability Intelligence")
st.caption("Customer, Product, and Profitability Performance Analysis | Interactive commercial analytics")
st.markdown("""
This dashboard evaluates **revenue, profit, customer value, product/category margins, discount effects,
and market performance**. Use the sidebar filters to explore selected slices of the data.
""")

with st.sidebar:
    st.header("⚙️ Data & Filters")
    uploaded = st.file_uploader("Upload dataset (CSV)", type=["csv"], help="If not uploaded, app loads APL_Logistics.csv from the app folder.")
    st.caption("Dataset: APL Logistics / DataCo-style supply chain records")

df = load_data(uploaded)
if df is None:
    st.error("APL_Logistics.csv was not found. Place it in the same folder as app.py or upload it in the sidebar.")
    st.stop()

required = ["Revenue", "Profit", "Customer Segment", "Category Name", "Product Name", "Market", "Order Region"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Required columns are missing: {missing}")
    st.stop()

# Data validation summary
with st.expander("🔎 Data quality & financial validation", expanded=False):
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Rows loaded", f"{len(df):,}")
    q2.metric("Missing revenue", f"{df['Revenue'].isna().sum():,}")
    q3.metric("Missing profit", f"{df['Profit'].isna().sum():,}")
    q4.metric("Duplicate rows", f"{df.duplicated().sum():,}")
    st.info("Financial figures are aggregated at the available row/item level. The source has no explicit Order ID column; "
            "avoid treating repeated order-level fields as unique order records. This dashboard uses the row-level Profit field "
            "(Order Profit Per Order, falling back to Benefit per order).")
    st.write("Revenue source: Sales (fallback: Order Item Total). Profit source: Order Profit Per Order (fallback: Benefit per order).")
    st.write("Records with missing Revenue or Profit are excluded from financial totals; zero/negative values are retained for transparency.")

# ----------------------------- Sidebar filters -----------------------------
def options(col):
    return sorted(df[col].dropna().astype(str).unique().tolist()) if col in df.columns else []

with st.sidebar:
    segments = options("Customer Segment")
    selected_segments = st.multiselect("Customer segment", segments, default=segments)
    categories = options("Category Name")
    selected_categories = st.multiselect("Category", categories, default=categories)
    markets = options("Market")
    selected_markets = st.multiselect("Market", markets, default=markets)
    regions = options("Order Region")
    selected_regions = st.multiselect("Order region", regions, default=regions)
    products = options("Product Name")
    selected_products = st.multiselect("Products (optional)", products, default=[])
    max_discount = float(df["Discount Rate"].fillna(0).max()) if len(df) else 0.0
    discount_range = st.slider("Discount rate range", 0.0, max(1.0, max_discount), (0.0, max(1.0, max_discount)), step=0.01,
                              help="Uses the dataset's Order Item Discount Rate values. Values may be stored as decimals (e.g., 0.10 = 10%).")

filtered = df.copy()
if selected_segments: filtered = filtered[filtered["Customer Segment"].astype(str).isin(selected_segments)]
if selected_categories: filtered = filtered[filtered["Category Name"].astype(str).isin(selected_categories)]
if selected_markets: filtered = filtered[filtered["Market"].astype(str).isin(selected_markets)]
if selected_regions: filtered = filtered[filtered["Order Region"].astype(str).isin(selected_regions)]
if selected_products: filtered = filtered[filtered["Product Name"].astype(str).isin(selected_products)]
filtered = filtered[filtered["Discount Rate"].fillna(0).between(discount_range[0], discount_range[1])]

fin = filtered.dropna(subset=["Revenue", "Profit"]).copy()
total_revenue = fin["Revenue"].sum()
total_profit = fin["Profit"].sum()
overall_margin = (total_profit / total_revenue * 100) if total_revenue else 0
total_discount = filtered["Discount"].sum()
discount_pct = (total_discount / (filtered["Gross Item Value"].sum() or 1) * 100)
customers_count = filtered["Customer ID"].nunique() if "Customer ID" in filtered else 0
avg_profit = fin["Profit"].mean() if len(fin) else 0

# ----------------------------- KPI strip -----------------------------
st.subheader("Revenue & Profit Overview")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Revenue", money(total_revenue))
k2.metric("Profit", money(total_profit), delta=pct(overall_margin) + " margin")
k3.metric("Profit margin", pct(overall_margin))
k4.metric("Customers", f"{customers_count:,}")
k5.metric("Discount total", money(total_discount))
k6.metric("Avg. row profit", money(avg_profit))

# Overview charts
left, right = st.columns(2)
with left:
    st.markdown("#### Revenue vs Profit by Market")
    market_perf = fin.groupby("Market", dropna=False)[["Revenue", "Profit"]].sum().reset_index().sort_values("Revenue", ascending=False)
    if not market_perf.empty:
        long_market = market_perf.melt(id_vars="Market", value_vars=["Revenue", "Profit"], var_name="Metric", value_name="Amount")
        fig = px.bar(long_market, x="Market", y="Amount", color="Metric", barmode="group", title=None)
        fig.update_layout(xaxis_title="", yaxis_title="Amount", legend_title="")
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("#### Profit Margin by Customer Segment")
    seg = fin.groupby("Customer Segment").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
    seg["Margin %"] = np.where(seg["Revenue"] != 0, seg["Profit"]/seg["Revenue"]*100, 0)
    fig = px.bar(seg.sort_values("Margin %"), x="Customer Segment", y="Margin %", color="Margin %", title=None)
    fig.update_layout(xaxis_title="", yaxis_title="Profit margin (%)", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------- Customer Value -----------------------------
st.divider()
st.header("👥 Customer Value Dashboard")
cust_col = "Customer ID"
if cust_col in fin.columns:
    customer = fin.groupby(cust_col).agg(
        Revenue=("Revenue","sum"), Profit=("Profit","sum"), Items=("Profit","size"),
        Segment=("Customer Segment","first"), Country=("Customer Country","first")
    ).reset_index()
    customer["Margin %"] = np.where(customer["Revenue"] != 0, customer["Profit"]/customer["Revenue"]*100, 0)
    customer["Customer Value Index %"] = np.where(total_profit != 0, customer["Profit"]/total_profit*100, 0)
    a,b = st.columns(2)
    with a:
        st.markdown("#### Top 10 customers by profit")
        top = customer.nlargest(10, "Profit").sort_values("Profit")
        fig = px.bar(top, x="Profit", y=cust_col, orientation="h", color="Margin %", hover_data=["Revenue","Margin %","Segment"])
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.markdown("#### Bottom 10 customers by profit")
        bottom = customer.nsmallest(10, "Profit").sort_values("Profit")
        fig = px.bar(bottom, x="Profit", y=cust_col, orientation="h", color="Margin %", hover_data=["Revenue","Margin %","Segment"])
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Customer segment contribution")
    segment_contrib = customer.groupby("Segment").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
    segment_contrib["Profit contribution %"] = np.where(total_profit != 0, segment_contrib["Profit"]/total_profit*100, 0)
    fig = px.bar(segment_contrib, x="Segment", y="Profit", color="Profit contribution %", hover_data=["Revenue","Profit contribution %"])
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Customer profitability table"):
        st.dataframe(customer.sort_values("Profit", ascending=False), use_container_width=True, hide_index=True)
else:
    st.warning("Customer ID column is unavailable.")

# ----------------------------- Product & Category -----------------------------
st.divider()
st.header("📊 Product & Category Performance")
p1,p2 = st.columns(2)
with p1:
    st.markdown("#### Product-level margin analysis")
    product_perf = fin.groupby("Product Name").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum"), Quantity=("Quantity","sum")).reset_index()
    product_perf["Margin %"] = np.where(product_perf["Revenue"] != 0, product_perf["Profit"]/product_perf["Revenue"]*100, 0)
    product_perf = product_perf.sort_values("Profit", ascending=False)
    fig = px.bar(product_perf.head(15).sort_values("Profit"), x="Profit", y="Product Name", orientation="h", color="Margin %", hover_data=["Revenue","Quantity","Margin %"])
    st.plotly_chart(fig, use_container_width=True)
with p2:
    st.markdown("#### Category profitability heatmap")
    category_perf = fin.groupby("Category Name").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
    category_perf["Margin %"] = np.where(category_perf["Revenue"] != 0, category_perf["Profit"]/category_perf["Revenue"]*100, 0)
    heat = category_perf.set_index("Category Name")[["Margin %"]]
    fig = px.imshow(heat, text_auto=".2f", aspect="auto", color_continuous_scale="RdYlGn", labels=dict(color="Margin %"))
    st.plotly_chart(fig, use_container_width=True)
st.markdown("#### Category detail")
st.dataframe(category_perf.sort_values("Profit", ascending=False), use_container_width=True, hide_index=True)

# ----------------------------- Discount analyzer -----------------------------
st.divider()
st.header("🏷️ Discount Impact Analyzer")
d1,d2 = st.columns(2)
with d1:
    st.markdown("#### Discount rate vs profit margin")
    discount_plot = fin.copy()
    discount_plot["Discount Rate (%)"] = discount_plot["Discount Rate"] * 100
    # Bin rates for a readable summary
    discount_plot["Discount Band"] = pd.cut(discount_plot["Discount Rate (%)"], bins=10, duplicates="drop")
    discount_band = discount_plot.groupby("Discount Band", observed=False).agg(
        Revenue=("Revenue","sum"), Profit=("Profit","sum"), Discount=("Discount","sum")
    ).reset_index()
    discount_band["Margin %"] = np.where(discount_band["Revenue"] != 0, discount_band["Profit"]/discount_band["Revenue"]*100, 0)
    discount_band["Discount Band"] = discount_band["Discount Band"].astype(str)
    fig = px.scatter(discount_plot, x="Discount Rate (%)", y="Profit Margin", color="Category Name",
                      opacity=0.45, hover_data=["Revenue","Profit","Discount"])
    fig.update_layout(yaxis_title="Row profit margin (%)")
    st.plotly_chart(fig, use_container_width=True)
with d2:
    st.markdown("#### Margin by discount band")
    fig = px.bar(discount_band, x="Discount Band", y="Margin %", color="Margin %", title=None)
    fig.update_layout(xaxis_title="Discount rate band", yaxis_title="Aggregated margin (%)", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("#### What-if discount scenario (illustrative)")
st.caption("This is a simplified scenario estimate: assumes revenue changes with the discount while current row profit is held as the baseline before discount adjustment. It is not a causal estimate.")
scenario_rate = st.slider("Scenario discount rate (%)", 0.0, 50.0, 5.0, 0.5)
baseline_gross = fin["Gross Item Value"].sum()
baseline_discount_rate = (fin["Discount"].sum()/baseline_gross*100) if baseline_gross else 0
scenario_discount_amount = baseline_gross * scenario_rate / 100
current_discount_amount = fin["Discount"].sum()
# Approximate profit delta from the difference in discount amount (other costs/prices held constant)
scenario_profit = total_profit + (current_discount_amount - scenario_discount_amount)
scenario_revenue = baseline_gross - scenario_discount_amount
scenario_margin = scenario_profit/scenario_revenue*100 if scenario_revenue else 0
s1,s2,s3,s4 = st.columns(4)
s1.metric("Current discount rate (weighted)", pct(baseline_discount_rate))
s2.metric("Scenario discount amount", money(scenario_discount_amount))
s3.metric("Scenario profit (estimate)", money(scenario_profit), delta=money(scenario_profit-total_profit))
s4.metric("Scenario margin (estimate)", pct(scenario_margin))

# ----------------------------- Market/region detail and operations -----------------------------
st.divider()
st.header("🌎 Market & Regional Profit Analysis")
m1,m2 = st.columns(2)
with m1:
    market_table = fin.groupby("Market").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
    market_table["Margin %"] = np.where(market_table["Revenue"] != 0, market_table["Profit"]/market_table["Revenue"]*100, 0)
    fig = px.treemap(market_table, path=["Market"], values="Revenue", color="Margin %", hover_data=["Profit","Margin %"])
    st.plotly_chart(fig, use_container_width=True)
with m2:
    region_table = fin.groupby("Order Region").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
    region_table["Margin %"] = np.where(region_table["Revenue"] != 0, region_table["Profit"]/region_table["Revenue"]*100, 0)
    fig = px.bar(region_table.sort_values("Profit"), x="Order Region", y="Profit", color="Margin %", hover_data=["Revenue","Margin %"])
    st.plotly_chart(fig, use_container_width=True)

st.markdown("#### Country profitability")
country_table = fin.groupby("Order Country").agg(Revenue=("Revenue","sum"), Profit=("Profit","sum")).reset_index()
country_table["Margin %"] = np.where(country_table["Revenue"] != 0, country_table["Profit"]/country_table["Revenue"]*100, 0)
st.dataframe(country_table.sort_values("Profit", ascending=False), use_container_width=True, hide_index=True)

# ----------------------------- Shipping context -----------------------------
st.divider()
st.header("🚚 Operational context (supporting analysis)")
o1,o2 = st.columns(2)
with o1:
    if "Shipping Mode" in filtered.columns:
        ship = (
            filtered.groupby("Shipping Mode")
            .agg(
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum"),
                Actual_Days=("Days for shipping (real)", "mean"),
                Scheduled_Days=("Days for shipment (scheduled)", "mean"),
            )
            .reset_index()
        )
        ship = ship.rename(columns={
            "Actual_Days": "Actual Days",
            "Scheduled_Days": "Scheduled Days",
        })
        fig = px.bar(
            ship,
            x="Shipping Mode",
            y="Profit",
            color="Shipping Mode",
            hover_data=["Revenue", "Actual Days", "Scheduled Days"],
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------------------------- Downloads -----------------------------
st.divider()
st.header("⬇️ Export filtered analysis")
csv_bytes = fin.to_csv(index=False).encode("utf-8-sig")
st.download_button("Download filtered row-level data (CSV)", data=csv_bytes, file_name="apl_filtered_analysis.csv", mime="text/csv")
customer_csv = customer.to_csv(index=False).encode("utf-8-sig") if "Customer ID" in fin.columns else b""
if customer_csv:
    st.download_button("Download customer profitability (CSV)", data=customer_csv, file_name="customer_profitability.csv", mime="text/csv")
st.caption("Built with Streamlit + Pandas + Plotly. Interpret profitability with row-level data definitions and validate business accounting assumptions.")
