# ---------------------------
# IMPORT LIBRARIES
# ---------------------------
import calendar
import numpy as np
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Set the page
st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

# ---------------------------
# CREATE PASSWORD PROTECTION
# ---------------------------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.sidebar.header("🔒 Login")

    password = st.sidebar.text_input(
        "Enter password",
        type="password"
    )

    if st.sidebar.button("Login"):
        if password == st.secrets["STREAMLIT_APP_PASSWORD"]:
            st.session_state.authenticated = True
            #st.experimental_rerun()
        else:
            st.sidebar.error("Incorrect password")

    return False

# Check password
if not check_password():
    st.stop()

# ---------------------------
# CREATE STREAMLIT APP
# ---------------------------

# Create sidebar
st.sidebar.header("Upload Data Files")

# Upload transaction file input
transactions_file = st.sidebar.file_uploader("Upload Transactions CSV", type=["csv"])
# Upload lookup file input
lookup_file = st.sidebar.file_uploader("Upload Account Lookup XLSX", type=["xlsx"])

# Guard clause: wait until both files are uploaded
if not transactions_file or not lookup_file:
    st.info("Please upload both CSV files to continue.")
    st.stop()

# ---------------------------
# READ TRANSACTIONS AND CAPTURE BAD ROWS
# ---------------------------
# Initalize empty list to hold bad rows
bad_rows = []

# Define function to handle bad lines
def handle_bad_line(row):
    bad_rows.append(row)
    return None  # skip it

# Read the transaction CSV
df_main = pd.read_csv(
    transactions_file,
    engine="python",
    quotechar='"',
    on_bad_lines=handle_bad_line,
    parse_dates=["Date"]
)

# Convert bad rows into DataFrame
df_bad = pd.DataFrame(bad_rows)

# Handle bad rows if any
if not df_bad.empty:
    # If Description was split due to a comma, combine
    if 5 in df_bad.columns:
        df_bad[4] = df_bad[4].astype(str) + "," + df_bad[5].astype(str)
        df_bad = df_bad.drop(columns=[5])

    # Rename columns in bad rows dataframe
    columns = {
        0:"Date",
        1:"Bank RTN",
        2:"Account Number",
        3:"Transaction Type",
        4:"Description",
        6:"Debit",
        7:"Credit",
        8:"Check Number",
        9:"Account Running Balance"
    }
    # Rename the columns
    df_bad = df_bad.rename(columns=columns)

    # Append bad rows to main dataframe
    df_main = pd.concat([df_main, df_bad], ignore_index=True)

# ---------------------------
# CLEAN BLANKS AND CONVERT TYPES
# ---------------------------
# Convert blanks to nulls in main dataframe
for col in ["Date", "Bank RTN", "Account Number", "Transaction Type",
            "Description", "Debit", "Credit", "Check Number", "Account Running Balance"]:
    if col in df_main.columns:
        df_main[col] = df_main[col].replace("", np.nan)

