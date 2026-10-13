import pandas as pd

MIN_RENTERS = 50
MAX_CV = 0.30

INDICATORS = {
    "rent_burden_pct": {
        "label": "Percent of renters spending 30%+ of income on rent",
        "short_label": "Rent Burden",
        "numerator": ["B25070_007E",    # 30.0–34.9%
                      "B25070_008E",    # 35.0–39.9%
                      "B25070_009E",    # 40.0–49.9%
                      "B25070_010E"],   # 50% or more
        "denominator": ["B25070_001E"], # total population
        "subtract": ["B25070_011E"],    # renters where burden can't be computed
        "min_denominator": 50,
    },
    "poverty_pct": {
        "label": "Percent of people below the poverty line",
        "short_label": "Poverty Rate",
        "numerator": ["B17001_002E"],   # total below under poverty line
        "denominator": ["B17001_001E"], # total population
        "subtract": [],
        "min_denominator": 100,
    },
    "no_internet_pct": {
        "label": "Percent of households with no internet access",
        "short_label": "No Internet Access",
        "numerator": ["B28002_013E"],   # total without internet
        "denominator": ["B28002_001E"], # total population
        "subtract": [],
        "min_denominator": 50,
    },
}


def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    value_cols = [c for c in df.columns if c[0] == "B" and c[-1] in "EM"]
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce")
    df[value_cols] = df[value_cols].mask(df[value_cols] < 0)
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    for col, spec in INDICATORS.items():
        num = df[spec["numerator"]].sum(axis=1)
        den = df[spec["denominator"]].sum(axis=1) - df[spec["subtract"]].sum(axis=1)
        df[col] = (num / den * 100).where(den >= spec["min_denominator"])
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
    df = add_indicators(df)
    df = add_reliability(df)
    return add_location(df, gaz)