import pandas as pd

MIN_RENTERS = 50
MAX_CV = 0.30


def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    value_cols = [c for c in df.columns if c[0] == "B" and c[-1] in "EM"]
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce")
    df[value_cols] = df[value_cols].mask(df[value_cols] < 0)
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    return df


def add_rent_burden(df: pd.DataFrame) -> pd.DataFrame:
    burdened = df[["B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E"]].sum(axis=1)
    computed = df["B25070_001E"] - df["B25070_011E"]
    df["rent_burden_pct"] = (burdened / computed * 100).where(computed >= MIN_RENTERS)
    return df


def add_reliability(df: pd.DataFrame) -> pd.DataFrame:
    cv = (df["B19013_001M"] / 1.645) / df["B19013_001E"]
    df["reliable"] = cv < MAX_CV
    return df


def add_location(df: pd.DataFrame, gaz: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(gaz, on="GEOID", how="left")
    df["pop_density"] = df["B01003_001E"] / df["ALAND_SQMI"]
    return df


def build_tract_table(rows: list[dict], gaz: pd.DataFrame) -> pd.DataFrame:
    #full build call
    df = to_dataframe(rows)
    df = add_rent_burden(df)
    df = add_reliability(df)
    return add_location(df, gaz)