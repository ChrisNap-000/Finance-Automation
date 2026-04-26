import pandas as pd
import streamlit as st
from streamlit_pivot import st_pivot_table, PivotStyle, RegionStyle

from config import INVESTMENT_ACCOUNTS


def render_pnl_breakdown(filtered_df, all_account_names: dict):
    """
    Render the PnL breakdown as an interactive pivot table.

    Row hierarchy: Account → Transaction Type → Category → Vendor
    Columns: one per MMM-YYYY month period present in the filtered data.
    Values: sum of Amount.

    Only PnL_flag=True transactions are included.

    Args:
        filtered_df:       Filtered and transformed DataFrame from Finance_App.py.
        all_account_names: Dict {account_name: id} from load_account_names().

    Returns:
        vendor_piv: Vendor-level pivot DataFrame passed to render_pnl_download().
    """
    st.subheader("PNL Breakdown")

    source = filtered_df[filtered_df["PnL_flag"] == True].copy()
    source["Category"] = source["Category"].fillna("Uncategorized")

    if source.empty:
        st.info("No PnL data for the current filter selection.")
        return pd.DataFrame()

    source["_period"]    = source["Date"].dt.to_period("M")
    source               = source.dropna(subset=["_period"])
    source["Month-Year"] = source["_period"].dt.strftime("%b-%Y")

    months = (
        source.drop_duplicates("_period")
        .sort_values("_period")["Month-Year"]
        .tolist()
    )

    pivot_data = source[
        ["Account", "Transaction Type", "Category", "Vendor", "Month-Year", "Amount"]
    ].copy()

    st_pivot_table(
        pivot_data,
        key="pnl_breakdown",
        rows=["Account", "Transaction Type", "Category", "Vendor"],
        columns=["Month-Year"],
        values=["Amount"],
        aggregation="sum",
        show_subtotals=True,
        row_layout="hierarchy",
        show_totals=True,
        sorters={"Month-Year": months},
        number_format="$,.2f",
        locked=True,
        hidden_from_aggregators=["Account", "Transaction Type", "Category", "Vendor"],
        style=PivotStyle(
            background_color="#0D1117",
            column_header=RegionStyle(
                background_color="#21262D",
                text_color="#C9D1D9",
                font_weight="bold",
            ),
            # Subtotal region covers Account, Transaction Type, and Category rows
            # (any row that is a parent in the hierarchy).
            subtotal=RegionStyle(
                background_color="#1C2128",
                text_color="#C9D1D9",
                font_weight="bold",
            ),
            # row_header covers the label cells for detail (Vendor) rows.
            row_header=RegionStyle(
                background_color="#161B22",
                text_color="#8B949E",
            ),
            data_cell=RegionStyle(
                background_color="#0D1117",
                text_color="#C9D1D9",
            ),
            # Grand total row/column uses the app's green accent.
            row_total=RegionStyle(
                background_color="#0f2a1a",
                text_color="#3fb950",
                font_weight="bold",
            ),
            column_total=RegionStyle(
                background_color="#0f2a1a",
                text_color="#3fb950",
                font_weight="bold",
            ),
        ),
    )

    # Build vendor_piv for the download section
    vendor_piv = (
        source.pivot_table(
            index=["Account", "Transaction Type", "Category", "Vendor"],
            columns="Month-Year",
            values="Amount",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(columns=months, fill_value=0)
    )
    vendor_piv["Total"] = vendor_piv[months].sum(axis=1)

    return vendor_piv


def render_transactions_table(filtered_df):
    """
    Render the full transactions list as a sortable dataframe, newest first.

    Displays: Date, Account, Transaction Type, Vendor, Category,
              Check Number, Amount, Notes, PnL_flag

    Date is formatted as MM-DD-YYYY for readability.
    Amount is formatted with a dollar sign and commas.
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
    Render the full vendor-level PnL pivot table for export.

    Args:
        pivoted_df: The DataFrame returned by render_pnl_breakdown().
    """
    st.subheader("PNL Breakdown Download")
    if pivoted_df.empty:
        st.info("No PnL data to display.")
        return
    st.dataframe(pivoted_df.style.format("${:,.2f}"), use_container_width=True)
