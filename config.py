# =============================================================================
# config.py — Application-wide constants
#
# Add any shared configuration values here so they can be imported by multiple
# modules without duplication.
# =============================================================================

# All accounts included in the "Total Balance" KPI.
# Must match account_name values in dim_accounts exactly (case-sensitive).
BALANCE_ACCOUNTS = ["TD Checking", "TD Savings", "TD CD", "Schwab", "Vanguard", "Retirement"]

# Bank/cash accounts shown in their own balance row on the dashboard.
BANK_ACCOUNTS = ["TD Checking", "TD Savings", "TD CD"]

# Investment accounts shown separately — excluded from PnL calculations.
INVESTMENT_ACCOUNTS = ["Schwab", "Vanguard", "Retirement"]

# Preferred display order for the account dropdown in Add Transaction.
# Any account not listed here will appear at the end in alphabetical order.
ACCOUNT_DROPDOWN_ORDER = ["TD Cash", "TD Checking", "TD Savings", "TD CD", "Retirement", "Schwab", "Vanguard"]
