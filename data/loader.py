import pandas as pd
import streamlit as st
from supabase import create_client, Client


def _get_authenticated_client() -> Client:
    client = create_client(st.secrets["url"], st.secrets["key"])
    access_token = st.session_state.get("access_token", "")
    refresh_token = st.session_state.get("refresh_token", "")
    if access_token:
        client.auth.set_session(access_token, refresh_token)
    return client


@st.cache_data(ttl=300, show_spinner="Loading transactions...")
def load_transactions(access_token: str) -> pd.DataFrame:
    client = _get_authenticated_client()

    res = client.table("FCT_TRANSACTIONS").select(
        "TRANSACTION_DATE, ACCOUNT, TRANSACTION_TYPE, VENDOR_NAME, "
        "AMOUNT, CATEGORY, CHECK_NUMBER, NOTES"
    ).execute()

    if not res.data:
        return pd.DataFrame()

    df = pd.DataFrame(res.data).rename(columns={
        "TRANSACTION_DATE": "Date",
        "ACCOUNT":          "Account",
        "TRANSACTION_TYPE": "Transaction Type",
        "VENDOR_NAME":      "Vendor",
        "AMOUNT":           "Amount",
        "CATEGORY":         "Category",
        "CHECK_NUMBER":     "Check Number",
        "NOTES":            "Notes",
    })

    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    return df


@st.cache_data(ttl=300, show_spinner="Loading account balances...")
def load_account_balances(access_token: str) -> dict:
    """
    Returns {account_name: current_balance} computed as:
        most recent seed balance + SUM of all transactions after the seed date
    """
    client = _get_authenticated_client()

    sb_res = client.table("DIM_STARTING_BALANCES").select(
        "ACCOUNT_ID, BALANCE, RECORDED_DATE, DIM_ACCOUNTS!inner(ACCOUNT_NAME)"
    ).execute()

    if not sb_res.data:
        return {}

    df_sb = pd.DataFrame(sb_res.data)
    df_sb["ACCOUNT_NAME"]   = df_sb["DIM_ACCOUNTS"].apply(lambda x: x["ACCOUNT_NAME"])
    df_sb["RECORDED_DATE"]  = pd.to_datetime(df_sb["RECORDED_DATE"])
    df_sb["BALANCE"]        = pd.to_numeric(df_sb["BALANCE"], errors="coerce").fillna(0)

    # Keep only the most recent seed per account
    latest_seeds = (
        df_sb.sort_values("RECORDED_DATE")
        .groupby("ACCOUNT_NAME")
        .last()
        .reset_index()[["ACCOUNT_NAME", "BALANCE", "RECORDED_DATE"]]
    )

    txn_res = client.table("FCT_TRANSACTIONS").select(
        "ACCOUNT, AMOUNT, TRANSACTION_DATE"
    ).execute()

    df_txn = pd.DataFrame(txn_res.data) if txn_res.data else pd.DataFrame()

    if not df_txn.empty:
        df_txn["TRANSACTION_DATE"] = pd.to_datetime(df_txn["TRANSACTION_DATE"], errors="coerce")
        df_txn["AMOUNT"]           = pd.to_numeric(df_txn["AMOUNT"], errors="coerce").fillna(0)

    account_balances = {}
    for _, seed in latest_seeds.iterrows():
        account_name = seed["ACCOUNT_NAME"]
        seed_balance = seed["BALANCE"]
        seed_date    = seed["RECORDED_DATE"]

        if not df_txn.empty:
            post_seed = df_txn[
                (df_txn["ACCOUNT"] == account_name) &
                (df_txn["TRANSACTION_DATE"] > seed_date)
            ]
            current_balance = seed_balance + post_seed["AMOUNT"].sum()
        else:
            current_balance = seed_balance

        account_balances[account_name] = current_balance

    return account_balances


@st.cache_data(ttl=300, show_spinner=False)
def load_account_names(access_token: str) -> list:
    client = _get_authenticated_client()
    res = client.table("DIM_ACCOUNTS").select("ACCOUNT_NAME").order("ACCOUNT_NAME").execute()
    if not res.data:
        return []
    return [row["ACCOUNT_NAME"] for row in res.data]


def insert_transaction(data: dict) -> None:
    client = _get_authenticated_client()
    client.table("FCT_TRANSACTIONS").insert(data).execute()
