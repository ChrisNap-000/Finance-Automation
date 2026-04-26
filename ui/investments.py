import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.loader import load_investment_balances

# Order matches user spec: Vanguard=6, Schwab=5, Retirement=7
INVESTMENT_ACCOUNTS = [(6, "Vanguard"), (5, "Schwab"), (7, "Retirement")]
ACCOUNT_COLORS      = {5: "#17923c", 6: "#4C9BE8", 7: "#E8A24C"}


def _compute_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each account's full balance history, compute MoM and YoY $ and % changes.
    Adds columns: mom_dollar, mom_pct, yoy_dollar, yoy_pct
    """
    results = []
    for account_id, _ in INVESTMENT_ACCOUNTS:
        acct = df[df["account_id"] == account_id].sort_values("recorded_date").copy()
        if acct.empty:
            continue

        acct["period"] = acct["recorded_date"].dt.to_period("M")

        # MoM: compare each row to the previous row
        acct["prev_mom"]   = acct["balance"].shift(1)
        acct["mom_dollar"] = acct["balance"] - acct["prev_mom"]
        acct["mom_pct"]    = acct["mom_dollar"] / acct["prev_mom"] * 100

        # YoY: compare each row to the same calendar month one year prior
        period_to_bal = dict(zip(acct["period"], acct["balance"]))
        acct["prev_yoy"]   = acct["period"].apply(lambda p: period_to_bal.get(p - 12))
        acct["yoy_dollar"] = acct["balance"] - acct["prev_yoy"]
        acct["yoy_pct"]    = acct["yoy_dollar"] / acct["prev_yoy"] * 100

        results.append(acct)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def _fmt(val, show_pct: bool) -> str:
    if pd.isna(val):
        return "N/A"
    if show_pct:
        return f"{val:+.2f}%"
    sign = "+" if val >= 0 else "-"
    return f"{sign}${abs(val):,.0f}"


def _render_line_chart(df: pd.DataFrame, change_type: str, show_pct: bool) -> None:
    y_col   = f"{change_type}_pct"   if show_pct else f"{change_type}_dollar"
    y_label = "% Change"             if show_pct else "$ Change"
    title   = "Month-over-Month Change" if change_type == "mom" else "Year-over-Year Change"

    fig = go.Figure()

    for account_id, account_name in INVESTMENT_ACCOUNTS:
        acct = (
            df[df["account_id"] == account_id]
            .sort_values("recorded_date")
            .dropna(subset=[y_col])
        )
        if acct.empty:
            continue

        x = acct["recorded_date"].dt.strftime("%b %Y").tolist()
        y = acct[y_col].tolist()

        if show_pct:
            hover = (f"<b>{account_name}</b><br>%{{x}}<br>"
                     "Change: %{y:+.2f}%<extra></extra>")
        else:
            hover = (f"<b>{account_name}</b><br>%{{x}}<br>"
                     "Change: $%{y:+,.0f}<extra></extra>")

        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines+markers",
            name=account_name,
            line=dict(color=ACCOUNT_COLORS[account_id], width=2),
            hovertemplate=hover,
        ))

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title=y_label,
        yaxis_ticksuffix="%" if show_pct else "",
        yaxis_tickprefix="" if show_pct else "$",
        yaxis_tickformat=".1f" if show_pct else ",.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    st.subheader(title)
    st.plotly_chart(fig, use_container_width=True)


def render_investments(access_token: str, year_select=None, month_select=None) -> None:
    df_raw = load_investment_balances(access_token)

    if df_raw.empty:
        st.markdown(
        '<div style="background-color:rgba(23,146,60,0.09);border-left:4px solid #17923c;'
        'border-radius:4px;padding:0.75rem 1rem;color:#17923c;font-size:0.95rem;">'
        "No investment balance history found. Add balance snapshots in dim_starting_balances.<div>",
        unsafe_allow_html=True,
        )
        return

    df = _compute_changes(df_raw)

    # Apply year/month filters from the sidebar (compute changes on full history first)
    if year_select:
        df = df[df["recorded_date"].dt.year.isin(year_select)]
    if month_select:
        month_nums = [list(calendar.month_name).index(m) for m in month_select]
        df = df[df["recorded_date"].dt.month.isin(month_nums)]

    # Toggle button
    if "inv_show_pct" not in st.session_state:
        st.session_state["inv_show_pct"] = False

    show_pct = st.session_state["inv_show_pct"]

    btn_col, _ = st.columns([2, 5])
    with btn_col:
        label = "Showing: $ Change  —  Switch to %" if not show_pct else "Showing: % Change  —  Switch to $"
        if st.button(label, use_container_width=True):
            st.session_state["inv_show_pct"] = not show_pct

    st.divider()

    # Per-account KPIs — one column per account
    cols = st.columns(len(INVESTMENT_ACCOUNTS))
    for col, (account_id, account_name) in zip(cols, INVESTMENT_ACCOUNTS):
        acct = df[df["account_id"] == account_id].sort_values("recorded_date")
        if acct.empty:
            continue
        latest = acct.iloc[-1]

        mom_val = latest["mom_pct"   if show_pct else "mom_dollar"]
        yoy_val = latest["yoy_pct"   if show_pct else "yoy_dollar"]

        with col:
            st.subheader(account_name)
            st.metric("Current Balance", f"${latest['balance']:,.2f}")
            st.metric("MoM Change",      _fmt(mom_val, show_pct))
            st.metric("YoY Change",      _fmt(yoy_val, show_pct))

    st.divider()

    # Line charts — one per change type, all accounts on same chart
    _render_line_chart(df, "mom", show_pct)
    _render_line_chart(df, "yoy", show_pct)
