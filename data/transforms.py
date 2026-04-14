import calendar

import numpy as np
import pandas as pd

import streamlit as st

from config import BAD_ROW_COLUMNS, DATA_TYPES, DESC_PATTERNS, TRANS_TYPE_PATTERNS


def clean_data(df):
    for col in BAD_ROW_COLUMNS.values():
        if col in df.columns:
            df[col] = df[col].replace("", np.nan)

    for col in ["Debit", "Credit", "Account Running Balance"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[\$,]", "", regex=True),
                errors="coerce"
            )

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df


def apply_transformations(df):
    # Second blank-to-null pass after merge
    for col in BAD_ROW_COLUMNS.values():
        if col in df.columns:
            df[col] = df[col].replace("", np.nan)

    df = df.astype(DATA_TYPES)
    df = df.drop(columns=["Bank RTN"])

    df["Debit"] = df["Debit"].fillna(0)
    df["Credit"] = df["Credit"].fillna(0)
    df["Amount"] = df["Credit"] - df["Debit"]
    df = df.drop(columns=["Debit", "Credit"])

    df["Description"] = df["Description"].replace(DESC_PATTERNS, regex=True)
    df["Transaction Type"] = df["Transaction Type"].replace(TRANS_TYPE_PATTERNS, regex=True)

    df["Transaction Type"] = np.where(
        df["Description"].str.contains("WITHDRAWAL", case=False, na=False),
        "Withdrawal",
        df["Transaction Type"]
    )

    df.loc[
        (df["Transaction Type"].isna()) & (df["Amount"] < 0) & (df["Account Name"] == "Credit Card"),
        "Transaction Type"
    ] = "Expense"

    df.loc[
        (df["Transaction Type"].isna()) & (df["Amount"] > 0) & (df["Account Name"] == "Credit Card"),
        "Transaction Type"
    ] = "CC Payment"

    _apply_pnl_flag(df)

    df["Year"] = df["Date"].apply(lambda d: d.year)
    df["MonthNum"] = df["Date"].apply(lambda d: d.month)
    df["Month"] = df["MonthNum"].apply(lambda m: calendar.month_name[m])
    df.drop(columns=["MonthNum"], inplace=True)

    return df


def _apply_pnl_flag(df):
    df["PnL_flag"] = True

    df.loc[
        (df["Account Name"] == "Credit Card") & (df["Amount"] > 0),
        "PnL_flag"
    ] = False

    df.loc[
        (df["Transaction Type"].str.upper() == "TRANSFER") &
        (df["Description"].str.upper() == st.secrets["CC_SECRET"]),
        "PnL_flag"
    ] = False
