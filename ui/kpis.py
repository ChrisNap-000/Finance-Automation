import streamlit as st

from config import BALANCE_ACCOUNTS


def render_kpis(filtered_df, account_balances: dict):
    income   = filtered_df.loc[filtered_df["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
    spending = filtered_df.loc[filtered_df["Transaction Type"].isin(["Expense"]), "Amount"].sum()
    net      = income + spending

    checking_balance = account_balances.get("Checking", 0)
    savings_balance  = account_balances.get("Savings", 0)
    cd_balance       = account_balances.get("CD", 0)
    total_balance    = sum(account_balances.get(acc, 0) for acc in BALANCE_ACCOUNTS)

    spacer, row1_col2, spacer2 = st.columns(3)
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    row3_col1, row3_col2, row3_col3 = st.columns(3)

    row1_col2.metric("Total Balance",     f"${total_balance:,.2f}")
    row2_col1.metric("Income",            f"${income:,.2f}")
    row2_col2.metric("Spending",          f"${spending:,.2f}")
    row2_col3.metric("Net Cash Flow",     f"${net:,.2f}")
    row3_col1.metric("Checking Balance",  f"${checking_balance:,.2f}")
    row3_col2.metric("Savings Balance",   f"${savings_balance:,.2f}")
    row3_col3.metric("CD Balance",        f"${cd_balance:,.2f}")
