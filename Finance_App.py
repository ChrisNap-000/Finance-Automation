# =============================================================================
# Finance_App.py — Main Streamlit entry point
#
# This is the root file Streamlit runs. It handles:
#   1. Page config and global CSS styling
#   2. Authentication gate (stops rendering if not logged in)
#   3. Loading shared data (account names) used across pages
#   4. Top navigation bar with three page buttons
#   5. Routing to the correct page component
#   6. Dashboard rendering (filters, KPIs, charts, tables)
#
# To run: `streamlit run Finance_App.py`
# =============================================================================

import streamlit as st

from auth import check_auth
from data.loader import load_transactions, load_account_balances, load_account_names
from data.transforms import apply_transformations
from ui.filters import render_filters
from ui.kpis import render_kpis
from ui.charts import render_monthly_cashflow
from ui.tables import render_pnl_breakdown, render_transactions_table, render_pnl_download
from ui.add_transaction import render_add_transaction
from ui.add_balance import render_add_balance
from ui.investments import render_investments

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(page_title="Finance Dashboard", page_icon="💲", layout="wide", initial_sidebar_state="expanded")

# ---------------------------
# GLOBAL STYLES
# ---------------------------
# Custom CSS to hide Streamlit's default chrome, style the title block,
# nav buttons, sidebar, metric cards, and dividers.
st.markdown("""
<style>
    /* Hide Streamlit chrome */
    #MainMenu                        { visibility: hidden; }
    footer                           { visibility: hidden; }
    [data-testid="stToolbar"]        { visibility: hidden; }
    header[data-testid="stHeader"]   { background: transparent; box-shadow: none; }

    /* Tighten top padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Title block */
    .title-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        margin-bottom: 0.3rem;
    }
    .app-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3.2rem;
        height: 3.2rem;
        border-radius: 50%;
        background-color: #17923c;
        color: #0D1117;
        font-size: 1.7rem;
        font-weight: 800;
        flex-shrink: 0;
    }
    .app-title {
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        color: #C9D1D9;
        margin: 0;
        line-height: 1;
    }
    .app-subtitle {
        text-align: center;
        font-size: 0.8rem;
        color: #6E7681;
        margin-bottom: 1.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    /* Nav buttons */
    div[data-testid="column"] > div > div > div > div > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
        padding: 0.45rem 0;
        width: 100%;
        transition: opacity 0.15s;
    }

    /* Sidebar — clean up */
    section[data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #21262D;
        overflow: visible !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
    }

    /* Prevent sidebar from being collapsed */
    [data-testid="stSidebarCollapseButton"] { display: none !important; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1rem 1.2rem;
    }

    /* Divider */
    hr {
        border-color: #21262D;
        margin: 0.75rem 0 1.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# AUTH
# ---------------------------
# check_auth() renders the login page and returns False if not logged in.
# st.stop() is not needed here — check_auth internally shows the login UI
# and the `if not` guard prevents the rest of the app from rendering.
if not check_auth():
    st.stop()

# ---------------------------
# LOAD SHARED DATA
# ---------------------------
# account_names is a dict: {account_name (str): account_id (int)}
# It is loaded once here and passed to any page that needs an account dropdown.
# The access_token is passed as a cache key so the result refreshes when the
# user's session changes (e.g. after re-login).
access_token  = st.session_state.get("access_token", "")
account_names = load_account_names(access_token)

# ---------------------------
# TITLE
# ---------------------------
st.markdown("""
<div class="title-container">
    <div class="app-logo">$</div>
    <p class="app-title">Finance Dashboard</p>
</div>
<p class="app-subtitle">Personal Financial Overview</p>
""", unsafe_allow_html=True)

# ---------------------------
# DEMO MODE BANNER
# ---------------------------
if st.session_state.get("demo_mode"):
    demo_col1, demo_col2 = st.columns([5, 1])
    with demo_col1:
        st.markdown(
        '<div style="background-color:rgba(23,146,60,0.09);border-left:4px solid #17923c;'
        'border-radius:4px;padding:0.75rem 1rem;color:#17923c;font-size:0.95rem;">'
        "Demo mode — viewing sample data. No real data is shown or saved.<div>",
        unsafe_allow_html=True,
        )
    with demo_col2:
        if st.button("Exit Demo", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ---------------------------
# CENTERED NAV BUTTONS
# ---------------------------
# Default to Dashboard on first load.
if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"

# Four equal nav buttons centered with padding columns on each side.
_, col1, col2, col3, col4, _ = st.columns([1, 1, 1, 1, 1, 1])

if col1.button("Dashboard", use_container_width=True,
               type="primary" if st.session_state["page"] == "Dashboard" else "secondary"):
    st.session_state["page"] = "Dashboard"
    st.rerun()

if col2.button("Investments", use_container_width=True,
               type="primary" if st.session_state["page"] == "Investments" else "secondary"):
    st.session_state["page"] = "Investments"
    st.rerun()

if col3.button("Add Transaction", use_container_width=True,
               type="primary" if st.session_state["page"] == "Add Transaction" else "secondary"):
    st.session_state["page"] = "Add Transaction"
    st.rerun()

if col4.button("Add Starting Balance", use_container_width=True,
               type="primary" if st.session_state["page"] == "Add Starting Balance" else "secondary"):
    st.session_state["page"] = "Add Starting Balance"
    st.rerun()

st.divider()

# ---------------------------
# PAGE ROUTING
# ---------------------------
# Form pages need no transaction data or sidebar — route them immediately.
if st.session_state["page"] == "Add Transaction":
    render_add_transaction(account_names)
    st.stop()

if st.session_state["page"] == "Add Starting Balance":
    render_add_balance(account_names)
    st.stop()

# ---------------------------
# LOAD TRANSACTIONS + SIDEBAR FILTERS
# ---------------------------
# Dashboard and Investments both show the sidebar with transaction-based filters.
df_raw = load_transactions(access_token)

if not df_raw.empty:
    df = apply_transformations(df_raw)
    st.sidebar.header("Filters")
    year_select, month_select, txn_types = render_filters(df)
else:
    df = df_raw
    year_select, month_select, txn_types = [], [], []

# ---------------------------
# INVESTMENTS PAGE
# ---------------------------
if st.session_state["page"] == "Investments":
    render_investments(access_token, year_select, month_select)
    st.stop()

# ---------------------------
# DASHBOARD — LOAD & TRANSFORM
# ---------------------------
account_balances = load_account_balances(access_token)

if df_raw.empty:
    st.markdown(
        '<div style="background-color:rgba(23,146,60,0.09);border-left:4px solid #17923c;'
        'border-radius:4px;padding:0.75rem 1rem;color:#17923c;font-size:0.95rem;">'
        "No transactions found in the database.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# Apply all three filters simultaneously
filtered_df = df[
    (df["Year"].isin(year_select)) &
    (df["Month"].isin(month_select)) &
    (df["Transaction Type"].isin(txn_types))
]

# ---------------------------
# RENDER DASHBOARD
# ---------------------------
render_kpis(filtered_df, account_balances)
render_monthly_cashflow(filtered_df)
pivoted_df = render_pnl_breakdown(filtered_df, account_names)
render_transactions_table(filtered_df)
render_pnl_download(pivoted_df)
