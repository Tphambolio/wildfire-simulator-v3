"""Runtime settings loaded from environment variables.

All paths are optional — the API falls back gracefully when not set.
Set these in the deployment environment or a local .env file.

Example .env:
    FIRESIM_FUEL_GRID_PATH=/data/fuel_maps/Edmonton_FBP_FuelLayer_20251105_10m.tif
    FIRESIM_WATER_PATH=/data/edmonton_water_bodies.geojson
    FIRESIM_BUILDINGS_PATH=/data/edmonton_buildings.geojson
"""

from __future__ import annotations

import os


class Settings:
    """Environment-backed settings for the FireSim API."""

    @property
    def fuel_grid_path(self) -> str | None:
        """Default GeoTIFF fuel raster to use when use_ca_mode=True.

        When set and the file exists, the real spatial grid is loaded instead
        of generating a synthetic landscape around the ignition point.
        """
        return os.environ.get("FIRESIM_FUEL_GRID_PATH")

    @property
    def water_path(self) -> str | None:
        """Default water bodies GeoJSON for non-fuel masking."""
        return os.environ.get("FIRESIM_WATER_PATH")

    @property
    def buildings_path(self) -> str | None:
        """Default building footprints GeoJSON for non-fuel masking."""
        return os.environ.get("FIRESIM_BUILDINGS_PATH")


settings = Settings()
