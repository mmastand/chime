import pandas as pd


def prep_dummy_data(paths):
    dfs = []
    for path in paths:
        df = pd.read_csv(path).assign(date = lambda d: pd.to_datetime(d.date)).fillna(method="backfill")
        dfs.append(df)
    if len(dfs) > 1:
        ops = {
            "ML": "mean",
            "Low_75": "mean",
            "High_75": "mean",
            "cases": "sum",
            "smoothed": "sum",
            "fcst": "sum",
            "prd_ets": "sum",
            "s": "sum",
            "i": "sum",
            "r": "sum",
        }
        combined = pd.concat(dfs)
        return combined.groupby("date").agg(ops).reset_index()
    else:
        return dfs[0]