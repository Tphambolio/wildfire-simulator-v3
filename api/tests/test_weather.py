"""Tests for the /api/v1/weather/current endpoint.

Uses httpx mock responder to avoid hitting the real CWFIS API in CI.
"""

from __future__ import annotations

import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from firesim_api.main import create_app

_CWFIS_URL = "https://cwfis.cfs.nrcan.gc.ca/api/forecast"


@pytest.fixture
def client():
    return TestClient(create_app())


_FULL_RESPONSE = {
    "ffmc": 90.5,
    "dmc": 42.3,
    "dc": 280.0,
    "isi": 11.2,
    "bui": 60.1,
    "fwi": 18.7,
    "ws": 22.0,
    "wd": 270.0,
    "temp": 24.0,
    "rh": 28.0,
}


class TestWeatherEndpoint:
    """Basic contract tests for GET /api/v1/weather/current."""

    @respx.mock
    def test_returns_200_with_data(self, client):
        """When CWFIS returns valid data, endpoint returns available=True."""
        respx.get(_CWFIS_URL).mock(
            return_value=httpx.Response(200, json=_FULL_RESPONSE)
        )
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["ffmc"] == pytest.approx(90.5)
        assert data["dmc"] == pytest.approx(42.3)
        assert data["dc"] == pytest.approx(280.0)
        assert data["fwi"] == pytest.approx(18.7)
        assert data["source"] == "CWFIS / Natural Resources Canada"

    @respx.mock
    def test_wind_fields_populated(self, client):
        """Wind speed and direction should come through."""
        respx.get(_CWFIS_URL).mock(
            return_value=httpx.Response(200, json=_FULL_RESPONSE)
        )
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        data = resp.json()
        assert data["wind_speed"] == pytest.approx(22.0)
        assert data["wind_direction"] == pytest.approx(270.0)
        assert data["temperature"] == pytest.approx(24.0)
        assert data["relative_humidity"] == pytest.approx(28.0)

    @respx.mock
    def test_cwfis_timeout_returns_unavailable(self, client):
        """Network timeout should return available=False, not 500."""
        respx.get(_CWFIS_URL).mock(side_effect=httpx.TimeoutException("timeout"))
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["ffmc"] is None

    @respx.mock
    def test_cwfis_http_error_returns_unavailable(self, client):
        """Non-200 from CWFIS should return available=False, not 500."""
        respx.get(_CWFIS_URL).mock(return_value=httpx.Response(503))
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    @respx.mock
    def test_empty_cwfis_response_returns_unavailable(self, client):
        """Empty JSON (off-season) should return available=False."""
        respx.get(_CWFIS_URL).mock(return_value=httpx.Response(200, json={}))
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    def test_missing_lat_returns_422(self, client):
        """Missing required lat param should return 422 validation error."""
        resp = client.get("/api/v1/weather/current?lng=-113.5")
        assert resp.status_code == 422

    def test_invalid_lat_returns_422(self, client):
        """Out-of-range lat should be rejected."""
        resp = client.get("/api/v1/weather/current?lat=999&lng=-113.5")
        assert resp.status_code == 422

    @respx.mock
    def test_message_contains_fwi_label(self, client):
        """Available response message should include FWI label."""
        respx.get(_CWFIS_URL).mock(
            return_value=httpx.Response(200, json=_FULL_RESPONSE)
        )
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        data = resp.json()
        assert "18.7" in data["message"] or "Moderate" in data["message"]

    @respx.mock
    def test_high_fwi_label(self, client):
        """FWI >= 19 should appear as High in the message."""
        high_fwi = {**_FULL_RESPONSE, "fwi": 25.0}
        respx.get(_CWFIS_URL).mock(return_value=httpx.Response(200, json=high_fwi))
        resp = client.get("/api/v1/weather/current?lat=53.5&lng=-113.5")
        data = resp.json()
        assert data["available"] is True
        assert "High" in data["message"]

    @respx.mock
    def test_coords_echoed_in_response(self, client):
        """Lat/lng should be echoed back in the response."""
        respx.get(_CWFIS_URL).mock(return_value=httpx.Response(200, json=_FULL_RESPONSE))
        resp = client.get("/api/v1/weather/current?lat=51.2&lng=-114.8")
        data = resp.json()
        assert data["lat"] == pytest.approx(51.2)
        assert data["lng"] == pytest.approx(-114.8)
