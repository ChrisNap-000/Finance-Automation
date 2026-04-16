import calendar

import streamlit as st


def apply_transformations(df):
    if df.empty:
        return df

    _apply_pnl_flag(df)

    df["Year"]     = df["Date"].dt.year
    df["MonthNum"] = df["Date"].dt.month
    df["Month"]    = df["MonthNum"].apply(lambda m: calendar.month_name[m])
    df.drop(columns=["MonthNum"], inplace=True)

    return df


def _apply_pnl_flag(df):
    df["PnL_flag"] = True

    # Credit card payments received should not count as income
    df.loc[
        (df["Account"] == "Credit Card") & (df["Amount"] > 0),
        "PnL_flag"
    ] = False

    # Outgoing transfer to credit card should not count as spending
    df.loc[
        (df["Transaction Type"].str.upper() == "TRANSFER") &
        (df["Vendor"].str.upper() == st.secrets["CC_SECRET"].upper()),
        "PnL_flag"
    ] = False
