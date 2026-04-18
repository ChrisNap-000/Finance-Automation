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

from config import BALANCE_ACCOUNTS


def render_kpis(filtered_df, account_balances: dict):
    """
    Render all KPI metric cards.

    Args:
        filtered_df:      Filtered transactions DataFrame from Finance_App.py.
                          Used to compute Income, Spending, and Net Cash Flow.
        account_balances: Dict of {account_name: current_balance} from
                          load_account_balances(). Used for balance metrics.

    Notes:
      - Income  : sum of "Interest" and "Income" type transactions (positive)
      - Spending: sum of "Expense" type transactions (typically negative)
      - Net     : Income + Spending (negative net means you spent more than earned)
      - BALANCE_ACCOUNTS controls which accounts appear in Row 3 and the Total.
        Update config.py if you add or rename accounts.

    Debug tip: If a balance shows $0.00 when it shouldn't, the account_name in
    BALANCE_ACCOUNTS (config.py) does not match the name in dim_accounts exactly
    (case-sensitive). Also check that a seed record exists in dim_starting_balances.
    """
    income   = filtered_df.loc[filtered_df["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
    spending = filtered_df.loc[filtered_df["Transaction Type"].isin(["Expense"]), "Amount"].sum()
    net      = income + spending

    # Pull individual balances — default to 0 if an account has no seed record
    checking_balance = account_balances.get("Checking", 0)
    savings_balance  = account_balances.get("Savings",  0)
    cd_balance       = account_balances.get("CD",       0)
    total_balance    = sum(account_balances.get(acc, 0) for acc in BALANCE_ACCOUNTS)

    # Row 1: Total Balance (centered in a 3-col layout using the middle column)
    spacer, row1_col2, spacer2 = st.columns(3)

    # Row 2: Income / Spending / Net Cash Flow
    row2_col1, row2_col2, row2_col3 = st.columns(3)

    # Row 3: Individual account balances
    row3_col1, row3_col2, row3_col3 = st.columns(3)

    row1_col2.metric("Total Balance",     f"${total_balance:,.2f}")
    row2_col1.metric("Income",            f"${income:,.2f}")
    row2_col2.metric("Spending",          f"${spending:,.2f}")
    row2_col3.metric("Net Cash Flow",     f"${net:,.2f}")
    row3_col1.metric("Checking Balance",  f"${checking_balance:,.2f}")
    row3_col2.metric("Savings Balance",   f"${savings_balance:,.2f}")
    row3_col3.metric("CD Balance",        f"${cd_balance:,.2f}")