# Convert numeric columns safely
for col in ["Debit", "Credit", "Account Running Balance"]:
    if col in df_main.columns:
        df_main[col] = pd.to_numeric(df_main[col].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce")

# Convert Date
if "Date" in df_main.columns:
    df_main["Date"] = pd.to_datetime(df_main["Date"], errors="coerce")

# ---------------------------
# READ LOOKUP FILE AND JOIN
# ---------------------------
# Read the lookup Excel file
df_lookup = pd.read_excel(lookup_file)

# Convert account number to string in main df for join
df_main['Account Number'] = df_main['Account Number'].astype('string')

# Convert account number to a string for join
df_lookup["Account Number"] = df_lookup["Account Number"].astype("string")

# Left join on Account Number
df = df_main.merge(df_lookup, how="left", on="Account Number")

# ---------------------------
# REQUIRED TRANSFORMATIONS
# ---------------------------

# Convert blanks to nulls
for i in columns.values():
    df[i] = df[i].replace('', np.nan)

# Define Data Types
data_types = {
    "Date": "datetime64[ns]",
    "Bank RTN": "string",
    "Account Number": "string",
    "Transaction Type": "string",
    "Description": "string",
    "Debit": "float64",
    "Credit": "float64",
    "Check Number": "string",
    "Account Running Balance": "float64"
}
# Apply Data Types
df = df.astype(data_types)

# Drop Unessessary Columns
df = df.drop(columns=["Bank RTN"])

# Coalesce Debit and Credit into Amount
df["Debit"] = df["Debit"].fillna(0)
df["Credit"] = df["Credit"].fillna(0)
df["Amount"] = df["Credit"] - df["Debit"]

# Drop Debit and Credit Columns
df = df.drop(columns=["Debit", "Credit"])

# Wildcard changes in Description column
desc_patterns = {
    r'.*AMAZON.*': 'Amazon',
    r'.*SJU.*': 'SJU Payroll',
    r'.*LEVELUP.*': 'LevelUP Payroll',
    r'.*DUNKIN.*': 'Dunkin',
    r'.*PLANET FITNESS.*': 'Planet Fitness'
}

# Apply replacements in Description column
df['Description'] = df['Description'].replace(
    desc_patterns,
    regex=True
)

# Wildcard Changes in Transaction Type column
trans_type_patterns = {
    r'.*CREDIT.*': 'Income',
    r'.*DEBIT.*': 'Expense',
    r'.*DEP.*': 'Deposit',
    r'.*DIRECTDEBIT.*': 'Expense',
    r'.*INT.*': 'Interest',
    r'.*XFER.*': 'Transfer'
}

# Apply replacements in Transaction Type column
df['Transaction Type'] = df['Transaction Type'].replace(
    trans_type_patterns,
    regex=True
)

# Categorize withdrawls descriptions as withdraws in transaction type
df['Transaction Type'] = np.where(
    (df['Description'].str.contains('WITHDRAWAL', case=False, na=False)),
    'Withdrawal',
    df['Transaction Type']
)

# If transaction type is null, set to Expense if Amount < 0
df.loc[(df['Transaction Type'].isna()) & (df['Amount'] < 0) & (df['Account Name'] == "Credit Card"), 'Transaction Type'] = 'Expense'

# If transaction type is null, set to CC Payments if Amount > 0
df.loc[(df['Transaction Type'].isna()) & (df['Amount'] > 0) & (df['Account Name'] == "Credit Card"), 'Transaction Type'] = 'CC Payment'

# Make Include In PNL Flag
def pnl_flag (df):
 # Default: include everything
    df["PnL_flag"] = True

    # Exclude credit card payments (liability paydowns)
    df.loc[
        (df["Account Name"] == "Credit Card") & (df["Amount"] > 0),
        "PnL_flag"
    ] = False

    # Exclude transfers between own accounts
    df.loc[
        (df["Transaction Type"].str.upper() == "TRANSFER") &
        (df["Description"].str.upper() == "ONLINE XFER TRANSFER TO CC X2491"),
        "PnL_flag"
    ] = False

pnl_flag(df)

# Add Year and Month Columns
df['Year'] = df['Date'].apply(lambda d: d.year)
df['MonthNum'] = df['Date'].apply(lambda d: d.month)
df['Month'] = df['MonthNum'].apply(lambda m: calendar.month_name[m])
df.drop(columns=['MonthNum'], inplace=True)

# ---------------------------
# SIDEBAR FILTERS
# ---------------------------
# Sidebar Header
st.sidebar.header("Filters")

# Define Default values for reset filters
DEFAULT_YEAR = list({int(df['Year'].max())})
DEFAULT_MONTH = df['Month'].unique().tolist()
DEFAULT_TRANSACTIONS = df['Transaction Type'].unique().tolist()

# Initalize Session state
if "year" not in st.session_state:
    st.session_state.year = DEFAULT_YEAR
if "month" not in st.session_state:
    st.session_state.month = DEFAULT_MONTH
if "transaction_type" not in st.session_state:
    st.session_state.transaction_type = DEFAULT_TRANSACTIONS

# Define reset function
def reset_filters():
    st.session_state.year = DEFAULT_YEAR
    st.session_state.month = DEFAULT_MONTH
    st.session_state.transaction_type = DEFAULT_TRANSACTIONS

# Add Reset Button
st.sidebar.button("🔄 Reset Filters", on_click=reset_filters)

# !!!!Uncomment if you want date range filter!!!!
# date_range = st.sidebar.date_input(
#     "Date Range",
#     [df["Date"].min(), df["Date"].max()]
# )

# Create filters in sidebar
year_select = st.sidebar.multiselect(
    "Year",
    options=sorted(df["Year"].unique()),
    key="year"
)

month_select = st.sidebar.multiselect(
    "Month",
    options= list(calendar.month_name)[1:],
    key="month"
)

txn_types = st.sidebar.multiselect(
    "Transaction Type",
    options=df["Transaction Type"].unique(),
    key='transaction_type'
)

# ---------------------------
# APPLY FILTERS
# ---------------------------
# Create a new dataframe that respects the filters from sidebar
filtered_df = df[
    #(df["Date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))) &
    (df["Year"].isin(year_select)) &
    (df["Month"].isin(month_select)) &
    (df["Transaction Type"].isin(txn_types))
]

# ---------------------------
# KPIS
# ---------------------------
# Calculate Income, Spending, and Net
income = filtered_df.loc[filtered_df["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
spending = filtered_df.loc[filtered_df["Transaction Type"].isin(["Expense"]), "Amount"].sum()
net = income + spending  # spending is negative

# Store the account names we want balances for
accs = ["Checking", "Savings", "CD"]

# Loop through and retrieve ending balances and store in a dictionary - Account names are keys
ending_balances = {
    acc: (
        filtered_df.loc[df["Account Name"] == acc]
          .loc[lambda x: x["Date"] == x["Date"].max(), "Account Running Balance"]
          .mean()
    )
    for acc in accs
}

# Calculate total balance across accounts
checkingBalance = ending_balances["Checking"]
savingsBalance = ending_balances["Savings"]
cdBalance = ending_balances["CD"]
# Calculate total balance
total_balance = checkingBalance + savingsBalance + cdBalance

# Display KPIs in three rows of three columns
spacer, row1_col2, spacer2 = st.columns(3)
row2_col1, row2_col2, row2_col3 = st.columns(3)
row3_col1, row3_col2, row3_col3 = st.columns(3)

row1_col2.metric("Total Balance", f"${total_balance:,.2f}")

row2_col1.metric("Income", f"${income:,.2f}")
row2_col2.metric("Spending", f"${spending:,.2f}")
row2_col3.metric("Net Cash Flow", f"${net:,.2f}")

row3_col1.metric("Checking Balance", f"${checkingBalance:,.2f}")
row3_col2.metric("Savings Balance", f"${savingsBalance:,.2f}")
row3_col3.metric("CD Balance", f"${cdBalance:,.2f}")
# ---------------------------
# MONTHLY CASH FLOW
# ---------------------------
# Create a Month column as datetime (first day of the month)
filtered_df["Month"] = filtered_df["Date"].dt.to_period("M").dt.to_timestamp()

# Define a function to compute net for a group
def monthly_net(group):
    income1 = group.loc[group["Transaction Type"].isin(["Interest", "Income"]), "Amount"].sum()
    spending = group.loc[group["Transaction Type"].isin(["Expense"]), "Amount"].sum()
    return income1 + spending

# Group by Month and calculate net cash flow
monthly = (
    filtered_df
    .groupby("Month")
    .apply(monthly_net)
    .reset_index(name='Net Cash Flow')
)

# Convert to string for nicer x-axis labels
monthly["MonthStr"] = monthly["Month"].dt.strftime("%b %Y")  # e.g., "Jan 2026"

# Sort chronologically
monthly = monthly.sort_values("Month")

# Create bar chart using Plotly
fig_cashflow = px.bar(
    monthly,
    x="Month",
    y="Net Cash Flow",
    title="Monthly Net Cash Flow"
)

# Update x-axis to show MonthStr
st.plotly_chart(fig_cashflow, use_container_width=True)

# ---------------------------
# PNL BREAKDOWN
# ---------------------------
# Create copy of filtered df for pivoting
pivoted_source = filtered_df[filtered_df["PnL_flag"] == True].copy()
# Create a Month-Year column as period for sorting, and a string for display
pivoted_source['Month-Year-Period'] = pivoted_source['Date'].dt.to_period('M')
pivoted_source['Month-Year'] = pivoted_source['Month-Year-Period'].dt.strftime("%b-%Y")

# Sort by Month-Year-Period so columns will be in chronological order
pivoted_source = pivoted_source.sort_values('Month-Year-Period')

# Get unique Month-Year values in chronological order for columns
month_year_order = pivoted_source.drop_duplicates('Month-Year-Period').sort_values('Month-Year-Period')['Month-Year'].tolist()

# Create pivot table
pivoted_df = pivoted_source.pivot_table(
    index=['Account Name', 'Transaction Type', 'Description'],
    columns='Month-Year',
    values='Amount',
    aggfunc='sum',
    margins=True,
    margins_name="Total"
).fillna(0)

# Reindex columns to enforce chronological order (except 'Total' which stays at the end)
cols = [col for col in month_year_order if col in pivoted_df.columns]
if 'Total' in pivoted_df.columns:
    cols.append('Total')
pivoted_df = pivoted_df.reindex(columns=cols)

# Display breakdown by Account and Transaction Type
for account in pivoted_df.index.get_level_values(0).unique():
    account_df = pivoted_df.xs(account, level=0, drop_level=False)
    with st.expander(f"Account: {account}", expanded=True):
        for txn_type in account_df.index.get_level_values(1).unique():
            txn_df = account_df.xs(txn_type, level=1, drop_level=False)
            # Subtotal for this transaction type
            subtotal = txn_df.sum(numeric_only=True).to_frame().T
            st.markdown(f"**Transaction Type: {txn_type} (Subtotal)**")
            st.dataframe(subtotal.style.format("${:,.2f}"))
            # Details for each description
            with st.expander(f"Show Details for {txn_type}"):
                detail_df = txn_df.droplevel([0, 1])
                st.dataframe(detail_df.style.format("${:,.2f}"))

# ---------------------------
# TRANSACTIONS TABLE
# ---------------------------
# Title
st.subheader("Transactions")

# Copy Dataframe for display
display_df = filtered_df[
    [
        'Date',
        'Account Name',
        'Transaction Type',
        'Description',
        'Check Number',
        'Amount',
        'Account Running Balance',
        'PnL_flag'
    ]
].copy()

# Format Date as MM-DD-YYYY
display_df['Date'] = display_df['Date'].dt.strftime('%m-%d-%Y')
st.dataframe(
    display_df.sort_values("Date", ascending=False).reset_index(drop=True).style.format({
        "Amount": "${:,.2f}",
        "Account Running Balance": "${:,.2f}"
    })
)

# ---------------------------
# DOWNLOADABLE PNL BREAKDOWN
# ---------------------------
# Title
st.subheader("PNL Breakdown Download")

# Display full pivoted dataframe with formatting
st.dataframe(pivoted_df.style.format("${:,.2f}"))
