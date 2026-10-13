from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from census import client, transform, viz

load_dotenv()  # reads CENSUS_API_KEY from .env when running locally

ROOT = Path(__file__).resolve().parent
GAZETTEER_PATH = ROOT / "data" / "gaz_tracts.parquet"
DEFAULT_STATE = "Texas"
DEFAULT_CITY = "Austin city"
ONE_DAY = 60 * 60 * 24

st.set_page_config(page_title="Census Dashboard Visualizer", layout="wide")

#caching data
@st.cache_data(ttl=ONE_DAY)
def load_states() -> list[dict]:
    return sorted(client.list_states(), key=lambda r: r["NAME"])


@st.cache_data(ttl=ONE_DAY)
def load_places(state_fips: str) -> list[dict]:
    return sorted(client.list_places(state_fips), key=lambda r: r["NAME"])


@st.cache_data
def load_gazetteer() -> pd.DataFrame:
    return pd.read_parquet(GAZETTEER_PATH)


@st.cache_data(ttl=ONE_DAY, show_spinner=False)
def load_tract_data(state_fips: str, place_fips: str) -> pd.DataFrame:
    rows = client.tracts_for_city(state_fips, place_fips)
    return transform.build_tract_table(rows, load_gazetteer())


def default_index(options: list[dict], name: str) -> int:
    return next((i for i, r in enumerate(options) if r["NAME"] == name), 0)


def short_place_name(full_name: str) -> str:
    return full_name.rsplit(",", 1)[0]


st.title("Census Dashboard Visualizer")
st.caption(
    "A visualization tool for Census Dashboard data. To derive impacted areas with cluster map visualization of data."
)

try:
    states = load_states()
except (client.CensusAPIError, requests.RequestException) as e:
    st.error(f"Couldn't reach the Census API: {e}")
    st.stop()

col_state, col_city, col_ind = st.columns(3)
state = col_state.selectbox(
    "State",
    states,
    index=default_index(states, DEFAULT_STATE),
    format_func=lambda r: r["NAME"],
)

try:
    places = load_places(state["state"])
except (client.CensusAPIError, requests.RequestException) as e:
    st.error(f"Couldn't load cities for {state['NAME']}: {e}")
    st.stop()

place = col_city.selectbox(
    "City",
    places,
    index=default_index(places, f"{DEFAULT_CITY}, {state['NAME']}"),
    format_func=lambda r: short_place_name(r["NAME"]),
    help="Start typing to search.",
)

indicator = col_ind.selectbox(
    "Indicator",
    list(transform.INDICATORS),
    format_func=lambda k: transform.INDICATORS[k]["label"],
)
spec = transform.INDICATORS[indicator]

try:
    with st.spinner(f"Fetching Census data for {short_place_name(place['NAME'])}..."):
        df = load_tract_data(state["state"], place["place"])
except client.InvalidAPIKeyError:
    st.error("The Census API rejected the API key. Check the CENSUS_API_KEY setting.")
    st.stop()
except (client.CensusAPIError, requests.RequestException) as e:
    st.error(f"Couldn't load data: {e}")
    st.stop()

has_burden = df["rent_burden_pct"].notna()
if not has_burden.any():
    st.warning("No tracts in this area have enough renter households to calculate rent burden.")
    st.stop()

# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Census tracts", f"{len(df):,}")
m2.metric("Median tract " + spec["short_label"], f"{df[indicator].median():.1f}%")
m3.metric(
    "Tracts where a majority suffer from " + spec["short_label"],
    f"{(df[indicator] > 50).sum():,}",
    help="Tracts where over 50% of the population suffer from " + spec["short_label"],
)
num = df[spec["numerator"]].sum(axis=1).sum()
den = (df[spec["denominator"]].sum(axis=1) - df[spec["subtract"]].sum(axis=1)).sum()
m4.metric("Area-wide rate", f"{num / den * 100:.1f}%",
          help="All tracts combined, not an average of tract percentages.")

#printing the map
st.plotly_chart(viz.build_map(df, metric=indicator, label=spec["label"]), use_container_width=True)


#top 10 board with option
has_value = df[indicator].notna()

st.subheader(f"Top 10 tracts: {spec['short_label'].lower()}")
st.caption(spec["label"])

top10 = df[has_value].nlargest(10, indicator)[
    ["NAME", indicator, "B19013_001E", "B01003_001E"]
]

st.dataframe(
    top10,
    hide_index=True,
    use_container_width=True,
    column_config={
        "NAME": st.column_config.TextColumn("Tract", width="large"),
        indicator: st.column_config.NumberColumn(spec["short_label"], format="%.1f%%"),
        "B19013_001E": st.column_config.NumberColumn("Median household income", format="dollar"),
        "B01003_001E": st.column_config.NumberColumn("Population", format="localized"),
    },
)

st.download_button(
    "Download all tract data (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"tract_data_{state['state']}{place['place']}.csv",
    mime="text/csv",
)