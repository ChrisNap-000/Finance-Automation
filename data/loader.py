# =============================================================================
# data/loader.py — Supabase data loading and writing functions
#
# All database access goes through this module. Each load function:
#   - Creates an authenticated Supabase client using the current session tokens
#   - Is decorated with @st.cache_data so repeated renders don't hit the DB
#   - Accepts `access_token` as a parameter (even if unused inside) so that
#     the cache key changes when the user's session changes
#
# Database schema (Supabase / PostgreSQL):
#   fct_transactions
#     transaction_date  date
#     account_id        int4  FK → dim_accounts.id
#     transaction_type  text
#     vendor_name       text
#     amount            numeric
#     category          text (nullable)
#     check_number      text (nullable)
#     notes             text (nullable)
#     user_id           uuid  FK → auth.users.id
#
#   dim_accounts
#     id                int4  (primary key)
#     account_name      text
#     account_type      text
#     user_id           uuid
#
#   dim_starting_balances
#     account_id        int4  FK → dim_accounts.id
#     balance           numeric
#     recorded_date     date
#     notes             text (nullable)
#     user_id           uuid
#
# RLS note:
#   All tables have Row Level Security enabled in Supabase. The authenticated
#   Supabase client (using the user's JWT) will only return rows the user owns.
#   If a query returns empty unexpectedly, check the RLS policies in the
#   Supabase dashboard under Authentication → Policies.
# =============================================================================

import pandas as pd
import streamlit as st
from supabase import create_client, Client


def _get_authenticated_client() -> Client:
    """
    Create a Supabase client and attach the current user's session tokens.

    The client is created with the anon key from st.secrets, then the user's
    JWT (access_token + refresh_token) is set so RLS policies apply correctly.

    Debug tip: If queries return empty data, verify that access_token is present
    in st.session_state (the user must be logged in before calling this).
    """
    client = create_client(st.secrets["url"], st.secrets["key"])
    access_token  = st.session_state.get("access_token", "")
    refresh_token = st.session_state.get("refresh_token", "")
    if access_token:
        client.auth.set_session(access_token, refresh_token)
    return client


@st.cache_data(ttl=300, show_spinner="Loading transactions...")
def load_transactions(access_token: str) -> pd.DataFrame:
    """
    Load all transactions from fct_transactions, joined to dim_accounts
    to resolve account_id → account_name for display.

    Returns a DataFrame with columns:
      Date, Account, Transaction Type, Vendor, Amount, Category,
      Check Number, Notes

    The cache expires every 5 minutes (ttl=300). To force a refresh immediately
    (e.g. after inserting a new transaction), call load_transactions.clear().

    Debug tip: If Account shows as None for a row, the FK join failed —
    the account_id in fct_transactions does not exist in dim_accounts.
    """
    client = _get_authenticated_client()

    # Join dim_accounts to resolve account_id → account_name in one query
    res = client.table("fct_transactions").select(
        "transaction_date, account_id, dim_accounts(account_name), transaction_type, vendor_name, "
        "amount, category, check_number, notes"
    ).execute()

    if not res.data:
        return pd.DataFrame()

    df = pd.DataFrame(res.data)

    # Extract the nested account_name from the joined dim_accounts dict
    df["account_name"] = df["dim_accounts"].apply(lambda x: x["account_name"] if x else None)
    df.drop(columns=["dim_accounts", "account_id"], inplace=True)

    df.rename(columns={
        "transaction_date": "Date",
        "account_name":     "Account",
        "transaction_type": "Transaction Type",
        "vendor_name":      "Vendor",
        "amount":           "Amount",
        "category":         "Category",
        "check_number":     "Check Number",
        "notes":            "Notes",
    }, inplace=True)

    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    return df


