import calendar

import streamlit as st


def render_filters(df):
    default_year = list({int(df["Year"].max())})
    default_month = df["Month"].unique().tolist()
    default_transactions = df["Transaction Type"].unique().tolist()

    if "year" not in st.session_state:
        st.session_state.year = default_year
    if "month" not in st.session_state:
        st.session_state.month = default_month
    if "transaction_type" not in st.session_state:
        st.session_state.transaction_type = default_transactions

    def reset_filters():
        st.session_state.year = default_year
        st.session_state.month = default_month
        st.session_state.transaction_type = default_transactions

    st.sidebar.button("🔄 Reset Filters", on_click=reset_filters)

    year_select = st.sidebar.multiselect(
        "Year",
        options=sorted(df["Year"].unique()),
        key="year"
    )

    month_select = st.sidebar.multiselect(
        "Month",
        options=list(calendar.month_name)[1:],
        key="month"
    )

    txn_types = st.sidebar.multiselect(
        "Transaction Type",
        options=df["Transaction Type"].unique(),
        key="transaction_type"
    )

    return year_select, month_select, txn_types
