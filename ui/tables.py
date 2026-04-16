import streamlit as st


def render_pnl_breakdown(filtered_df):
    st.subheader("PNL Breakdown by Account and Transaction Type")

    source = filtered_df[filtered_df["PnL_flag"] == True].copy()
    source["Month-Year-Period"] = source["Date"].dt.to_period("M")
    source["Month-Year"]        = source["Month-Year-Period"].dt.strftime("%b-%Y")
    source = source.sort_values("Month-Year-Period")

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
        margins=True,
        margins_name="Total"
    ).fillna(0)

    cols = [col for col in month_year_order if col in pivoted_df.columns]
    if "Total" in pivoted_df.columns:
        cols.append("Total")
    pivoted_df = pivoted_df.reindex(columns=cols)

    for account in pivoted_df.index.get_level_values(0).unique():
        account_df = pivoted_df.xs(account, level=0, drop_level=False)

        with st.expander(f"Account: {account}", expanded=True):
            for txn_type in account_df.index.get_level_values(1).unique():
                txn_df = account_df.xs(txn_type, level=1, drop_level=False)

                subtotal = txn_df.sum(numeric_only=True).to_frame().T
                st.markdown(f"**Transaction Type: {txn_type} (Subtotal)**")
                st.dataframe(subtotal.style.format("${:,.2f}"))

                show_details = st.checkbox(
                    f"Show details for {txn_type}",
                    key=f"{account}_{txn_type}_details"
                )

                if show_details:
                    detail_df = txn_df.droplevel([0, 1])
                    st.dataframe(detail_df.style.format("${:,.2f}"))

    return pivoted_df


def render_transactions_table(filtered_df):
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
    st.subheader("PNL Breakdown Download")
    st.dataframe(pivoted_df.style.format("${:,.2f}"), use_container_width=True)