@st.cache_data(ttl=300, show_spinner="Loading account balances...")
def load_account_balances(access_token: str) -> dict:
    """
    Compute current balances for all accounts as:
        current_balance = most_recent_seed_balance + SUM(transactions after seed date)

    Returns a dict: {account_name (str): current_balance (float)}

    Logic:
      1. Load dim_starting_balances joined to dim_accounts (to get account names)
      2. Keep only the most recent seed balance per account
      3. Load all transactions joined to dim_accounts (to match by account name)
      4. For each account, sum all transactions that occurred after the seed date
      5. Add the seed balance to get the running current balance

    Debug tip: If balances look wrong, check:
      - That dim_starting_balances has a seed record for each account
      - That transaction amounts use the correct sign (negative = debit)
      - That recorded_date on the seed is earlier than the transactions you expect
    """
    client = _get_authenticated_client()

    # Load seed balances with account names via FK join
    sb_res = client.table("dim_starting_balances").select(
        "account_id, balance, recorded_date, dim_accounts!inner(account_name)"
    ).execute()

    if not sb_res.data:
        return {}

    df_sb = pd.DataFrame(sb_res.data)
    df_sb["account_name"]  = df_sb["dim_accounts"].apply(lambda x: x["account_name"])
    df_sb["recorded_date"] = pd.to_datetime(df_sb["recorded_date"])
    df_sb["balance"]       = pd.to_numeric(df_sb["balance"], errors="coerce").fillna(0)

    # Keep only the most recent seed per account (handles multiple seed records)
    latest_seeds = (
        df_sb.sort_values("recorded_date")
        .groupby("account_name")
        .last()
        .reset_index()[["account_name", "balance", "recorded_date"]]
    )

    # Load transactions with account names via FK join
    txn_res = client.table("fct_transactions").select(
        "account_id, amount, transaction_date, dim_accounts(account_name)"
    ).execute()

    df_txn = pd.DataFrame(txn_res.data) if txn_res.data else pd.DataFrame()

    if not df_txn.empty:
        df_txn["account_name"]     = df_txn["dim_accounts"].apply(lambda x: x["account_name"] if x else None)
        df_txn.drop(columns=["dim_accounts", "account_id"], inplace=True)
        df_txn["transaction_date"] = pd.to_datetime(df_txn["transaction_date"], errors="coerce")
        df_txn["amount"]           = pd.to_numeric(df_txn["amount"], errors="coerce").fillna(0)

    account_balances = {}
    for _, seed in latest_seeds.iterrows():
        account_name = seed["account_name"]
        seed_balance = seed["balance"]
        seed_date    = seed["recorded_date"]

        if not df_txn.empty:
            # Only count transactions that happened AFTER the seed date
            post_seed = df_txn[
                (df_txn["account_name"] == account_name) &
                (df_txn["transaction_date"] > seed_date)
            ]
            current_balance = seed_balance + post_seed["amount"].sum()
        else:
            current_balance = seed_balance

        account_balances[account_name] = current_balance

    return account_balances


@st.cache_data(ttl=300, show_spinner=False)
def load_account_names(access_token: str) -> dict:
    """
    Load all account names and their IDs from dim_accounts.

    Returns a dict: {account_name (str): id (int)}

    This dict is used by the Add Transaction and Add Starting Balance forms:
      - Keys are displayed in the dropdown (human-readable names)
      - Values are written to the database as the foreign key (account_id)

    Debug tip: If the dropdown is empty, this function returned {}. Common causes:
      1. No RLS SELECT policy exists for dim_accounts — add one in Supabase:
            CREATE POLICY "authenticated users can read accounts"
            ON dim_accounts FOR SELECT TO authenticated USING (true);
      2. The Supabase client is not authenticated (access_token missing from session)
      3. The dim_accounts table is empty
    """
    client = _get_authenticated_client()
    res = client.table("dim_accounts").select("id, account_name").order("account_name").execute()
    if not res.data:
        return {}
    return {row["account_name"]: row["id"] for row in res.data}


def insert_transaction(data: dict) -> None:
    """
    Insert a single row into fct_transactions.

    The `data` dict should contain only valid column names for the table.
    The caller (ui/add_transaction.py) is responsible for stripping any
    display-only keys (e.g. 'account_name') before calling this function.

    Debug tip: If the insert fails with a FK violation, account_id does not
    exist in dim_accounts. If it fails with an RLS error, ensure the INSERT
    policy is configured in Supabase.
    """
    client = _get_authenticated_client()
    client.table("fct_transactions").insert(data).execute()


def insert_starting_balance(data: dict) -> None:
    """
    Insert a single row into dim_starting_balances.

    The `data` dict should contain only valid column names for the table.
    The caller (ui/add_balance.py) strips the display-only 'account_name'
    key before calling this function.

    After inserting, the caller clears the load_account_balances cache so
    the dashboard KPIs reflect the new balance immediately.
    """
    client = _get_authenticated_client()
    client.table("dim_starting_balances").insert(data).execute()
