"""Tests for census/transform.py, using tiny hand-made tables."""
import pandas as pd
import pytest

from census import transform


def make_tract(**values):
    """One raw API row (all strings, like the real API), with sensible defaults."""
    row = {
        "NAME": "Census Tract 1", "state": "48", "county": "453", "tract": "000101",
        "B01003_001E": "4000", "B19013_001E": "60000", "B19013_001M": "5000",
        # rent burden: 200 renters, 0 not computed, 80 burdened (40%)
        "B25070_001E": "200", "B25070_007E": "20", "B25070_008E": "20",
        "B25070_009E": "20", "B25070_010E": "20", "B25070_011E": "0",
        # poverty: 1000 people, 150 below poverty (15%)
        "B17001_001E": "1000", "B17001_002E": "150",
        # internet: 500 households, 50 with no internet access (10%)
        "B28002_001E": "500", "B28002_013E": "50",
    }
    # Any variable a future indicator needs gets a placeholder "0", so adding
    # an indicator to the config never breaks these tests.
    for spec in transform.INDICATORS.values():
        for var in spec["numerator"] + spec["denominator"] + spec["subtract"]:
            row.setdefault(var, "0")
    row.update({k: str(v) for k, v in values.items()})
    return row


# ---- to_dataframe ---------------------------------------------------------

def test_values_become_numbers():
    df = transform.to_dataframe([make_tract()])
    assert df.loc[0, "B01003_001E"] == 4000


def test_census_no_data_codes_become_missing():
    # The API uses values like -666666666 to mean "no data".
    df = transform.to_dataframe([make_tract(B19013_001E=-666666666)])
    assert pd.isna(df.loc[0, "B19013_001E"])


def test_geoid_keeps_leading_zeros():
    df = transform.to_dataframe([make_tract(state="06", county="001", tract="400100")])
    assert df.loc[0, "GEOID"] == "06001400100"


# ---- add_indicators -------------------------------------------------------

def test_rent_burden_is_calculated_correctly():
    df = transform.add_indicators(transform.to_dataframe([make_tract()]))
    assert df.loc[0, "rent_burden_pct"] == pytest.approx(40.0)


def test_poverty_and_internet_rates():
    df = transform.add_indicators(transform.to_dataframe([make_tract()]))
    assert df.loc[0, "poverty_pct"] == pytest.approx(15.0)
    assert df.loc[0, "no_internet_pct"] == pytest.approx(10.0)


def test_not_computed_renters_are_left_out_of_the_denominator():
    # 200 renters, 40 can't be computed -> 80 burdened / 160 = 50%
    df = transform.add_indicators(transform.to_dataframe([make_tract(B25070_011E=40)]))
    assert df.loc[0, "rent_burden_pct"] == pytest.approx(50.0)


def test_small_samples_are_excluded():
    # Only 10 renters: a percentage would be misleading, so it should be blank.
    small = make_tract(B25070_001E=10, B25070_007E=5, B25070_008E=0,
                       B25070_009E=0, B25070_010E=0)
    df = transform.add_indicators(transform.to_dataframe([small]))
    assert pd.isna(df.loc[0, "rent_burden_pct"])


def test_every_indicator_gets_a_column():
    df = transform.add_indicators(transform.to_dataframe([make_tract()]))
    for column in transform.INDICATORS:
        assert column in df.columns


def test_indicator_config_is_complete():
    required = {"label", "short_label", "numerator", "denominator", "subtract", "min_denominator"}
    for name, spec in transform.INDICATORS.items():
        missing = required - spec.keys()
        assert not missing, f"{name} is missing {missing}"


# ---- add_reliability ------------------------------------------------------

def test_reliability_flag():
    rows = [
        make_tract(tract="000101", B19013_001E=60000, B19013_001M=5000),   # CV ~5%
        make_tract(tract="000102", B19013_001E=20000, B19013_001M=15000),  # CV ~46%
    ]
    df = transform.add_reliability(transform.to_dataframe(rows))
    assert df["reliable"].tolist() == [True, False]


# ---- add_location ---------------------------------------------------------

def test_gazetteer_merge_and_density():
    df = transform.to_dataframe([make_tract()])
    gaz = pd.DataFrame({"GEOID": ["48453000101"], "INTPTLAT": [30.3],
                        "INTPTLONG": [-97.7], "ALAND_SQMI": [2.0]})

    out = transform.add_location(df, gaz)

    assert out.loc[0, "INTPTLAT"] == 30.3
    assert out.loc[0, "pop_density"] == 2000