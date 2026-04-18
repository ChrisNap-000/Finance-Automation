# =============================================================================
# config.py — Application-wide constants
#
# Add any shared configuration values here so they can be imported by multiple
# modules without duplication.
# =============================================================================

# Accounts included in the "Total Balance" KPI and individual balance metrics.
# These must match the account_name values stored in the dim_accounts table.
# If you add or rename an account in Supabase, update this list to match.
BALANCE_ACCOUNTS = ["Checking", "Savings", "CD"]
