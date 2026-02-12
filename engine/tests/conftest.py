"""Shared test fixtures for firesim engine tests."""

import pytest

from firesim.fbp.constants import FuelType


@pytest.fixture
def standard_weather():
    """Standard fire weather conditions for testing.

    Represents a moderate-to-high fire danger day:
    FFMC=90, DMC=45, DC=300, wind=20 km/h
    """
    return {
        "ffmc": 90.0,
        "dmc": 45.0,
        "dc": 300.0,
        "wind_speed": 20.0,
    }


@pytest.fixture
def extreme_weather():
    """Extreme fire weather conditions for testing.

    Represents a very high fire danger day:
    FFMC=95, DMC=80, DC=500, wind=40 km/h
    """
    return {
        "ffmc": 95.0,
        "dmc": 80.0,
        "dc": 500.0,
        "wind_speed": 40.0,
    }


@pytest.fixture
def all_fuel_types():
    """List of all 18 FBP fuel types."""
    return list(FuelType)
