import streamlit as st

from config import BALANCE_ACCOUNTS


def render_kpis(df, filtered_df):
    income = filtered_df.loc[filtered_df["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
    spending = filtered_df.loc[filtered_df["Transaction Type"].isin(["Expense"]), "Amount"].sum()
    net = income + spending

    ending_balances = {
        acc: (
            filtered_df.loc[df["Account Name"] == acc]
            .loc[lambda x: x["Date"] == x["Date"].max(), "Account Running Balance"]
            .mean()
        )
        for acc in BALANCE_ACCOUNTS
    }

    checking_balance = ending_balances["Checking"]
    savings_balance = ending_balances["Savings"]
    cd_balance = ending_balances["CD"]
    total_balance = checking_balance + savings_balance + cd_balance

    spacer, row1_col2, spacer2 = st.columns(3)
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    row3_col1, row3_col2, row3_col3 = st.columns(3)

    row1_col2.metric("Total Balance", f"${total_balance:,.2f}")
    row2_col1.metric("Income", f"${income:,.2f}")
    row2_col2.metric("Spending", f"${spending:,.2f}")
    row2_col3.metric("Net Cash Flow", f"${net:,.2f}")
    row3_col1.metric("Checking Balance", f"${checking_balance:,.2f}")
    row3_col2.metric("Savings Balance", f"${savings_balance:,.2f}")
    row3_col3.metric("CD Balance", f"${cd_balance:,.2f}")
