# =============================================================================
# ui/add_transaction.py — "Add Transaction" page
#
# Two-step form flow:
#   Step 1 (form)    : User fills in transaction details and clicks "Review"
#   Step 2 (confirm) : User reviews a summary and clicks "Confirm & Save"
#                      or "Go Back & Edit" to return to the form
#
# The current step is tracked in st.session_state["add_txn_step"].
# The pending (unconfirmed) transaction dict is stored in
# st.session_state["pending_transaction"] between steps.
#
# Account handling:
#   - The account dropdown shows human-readable names from dim_accounts
#   - On submit, the corresponding integer ID (account_id) is stored for the DB
#   - The human-readable name is kept as "account_name" for the confirmation
#     screen only and is stripped before the DB insert
#
# Category handling:
#   - A predefined dropdown (CATEGORIES list) is shown
#   - Selecting "Other" enables a free-text field for custom input
#   - Leaving the dropdown blank stores NULL in the database
# =============================================================================

from datetime import date

import streamlit as st

from data.loader import insert_transaction, load_transactions

TRANSACTION_TYPES = [
    "Expense",
    "Income",
    "Transfer",
    "Deposit",
    "Withdrawal",
    "Interest",
    "CC Payment",
]

# Predefined expense category options shown in the dropdown.
# Add or remove entries here to update the dropdown options.
# "Other" is automatically appended as the last option.
CATEGORIES = [
    "Eating Out/Drinks",
    "Subscriptions",
    "Groceries",
    "Entertainment",
    "Health/Medical",
    "Utilities",
    "Rent/Mortgage",
    "Transportation",
    "Miscellaneous"
]


def render_add_transaction(account_names: dict) -> None:
    """
    Entry point for the Add Transaction page.

    Reads the current step from session state and delegates to the
    appropriate sub-renderer.

    Args:
        account_names: Dict of {account_name: account_id} from load_account_names().
    """
    st.title("Add Transaction")

    step = st.session_state.get("add_txn_step", "form")

    if step == "form":
        _render_form(account_names)
    elif step == "confirm":
        _render_confirmation()


def _render_form(account_names: dict) -> None:
    """
    Render the transaction input form (Step 1).

    On submit, validates that Vendor Name is filled, then stores the
    transaction dict in session state and advances to the confirm step.

    Layout: two columns
      Left  — Date, Account, Transaction Type, Vendor
      Right — Amount, Expense Category, (Other specify), Check Number, Notes

    Debug tip: If the Account dropdown is empty, account_names is {} —
    see load_account_names() in data/loader.py for RLS debugging steps.

    Debug tip: The "If Other, specify" text box is always visible but its
    value is only used when "Other" is selected in the category dropdown.
    This is intentional — st.form does not support dynamic widget toggling.
    """
    with st.form("add_transaction_form", border=True):
        col1, col2 = st.columns(2)

        with col1:
            txn_date = st.date_input("Transaction Date", value=date.today())
            account  = st.selectbox("Account", options=list(account_names.keys()))
            txn_type = st.selectbox("Transaction Type", options=TRANSACTION_TYPES)
            vendor   = st.text_input("Vendor Name")

        with col2:
            amount          = st.number_input("Amount", step=0.01, format="%.2f",
                                              help="Use negative values for debits/expenses.")
            category_select = st.selectbox("Expense Category (optional)", options=[""] + CATEGORIES + ["Other"])
            category_other  = st.text_input("If Other, specify:", help="Only used when 'Other' is selected above.")
            check_number    = st.text_input("Check Number (optional)")
            notes           = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Review Transaction", use_container_width=True, type="primary")

    if submitted:
        if not vendor:
            st.error("Vendor Name is required.")
            return

        # Resolve the category value:
        #   - "Other" selected → use the free-text field (or None if blank)
        #   - predefined option selected → use it directly
        #   - blank ("") selected → store None
        resolved_category = (
            (category_other.strip() or None)
            if category_select == "Other"
            else (category_select or None)
        )

        st.session_state["pending_transaction"] = {
            "transaction_date": txn_date.isoformat(),
            "account_id":       account_names[account],  # integer FK for DB
            "account_name":     account,                  # display only — stripped before insert
            "transaction_type": txn_type,
            "vendor_name":      vendor,
            "amount":           amount,
            "category":         resolved_category,
            "check_number":     check_number or None,
            "notes":            notes or None,
            "user_id":          st.session_state.get("user_id"),
        }
        st.session_state["add_txn_step"] = "confirm"
        st.rerun()


def _render_confirmation() -> None:
    """
    Render the confirmation screen (Step 2).

    Reads the pending transaction from session state and displays it as
    metric cards split across two columns. The user can confirm (insert to DB)
    or go back to edit.

    On confirm:
      - "account_name" is stripped from the dict before inserting (it is a
        display-only field not present in fct_transactions)
      - The load_transactions cache is cleared so the dashboard reflects the
        new row immediately on return
      - Session state is cleaned up and the step resets to "form"

    Debug tip: If saving fails with a database error, the full error message
    is shown via st.error(). Common causes:
      - FK violation: account_id not found in dim_accounts
      - RLS violation: INSERT policy missing in Supabase
      - Type mismatch: amount stored as string instead of float
    """
    st.subheader("Confirm Transaction")
    st.write("Review the details below before saving to the database.")

    txn = st.session_state.get("pending_transaction", {})

    # Maps DB/session keys → human-readable display labels
    # Note: account_id is not shown; account_name is used for display instead
    labels = {
        "transaction_date": "Date",
        "account_name":     "Account",
        "transaction_type": "Transaction Type",
        "vendor_name":      "Vendor",
        "amount":           "Amount",
        "category":         "Expense Category",
        "check_number":     "Check Number",
        "notes":            "Notes",
    }

    col1, col2 = st.columns(2)
    items = [(labels[k], txn.get(k)) for k in labels]
    half  = len(items) // 2

    with col1:
        for label, value in items[:half]:
            st.metric(label, value if value is not None else "—")

    with col2:
        for label, value in items[half:]:
            formatted = f"${value:,.2f}" if label == "Amount" and value is not None else (value or "—")
            st.metric(label, formatted)

    st.divider()
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Confirm & Save", type="primary", use_container_width=True):
            try:
                # Strip display-only key before inserting into the database
                insert_transaction({k: v for k, v in txn.items() if k != "account_name"})
                load_transactions.clear()   # force dashboard to reload with new row
                st.session_state.pop("pending_transaction", None)
                st.session_state["add_txn_step"] = "form"
                st.success("Transaction saved successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save transaction: {e}")

    with btn_col2:
        if st.button("Go Back & Edit", use_container_width=True):
            st.session_state["add_txn_step"] = "form"
            st.rerun()
