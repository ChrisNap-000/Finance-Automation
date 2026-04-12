import streamlit as st

from auth import check_password
from data.loader import load_transactions, load_lookup, merge_data
from data.transforms import clean_data, apply_transformations
from ui.filters import render_filters
from ui.kpis import render_kpis
from ui.charts import render_monthly_cashflow
from ui.tables import render_pnl_breakdown, render_transactions_table, render_pnl_download

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

# ---------------------------
# AUTH
# ---------------------------
if not check_password():
    st.stop()

# ---------------------------
# FILE UPLOAD
# ---------------------------
st.sidebar.header("Upload Data Files")
transactions_file = st.sidebar.file_uploader("Upload Transactions CSV", type=["csv"])
lookup_file = st.sidebar.file_uploader("Upload Account Lookup XLSX", type=["xlsx"])

if not transactions_file or not lookup_file:
    st.info("Please upload both CSV files to continue.")
    st.stop()

# ---------------------------
# LOAD & TRANSFORM DATA
# ---------------------------
df_main = load_transactions(transactions_file)
df_lookup = load_lookup(lookup_file)
df_merged = merge_data(df_main, df_lookup)
df_clean = clean_data(df_merged)
df = apply_transformations(df_clean)

# ---------------------------
# SIDEBAR FILTERS
# ---------------------------
st.sidebar.header("Filters")
year_select, month_select, txn_types = render_filters(df)

filtered_df = df[
    (df["Year"].isin(year_select)) &
    (df["Month"].isin(month_select)) &
    (df["Transaction Type"].isin(txn_types))
]

# ---------------------------
# RENDER UI
# ---------------------------
render_kpis(df, filtered_df)
render_monthly_cashflow(filtered_df)
pivoted_df = render_pnl_breakdown(filtered_df)
render_transactions_table(filtered_df)
render_pnl_download(pivoted_df)
