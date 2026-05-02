# =============================================================================
# ui/kpis.py — KPI metric cards for the dashboard
#
# Renders a 3-row grid of st.metric cards:
#   Row 1 (center): Total Balance across all BALANCE_ACCOUNTS
#   Row 2: Income | Spending | Net Cash Flow  (from filtered transactions)
#   Row 3: Per-account balances (Checking, Savings, CD)
#
# Income and Spending are calculated from the filtered DataFrame (respects
# the sidebar Year/Month/Type filters). Account balances come from
# load_account_balances() which is computed independently of filters.
# =============================================================================

import streamlit as st

from config import BALANCE_ACCOUNTS, BANK_ACCOUNTS, INVESTMENT_ACCOUNTS


def render_kpis(filtered_df, account_balances: dict):
    """
    Render all KPI metric cards.

    Args:
        filtered_df:      Filtered transactions DataFrame from Finance_App.py.
                          Used to compute Income, Spending, and Net Cash Flow.
        account_balances: Dict of {account_name: current_balance} from
                          load_account_balances(). Used for balance metrics.

    Notes:
      - Income     : sum of "Interest" and "Income" type transactions
      - Spending   : sum of "Expense" type transactions
      - Net        : Income + Spending
      - Row 3      : Bank/cash account balances (BANK_ACCOUNTS in config.py)
      - Row 4      : Investment account balances (INVESTMENT_ACCOUNTS in config.py)

    Debug tip: If a balance shows $0.00, the account_name in config.py does not
    match dim_accounts exactly (case-sensitive), or no seed record exists in
    dim_starting_balances for that account.
    """
    income   = filtered_df.loc[filtered_df["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
    spending = filtered_df.loc[filtered_df["Transaction Type"].isin(["Expense"]), "Amount"].sum()
    net      = income + spending

    total_balance = sum(account_balances.get(acc, 0) for acc in BALANCE_ACCOUNTS)

    # Row 1: Total Balance (centered)
    spacer, row1_col2, spacer2 = st.columns(3)
    row1_col2.metric("Total Balance", f"${total_balance:,.2f}")

    # Row 2: Income / Spending / Net Cash Flow
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    row2_col1.metric("Income",        f"${income:,.2f}")
    row2_col2.metric("Spending",      f"${spending:,.2f}")
    row2_col3.metric("Net Cash Flow", f"${net:,.2f}")

    # Row 3: Bank / cash account balances
    bank_cols = st.columns(len(BANK_ACCOUNTS))
    for col, name in zip(bank_cols, BANK_ACCOUNTS):
        col.metric(f"{name}", f"${account_balances.get(name, 0):,.2f}")

    # # Row 4: Investment account balances
    # inv_cols = st.columns(len(INVESTMENT_ACCOUNTS))
    # for col, name in zip(inv_cols, INVESTMENT_ACCOUNTS):
    #     col.metric(f"{name}", f"${account_balances.get(name, 0):,.2f}")
