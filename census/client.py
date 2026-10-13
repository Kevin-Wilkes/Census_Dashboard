
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from census.transform import INDICATORS

BASE_VARS = ["NAME", "B01003_001E", "B19013_001E", "B19013_001M"]
INDICATOR_VARS = sorted({v for spec in INDICATORS.values()
                         for key in ("numerator", "denominator", "subtract")
                         for v in spec[key]})
ACS_VARS = BASE_VARS + INDICATOR_VARS

BASE = "https://api.census.gov/data"

class CensusAPIError(Exception):
    """Something went wrong talking to the Census API."""

class InvalidAPIKeyError(CensusAPIError):
    """The Census API rejected the API key."""

def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,                        
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


SESSION = _make_session()


def census_get(path: str, params: dict) -> list[dict]:

    params = dict(params)
    api_key = os.getenv("CENSUS_API_KEY")
    if api_key:
        params["key"] = api_key

    resp = SESSION.get(f"{BASE}/{path}", params=params, timeout=30)

    # checks for invalid key in an HTML response
    if "invalid key" in resp.text.lower():
        raise InvalidAPIKeyError("The Census API rejected the API key. Check CENSUS_API_KEY.")

    resp.raise_for_status()

    # incorrect FIRP code
    if resp.status_code == 204 or not resp.text.strip():
        raise CensusAPIError("No data found for that location. Check the state and city codes.")

    header, *rows = resp.json()
    return [dict(zip(header, row)) for row in rows]


def list_states() -> list[dict]:
    return census_get("2020/dec/pl", {"get": "NAME", "for": "state:*"})


def list_places(state: str) -> list[dict]:
    return census_get("2020/dec/pl", {
        "get": "NAME",
        "for": "place:*",
        "in": f"state:{state.zfill(2)}",
    })

def county_codes_in_city(state: str, place: str) -> list[str]:

    rows = census_get("2020/dec/pl", {
        "get": "NAME,P1_001N",
        "for": "county (or part):*",
        "in": f"state:{state.zfill(2)} place:{place.zfill(5)}",
    })
    return [r["county (or part)"] for r in rows if int(r["P1_001N"]) > 0]

#Gathers all tracts that touch city lines even outside of city lines.
def tracts_for_city(state: str, place: str) -> list[dict]:
    rows = []
    for county in county_codes_in_city(state, place):
        rows += census_get("2024/acs/acs5", {
            "get": ",".join(ACS_VARS),
            "for": "tract:*",
            "in": f"state:{state.zfill(2)} county:{county}",
        })
    return rows