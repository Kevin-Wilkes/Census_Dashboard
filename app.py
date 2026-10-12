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

st.set_page_config(page_title="Renter Cost Burden Explorer", layout="wide")

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


st.title("Where are renters most cost-burdened?")
st.caption(
    "Share of renter households spending 30% or more of their income on rent"
)

try:
    states = load_states()
except (client.CensusAPIError, requests.RequestException) as e:
    st.error(f"Couldn't reach the Census API: {e}")
    st.stop()

col_state, col_city = st.columns(2)
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
m2.metric("Median tract rent burden", f"{df['rent_burden_pct'].median():.1f}%")
m3.metric(
    "Tracts where most renters are burdened",
    f"{(df['rent_burden_pct'] > 50).sum():,}",
    help="Tracts where over 50% of renter households spend 30%+ of income on rent.",
)
m4.metric(
    "Low-reliability estimates",
    f"{(~df['reliable']).sum():,}",
    help="Tracts whose median income estimate has a coefficient of variation above 30%.",
)

#printing the map
st.plotly_chart(viz.build_map(df), use_container_width=True)

#top 10 board with option
st.subheader("Most cost-burdened tracts")

top10 = (
    df[has_burden]
    .nlargest(10, "rent_burden_pct")[
        ["NAME", "rent_burden_pct", "B19013_001E", "B01003_001E"]
    ]
)
st.dataframe(
    top10,
    hide_index=True,
    use_container_width=True,
    column_config={
        "NAME": st.column_config.TextColumn("Tract"),
        "rent_burden_pct": st.column_config.NumberColumn("% renters burdened", format="%.1f%%"),
        "B19013_001E": st.column_config.NumberColumn("Median household income", format="$%,.0f"),
        "B01003_001E": st.column_config.NumberColumn("Population", format="%,d"),
    },
)

st.download_button(
    "Download all tract data (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"rent_burden_{state['state']}{place['place']}.csv",
    mime="text/csv",
)

