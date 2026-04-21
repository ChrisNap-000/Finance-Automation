# =============================================================================
# data/transforms.py — DataFrame transformation and feature engineering
#
# Applies derived columns to the raw transactions DataFrame after it is loaded
# from Supabase. All transformations happen in-memory on the Pandas DataFrame.
#
# Called once per dashboard load in Finance_App.py after load_transactions().
# =============================================================================

import calendar

import streamlit as st

from config import INVESTMENT_ACCOUNTS


def apply_transformations(df):
    """
    Add derived columns to the raw transactions DataFrame and return it.

    Derived columns added:
      - PnL_flag (bool) : False for transactions excluded from PnL reporting
      - Year (int)      : calendar year of the transaction date
      - Month (str)     : full month name (e.g. "January")

    The MonthNum column is created temporarily for Month derivation and then
    dropped so it does not appear in the UI.

    Args:
        df: Raw DataFrame from load_transactions()

    Returns:
        The same DataFrame with additional columns added in place.
    """
    if df.empty:
        return df

    _apply_pnl_flag(df)

    df["Year"]     = df["Date"].dt.year
    df["MonthNum"] = df["Date"].dt.month
    df["Month"]    = df["MonthNum"].apply(lambda m: calendar.month_name[m])
    df.drop(columns=["MonthNum"], inplace=True)

    return df


def _apply_pnl_flag(df):
    """
    Add a PnL_flag boolean column to exclude certain transactions from
    profit-and-loss calculations.

    Rules (PnL_flag = False means excluded from PnL):
      1. Credit card payments received into the credit card account are not
         income — they are just the account being paid off.
      2. Transfers sent to the credit card vendor are not spending — they are
         internal balance moves, not actual expenses.

    The credit card vendor name is stored in st.secrets["CC_SECRET"] to keep
    it out of source control.

    Debug tip: If a transaction is incorrectly appearing in (or excluded from)
    PnL, check the Transaction Type and Vendor values in the database, and
    verify CC_SECRET in .streamlit/secrets.toml matches exactly.
    """
    # Start with all transactions included in PnL
    df["PnL_flag"] = True

    # Credit card payments received into TD Cash should not count as income
    df.loc[
        (df["Account"] == "TD Cash") & (df["Amount"] > 0),
        "PnL_flag"
    ] = False

    # Outgoing transfer to credit card should not count as spending
    df.loc[
        (df["Transaction Type"].str.upper() == "TRANSFER") &
        (df["Vendor"].str.upper() == st.secrets["CC_SECRET"].upper()),
        "PnL_flag"
    ] = False

    # Investment account transactions are not income/spending — exclude from PnL
    df.loc[df["Account"].isin(INVESTMENT_ACCOUNTS), "PnL_flag"] = False
