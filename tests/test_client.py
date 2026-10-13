"""Tests for census/client.py.

The real Census API is never called: each test swaps SESSION.get for a fake
that returns a pre-built response, so tests are fast, free, and run offline.
"""
import pytest

from census import client


class FakeResponse:
    """Just enough of a requests.Response for census_get to work with."""

    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise client.requests.HTTPError(f"{self.status_code} error")


def fake_api(monkeypatch, response, captured=None):
    """Make SESSION.get return `response` (and optionally record the call)."""

    def fake_get(url, params=None, timeout=None):
        if captured is not None:
            captured["url"] = url
            captured["params"] = params
        return response

    monkeypatch.setattr(client.SESSION, "get", fake_get)


# ---- census_get -----------------------------------------------------------

def test_rows_are_returned_as_dicts(monkeypatch):
    data = [["NAME", "state"], ["Texas", "48"], ["Ohio", "39"]]
    fake_api(monkeypatch, FakeResponse(text="[...]", json_data=data))

    rows = client.census_get("2020/dec/pl", {"get": "NAME", "for": "state:*"})

    assert rows == [{"NAME": "Texas", "state": "48"}, {"NAME": "Ohio", "state": "39"}]


def test_invalid_key_page_raises_clear_error(monkeypatch):
    # Bug found in development: a bad key returns an HTML page, not JSON.
    html = "<html><head><title>Invalid Key</title></head></html>"
    fake_api(monkeypatch, FakeResponse(text=html))

    with pytest.raises(client.InvalidAPIKeyError):
        client.census_get("2024/acs/acs5", {})


def test_empty_204_response_raises_clear_error(monkeypatch):
    # Bug found in development: an unknown geography returns an empty body,
    # which used to crash with a confusing JSONDecodeError.
    fake_api(monkeypatch, FakeResponse(status_code=204, text=""))

    with pytest.raises(client.CensusAPIError):
        client.census_get("2020/dec/pl", {})


def test_api_key_is_added_from_environment(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "test-key-123")
    captured = {}
    fake_api(monkeypatch, FakeResponse(text="[...]", json_data=[["NAME"]]), captured)

    client.census_get("2020/dec/pl", {"get": "NAME"})

    assert captured["params"]["key"] == "test-key-123"


def test_callers_params_are_not_modified(monkeypatch):
    monkeypatch.setenv("CENSUS_API_KEY", "test-key-123")
    fake_api(monkeypatch, FakeResponse(text="[...]", json_data=[["NAME"]]))
    params = {"get": "NAME"}

    client.census_get("2020/dec/pl", params)

    assert "key" not in params


# ---- county_codes_in_city -------------------------------------------------

def test_short_fips_codes_are_zero_padded(monkeypatch):
    # Bug found in development: "0500" instead of "05000" returned no data.
    captured = {}
    data = [["NAME", "P1_001N", "state", "place", "county (or part)"]]
    fake_api(monkeypatch, FakeResponse(text="[...]", json_data=data), captured)

    client.county_codes_in_city("48", "5000")

    assert captured["params"]["in"] == "state:48 place:05000"


def test_zero_population_county_parts_are_dropped(monkeypatch):
    # Austin's boundary touches Bastrop County, but no one lives in that piece.
    data = [
        ["NAME", "P1_001N", "state", "place", "county (or part)"],
        ["Travis County (part)", "880000", "48", "05000", "453"],
        ["Bastrop County (part)", "0", "48", "05000", "021"],
        ["Williamson County (part)", "80000", "48", "05000", "491"],
    ]
    fake_api(monkeypatch, FakeResponse(text="[...]", json_data=data))

    assert client.county_codes_in_city("48", "05000") == ["453", "491"]