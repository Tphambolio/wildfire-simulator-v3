"""Pydantic models for simulation endpoints."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class WeatherParams(BaseModel):
    """Weather input for simulation."""

    wind_speed: float = Field(..., ge=0, le=100, description="Wind speed in km/h")
    wind_direction: float = Field(
        ..., ge=0, lt=360, description="Wind direction (degrees, meteorological FROM)"
    )
    temperature: float = Field(
        default=25.0, ge=-40, le=50, description="Temperature in Celsius"
    )
    relative_humidity: float = Field(
        default=30.0, ge=0, le=100, description="Relative humidity (%)"
    )
    precipitation_24h: float = Field(
        default=0.0, ge=0, description="24-hour precipitation (mm)"
    )


class FWIOverrides(BaseModel):
    """Optional FWI component overrides."""

    ffmc: float | None = Field(default=None, ge=0, le=101, description="Fine Fuel Moisture Code")
    dmc: float | None = Field(default=None, ge=0, description="Duff Moisture Code")
    dc: float | None = Field(default=None, ge=0, description="Drought Code")


class SimulationCreate(BaseModel):
    """Request body for creating a new simulation."""

    ignition_lat: float = Field(..., ge=-90, le=90, description="Ignition latitude")
    ignition_lng: float = Field(..., ge=-180, le=180, description="Ignition longitude")
    weather: WeatherParams
    fwi_overrides: FWIOverrides | None = None
    duration_hours: float = Field(default=4.0, gt=0, le=24, description="Simulation duration (hours)")
    snapshot_interval_minutes: float = Field(
        default=30.0, gt=0, le=120, description="Snapshot interval (minutes)"
    )
    fuel_type: str = Field(default="C2", description="Default fuel type code")


class SimulationStatus(str, Enum):
    """Simulation run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationFrame(BaseModel):
    """A single simulation snapshot."""

    time_hours: float
    perimeter: list[list[float]]  # [[lat, lng], ...]
    area_ha: float
    head_ros_m_min: float
    max_hfi_kw_m: float
    fire_type: str
    flame_length_m: float
    fuel_breakdown: dict[str, float]


class SimulationResponse(BaseModel):
    """Response from simulation creation or status query."""

    simulation_id: str
    status: SimulationStatus
    config: SimulationCreate | None = None
    frames: list[SimulationFrame] = []
    error: str | None = None
