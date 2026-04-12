BAD_ROW_COLUMNS = {
    0: "Date",
    1: "Bank RTN",
    2: "Account Number",
    3: "Transaction Type",
    4: "Description",
    6: "Debit",
    7: "Credit",
    8: "Check Number",
    9: "Account Running Balance"
}

DATA_TYPES = {
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

DESC_PATTERNS = {
    r'.*AMAZON.*': 'Amazon',
    r'.*SJU.*': 'SJU Payroll',
    r'.*LEVELUP.*': 'LevelUP Payroll',
    r'.*DUNKIN.*': 'Dunkin',
    r'.*PLANET FITNESS.*': 'Planet Fitness'
}

TRANS_TYPE_PATTERNS = {
    r'.*CREDIT.*': 'Income',
    r'.*DEBIT.*': 'Expense',
    r'.*DEP.*': 'Deposit',
    r'.*DIRECTDEBIT.*': 'Expense',
    r'.*INT.*': 'Interest',
    r'.*XFER.*': 'Transfer'
}

BALANCE_ACCOUNTS = ["Checking", "Savings", "CD"]
