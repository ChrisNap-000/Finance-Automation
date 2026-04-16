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


def render_add_transaction(account_names: list) -> None:
    st.title("Add Transaction")

    step = st.session_state.get("add_txn_step", "form")

    if step == "form":
        _render_form(account_names)
    elif step == "confirm":
        _render_confirmation()


def _render_form(account_names: list) -> None:
    with st.form("add_transaction_form", border=True):
        col1, col2 = st.columns(2)

        with col1:
            txn_date     = st.date_input("Transaction Date", value=date.today())
            account      = st.selectbox("Account", options=account_names)
            txn_type     = st.selectbox("Transaction Type", options=TRANSACTION_TYPES)
            vendor       = st.text_input("Vendor Name")

        with col2:
            amount       = st.number_input("Amount", step=0.01, format="%.2f",
                                           help="Use negative values for debits/expenses.")
            category     = st.text_input("Category")
            check_number = st.text_input("Check Number (optional)")
            notes        = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Review Transaction", use_container_width=True, type="primary")

    if submitted:
        if not vendor:
            st.error("Vendor Name is required.")
            return

        st.session_state["pending_transaction"] = {
            "TRANSACTION_DATE": txn_date.isoformat(),
            "ACCOUNT":          account,
            "TRANSACTION_TYPE": txn_type,
            "VENDOR_NAME":      vendor,
            "AMOUNT":           amount,
            "CATEGORY":         category or None,
            "CHECK_NUMBER":     check_number or None,
            "NOTES":            notes or None,
            "USER_ID":          st.session_state.get("user_id"),
        }
        st.session_state["add_txn_step"] = "confirm"
        st.rerun()


def _render_confirmation() -> None:
    st.subheader("Confirm Transaction")
    st.write("Review the details below before saving to the database.")

    txn = st.session_state.get("pending_transaction", {})

    labels = {
        "TRANSACTION_DATE": "Date",
        "ACCOUNT":          "Account",
        "TRANSACTION_TYPE": "Transaction Type",
        "VENDOR_NAME":      "Vendor",
        "AMOUNT":           "Amount",
        "CATEGORY":         "Category",
        "CHECK_NUMBER":     "Check Number",
        "NOTES":            "Notes",
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
                insert_transaction(txn)
                load_transactions.clear()
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
