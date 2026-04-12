import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_monthly_cashflow(filtered_df):
    st.subheader("Monthly Net Cash Flow")

    df = filtered_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    paycheck_counts = (
        df.loc[df["Description"] == "LevelUP Payroll"]
        .groupby("Month")
        .size()
        .reset_index(name="Paycheck Count")
    )
    paycheck_counts["Paycheck Count"] = paycheck_counts["Paycheck Count"] / 2

    def monthly_net(group):
        income = group.loc[group["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
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
