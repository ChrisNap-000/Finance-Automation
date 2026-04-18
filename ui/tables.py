# =============================================================================
# ui/tables.py — Dashboard table components
#
# Three table components used on the Dashboard page:
#
#   render_pnl_breakdown()    — pivot table grouped by Account/Type/Vendor
#                               with monthly columns and a Total column
#   render_transactions_table() — raw transaction list, newest first
#   render_pnl_download()     — full pivot table shown at the bottom for export
# =============================================================================

import streamlit as st


def render_pnl_breakdown(filtered_df):
    """
    Render an expandable PnL pivot table grouped by Account and Transaction Type.

    Only transactions with PnL_flag == True are included (CC payments and
    internal transfers are excluded — see data/transforms.py).

    Structure:
      - One st.expander per account
      - Inside each expander: one section per transaction type
      - Each section shows a subtotal row by default, with a checkbox to
        expand the per-vendor detail rows

    Pivot columns: one column per calendar month (e.g. "Jan-2026") in
    chronological order, plus a "Total" column on the right.

    Args:
        filtered_df: Filtered and transformed DataFrame from Finance_App.py.

    Returns:
        pivoted_df: The full pivot table DataFrame, passed to render_pnl_download().

    Debug tip: If a month column is missing, it means no PnL_flag=True transactions
    exist for that month under the current filters. Adjust Year/Month filters.
    """
    st.subheader("PNL Breakdown by Account and Transaction Type")

    source = filtered_df[filtered_df["PnL_flag"] == True].copy()
    source["Month-Year-Period"] = source["Date"].dt.to_period("M")
    source["Month-Year"]        = source["Month-Year-Period"].dt.strftime("%b-%Y")
    source = source.sort_values("Month-Year-Period")

    # Build chronological month order for column sorting
    month_year_order = (
        source.drop_duplicates("Month-Year-Period")
        .sort_values("Month-Year-Period")["Month-Year"]
        .tolist()
    )

    pivoted_df = source.pivot_table(
        index=["Account", "Transaction Type", "Vendor"],
        columns="Month-Year",
        values="Amount",
        aggfunc="sum",
        margins=True,           # adds the "Total" row/column
        margins_name="Total"
    ).fillna(0)

    # Reorder columns chronologically (pivot_table may not preserve order)
    cols = [col for col in month_year_order if col in pivoted_df.columns]
    if "Total" in pivoted_df.columns:
        cols.append("Total")
    pivoted_df = pivoted_df.reindex(columns=cols)

    # Render one expander per account
    for account in pivoted_df.index.get_level_values(0).unique():
        account_df = pivoted_df.xs(account, level=0, drop_level=False)

        with st.expander(f"Account: {account}", expanded=True):
            for txn_type in account_df.index.get_level_values(1).unique():
                txn_df = account_df.xs(txn_type, level=1, drop_level=False)

                # Show the subtotal row (sum across all vendors for this type)
                subtotal = txn_df.sum(numeric_only=True).to_frame().T
                st.markdown(f"**Transaction Type: {txn_type} (Subtotal)**")
                st.dataframe(subtotal.style.format("${:,.2f}"))

                # Optional detail view (per-vendor breakdown)
                show_details = st.checkbox(
                    f"Show details for {txn_type}",
                    key=f"{account}_{txn_type}_details"
                )

                if show_details:
                    detail_df = txn_df.droplevel([0, 1])
                    st.dataframe(detail_df.style.format("${:,.2f}"))

    return pivoted_df


def render_transactions_table(filtered_df):
    """
    Render the full transactions list as a sortable dataframe, newest first.

    Displays: Date, Account, Transaction Type, Vendor, Category,
              Check Number, Amount, Notes, PnL_flag

    Date is formatted as MM-DD-YYYY for readability.
    Amount is formatted with a dollar sign and commas.

    Debug tip: Use this table to verify that transactions were inserted
    correctly and to spot unexpected PnL_flag values.
    """
    st.subheader("Transactions")

    display_df = filtered_df[[
        "Date", "Account", "Transaction Type", "Vendor",
        "Category", "Check Number", "Amount", "Notes", "PnL_flag"
    ]].copy()

    display_df["Date"] = display_df["Date"].dt.strftime("%m-%d-%Y")

    st.dataframe(
        display_df.sort_values("Date", ascending=False)
        .reset_index(drop=True)
        .style.format({"Amount": "${:,.2f}"}),
        use_container_width=True
    )


def render_pnl_download(pivoted_df):
    """
    Render the full PnL pivot table at the bottom of the dashboard for export.

    This shows the same data as render_pnl_breakdown() but as a single flat
    table, which makes it easy to copy or export to Excel.

    Args:
        pivoted_df: The DataFrame returned by render_pnl_breakdown().
    """
    st.subheader("PNL Breakdown Download")
    st.dataframe(pivoted_df.style.format("${:,.2f}"), use_container_width=True)
