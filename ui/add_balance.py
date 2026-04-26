# =============================================================================
# ui/add_balance.py — "Add Starting Balance" page
#
# Two-step form flow (mirrors add_transaction.py):
#   Step 1 (form)    : User selects account, enters balance, date, optional notes
#   Step 2 (confirm) : User reviews and confirms or goes back to edit
#
# A "starting balance" (seed balance) is a snapshot of an account's balance
# on a specific date. The load_account_balances() function uses these seeds
# as the baseline and adds all subsequent transactions to compute the
# current balance shown on the dashboard.
#
# Account handling:
#   - Dropdown shows human-readable names from dim_accounts
#   - The corresponding integer ID (account_id) is written to dim_starting_balances
#   - "account_name" is stored for the confirmation screen and stripped before insert
#
# Why seed balances matter:
#   If no seed balance exists for an account, that account will not appear in
#   the account balance KPIs on the dashboard. Add at least one seed per account.
# =============================================================================

from datetime import date

import streamlit as st

from data.loader import insert_starting_balance, load_account_balances


def render_add_balance(account_names: dict) -> None:
    """
    Entry point for the Add Starting Balance page.

    Reads the current step from session state and delegates to the
    appropriate sub-renderer.

    Args:
        account_names: Dict of {account_name: account_id} from load_account_names().
    """
    st.title("Add Starting Balance")

    if st.session_state.get("demo_mode"):
        st.markdown(
        '<div style="background-color:rgba(23,146,60,0.09);border-left:4px solid #17923c;'
        'border-radius:4px;padding:0.75rem 1rem;color:#17923c;font-size:0.95rem;">'
        "You are viewing demo data. Log in with real credentials to add balances.<div>",
        unsafe_allow_html=True,
        )
        return

    step = st.session_state.get("add_bal_step", "form")

    if step == "form":
        _render_form(account_names)
    elif step == "confirm":
        _render_confirmation()


def _render_form(account_names: dict) -> None:
    """
    Render the starting balance input form (Step 1).

    Fields:
      - Account       : dropdown of account names (writes account_id to DB)
      - Balance       : the account balance as of the recorded date
      - Recorded Date : the date the balance was observed/snapshotted
      - Notes         : optional free text

    On submit, stores the pending balance dict in session state and advances
    to the confirmation step.

    Debug tip: The Recorded Date should be set to a date BEFORE any transactions
    you want included in the running balance. The balance calculation in
    load_account_balances() only sums transactions AFTER the seed date.
    """
    with st.form("add_balance_form", border=True):
        account       = st.selectbox("Account", options=list(account_names.keys()))
        balance       = st.number_input("Balance", step=0.01, format="%.2f",
                                        help="Enter the account balance as of the recorded date.")
        recorded_date = st.date_input("Recorded Date", value=date.today())
        notes         = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Review", use_container_width=True, type="primary")

    if submitted:
        st.session_state["pending_balance"] = {
            "account_id":    account_names[account],  # integer FK for DB
            "account_name":  account,                  # display only — stripped before insert
            "balance":       balance,
            "recorded_date": recorded_date.isoformat(),
            "notes":         notes or None,
            "user_id":       st.session_state.get("user_id"),
        }
        st.session_state["add_bal_step"] = "confirm"
        st.rerun()


def _render_confirmation() -> None:
    """
    Render the confirmation screen (Step 2).

    Displays all pending balance fields as metric cards. The user confirms
    to insert or goes back to edit.

    On confirm:
      - "account_name" is stripped from the dict before inserting
      - load_account_balances cache is cleared so the dashboard KPIs update
        immediately after saving
      - Session state is cleaned up and the step resets to "form"

    Debug tip: If saving fails, the full Supabase error is shown. Common causes:
      - FK violation: account_id not found in dim_accounts
      - RLS violation: INSERT policy missing on dim_starting_balances in Supabase
    """
    st.subheader("Confirm Starting Balance")
    st.write("Review the details below before saving to the database.")

    bal = st.session_state.get("pending_balance", {})

    # Maps DB/session keys → display labels
    labels = {
        "account_name":  "Account",
        "balance":       "Balance",
        "recorded_date": "Recorded Date",
        "notes":         "Notes",
    }

    for key, label in labels.items():
        value = bal.get(key)
        if label == "Balance" and value is not None:
            st.metric(label, f"${value:,.2f}")
        else:
            st.metric(label, value if value is not None else "—")

    st.divider()
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Confirm & Save", type="primary", use_container_width=True):
            try:
                # Strip display-only key before inserting into the database
                insert_starting_balance({k: v for k, v in bal.items() if k != "account_name"})
                load_account_balances.clear()  # force dashboard to recalculate balances
                st.session_state.pop("pending_balance", None)
                st.session_state["add_bal_step"] = "form"
                st.success("Starting balance saved successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save starting balance: {e}")

    with btn_col2:
        if st.button("Go Back & Edit", use_container_width=True):
            st.session_state["add_bal_step"] = "form"
            st.rerun()
