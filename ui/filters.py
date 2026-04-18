# =============================================================================
# ui/filters.py — Sidebar filter controls for the dashboard
#
# Renders three multiselect filters in the sidebar (Year, Month, Transaction
# Type) and returns the selected values to Finance_App.py for filtering.
#
# Filter state is stored in st.session_state so selections persist across
# page rerenders. Defaults are set on first load only (when keys are absent).
# =============================================================================

import calendar

import streamlit as st


def render_filters(df):
    """
    Render sidebar filters and return the current selections.

    Defaults on first load:
      - Year    : only the most recent year in the data
      - Month   : all months present in the data
      - Type    : all transaction types present in the data

    A "Reset Filters" button restores all filters to their defaults.

    Args:
        df: Transformed transactions DataFrame (must have Year, Month,
            Transaction Type columns)

    Returns:
        Tuple of (year_select, month_select, txn_types) — each is a list
        of the currently selected values. Pass these directly to Finance_App.py
        for filtering the DataFrame.

    Debug tip: If filtering produces an empty result, check that the selected
    Year/Month combination has data. The multiselects default to the most recent
    year only, so older data is hidden until you add earlier years to the filter.
    """
    default_year         = list({int(df["Year"].max())})
    default_month        = df["Month"].unique().tolist()
    default_transactions = df["Transaction Type"].unique().tolist()

    # Initialize session state keys on first render only
    if "year" not in st.session_state:
        st.session_state.year = default_year
    if "month" not in st.session_state:
        st.session_state.month = default_month
    if "transaction_type" not in st.session_state:
        st.session_state.transaction_type = default_transactions

    def reset_filters():
        # Callback bound to the Reset button — reassigns all three filter keys
        st.session_state.year             = default_year
        st.session_state.month            = default_month
        st.session_state.transaction_type = default_transactions

    st.sidebar.button("🔄 Reset Filters", on_click=reset_filters)

    year_select = st.sidebar.multiselect(
        "Year",
        options=sorted(df["Year"].unique()),
        key="year"       # key links this widget to st.session_state.year
    )

    month_select = st.sidebar.multiselect(
        "Month",
        options=list(calendar.month_name)[1:],   # skip the empty first entry
        key="month"
    )

    txn_types = st.sidebar.multiselect(
        "Transaction Type",
        options=df["Transaction Type"].unique(),
        key="transaction_type"
    )

    return year_select, month_select, txn_types
