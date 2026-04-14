import pandas as pd

from config import BAD_ROW_COLUMNS


def load_transactions(file):
    bad_rows = []

    def handle_bad_line(row):
        bad_rows.append(row)
        return None

    df_main = pd.read_csv(
        file,
        engine="python",
        quotechar='"',
        on_bad_lines=handle_bad_line,
        parse_dates=["Date"]
    )

    df_bad = pd.DataFrame(bad_rows)

    if not df_bad.empty:
        if 5 in df_bad.columns:
            df_bad[4] = df_bad[4].astype(str) + "," + df_bad[5].astype(str)
            df_bad = df_bad.drop(columns=[5])
        df_bad = df_bad.rename(columns=BAD_ROW_COLUMNS)
        df_main = pd.concat([df_main, df_bad], ignore_index=True)

    return df_main


def load_lookup(file):
    return pd.read_excel(file)


def merge_data(df_main, df_lookup):
    df_main["Account Number"] = df_main["Account Number"].astype("string")
    df_lookup["Account Number"] = df_lookup["Account Number"].astype("string")
    return df_main.merge(df_lookup, how="left", on="Account Number")
