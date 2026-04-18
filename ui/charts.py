# =============================================================================
# ui/charts.py — Plotly chart components for the dashboard
#
# Currently contains one chart: Monthly Net Cash Flow bar chart.
# Each bar represents one calendar month and shows net cash flow
# (income minus spending). Paycheck count is overlaid as bar text.
# =============================================================================

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_monthly_cashflow(filtered_df):
    """
    Render an interactive Plotly bar chart of monthly net cash flow.

    Each bar = one calendar month. Bar height = total income - total spending
    for that month. Bar label = number of paychecks received (LevelUp vendor,
    divided by 2 because each paycheck appears as two transactions).

    Hover tooltip shows: Month, Net Cash Flow ($), Paycheck count.

    Args:
        filtered_df: Filtered transactions DataFrame. Must have columns:
                     Date, Vendor, Transaction Type, Amount.

    Notes:
      - The paycheck vendor filter looks for "LEVELUP" (case-insensitive) in
        the Vendor column. Update the string if the vendor name changes.
      - Dividing paycheck count by 2 assumes each paycheck generates exactly
        2 transactions. Adjust if your payroll structure differs.
      - Net Cash Flow only counts "Interest"/"Income" and "Expense" types —
        Transfers, CC Payments, etc. are excluded (same logic as render_kpis).

    Debug tip: If paycheck counts look wrong, inspect the Vendor column for
    LEVELUP rows and check for duplicate or missing entries per paycheck.
    """
    st.subheader("Monthly Net Cash Flow")

    df = filtered_df.copy()
    df["Date"]  = pd.to_datetime(df["Date"], errors="coerce")

    # Convert to start-of-month timestamp for clean grouping and sorting
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    # Count paycheck transactions per month (2 transactions per paycheck)
    paycheck_counts = (
        df.loc[df["Vendor"].str.contains("LEVELUP", case=False, na=False)]
        .groupby("Month")
        .size()
        .reset_index(name="Paycheck Count")
    )
    paycheck_counts["Paycheck Count"] = paycheck_counts["Paycheck Count"] / 2

    def monthly_net(group):
        """Sum income minus spending for a single month group."""
        income   = group.loc[group["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
        spending = group.loc[group["Transaction Type"].isin(["Expense"]), "Amount"].sum()
        return income + spending

    monthly = (
        df.groupby("Month")
        .apply(monthly_net)
        .reset_index(name="Net Cash Flow")
    )

    monthly["MonthStr"] = monthly["Month"].dt.strftime("%b %Y")
    monthly = monthly.merge(paycheck_counts, on="Month", how="left")
    monthly = monthly.sort_values("Month")

    fig = go.Figure(
        data=[
            go.Bar(
                x=monthly["MonthStr"].tolist(),
                y=monthly["Net Cash Flow"].tolist(),
                text=monthly["Paycheck Count"].astype(str).tolist(),
                textposition="outside",
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Net Cash Flow: $%{y:,.2f}<br>"
                    "Paychecks: %{text}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Net Cash Flow",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f"
    )
    st.plotly_chart(fig, use_container_width=True)
