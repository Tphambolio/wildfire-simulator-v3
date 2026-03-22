"""Simulation runner service.

Manages simulation lifecycle: creation, execution, and result storage.
Simulations run in background threads and stream frames via callbacks.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Callable

from firesim.fbp.constants import FuelType
from firesim.spread.simulator import Simulator
from firesim.types import SimulationConfig, SimulationFrame, WeatherInput

from firesim_api.schemas.simulation import (
    SimulationCreate,
    SimulationStatus,
)

logger = logging.getLogger(__name__)


class SimulationRun:
    """Tracks state of a single simulation run."""

    def __init__(self, sim_id: str, config: SimulationCreate):
        self.id = sim_id
        self.config = config
        self.status: SimulationStatus = SimulationStatus.PENDING
        self.frames: list[SimulationFrame] = []
        self.error: str | None = None
        self._lock = threading.Lock()
        # Pause/cancel control
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially running (not paused)
        self._cancel_event = threading.Event()

    def add_frame(self, frame: SimulationFrame) -> None:
        with self._lock:
            self.frames.append(frame)

    def get_frames(self) -> list[SimulationFrame]:
        with self._lock:
            return list(self.frames)

    def pause(self) -> None:
        """Pause the simulation after the current frame."""
        if self.status == SimulationStatus.RUNNING:
            self.status = SimulationStatus.PAUSED
            self._pause_event.clear()

    def resume(self) -> None:
        """Resume a paused simulation."""
        if self.status == SimulationStatus.PAUSED:
            self.status = SimulationStatus.RUNNING
            self._pause_event.set()

    def cancel(self) -> None:
        """Cancel the simulation immediately."""
        self.status = SimulationStatus.CANCELLED
        self._cancel_event.set()
        self._pause_event.set()  # Unblock if paused


class SimulationRunner:
    """Manages simulation runs.

    Stores active and completed simulations in memory.
    In a production system this would use a database.
    """

    def __init__(self) -> None:
        self._runs: dict[str, SimulationRun] = {}
        self._lock = threading.Lock()
        # Cache loaded grids keyed by (fuel_path, water_path, buildings_path, wui_path)
        # Grids are spatial only — independent of weather/FWI, so safe to reuse
        self._grid_cache: dict[tuple, tuple] = {}
        self._grid_cache_lock = threading.Lock()

    def create(
        self,
        params: SimulationCreate,
        on_frame: Callable[[str, SimulationFrame], None] | None = None,
    ) -> str:
        """Create and start a new simulation.

        Args:
            params: Simulation parameters
            on_frame: Optional callback invoked for each frame (sim_id, frame)

        Returns:
            Simulation ID
        """
        sim_id = str(uuid.uuid4())[:8]
        run = SimulationRun(sim_id, params)

        with self._lock:
            self._runs[sim_id] = run

        # Start simulation in background thread
        thread = threading.Thread(
            target=self._execute,
            args=(run, on_frame),
            daemon=True,
        )
        thread.start()

        return sim_id

    def get(self, sim_id: str) -> SimulationRun | None:
        with self._lock:
            return self._runs.get(sim_id)

    def _load_grids(
        self,
        fuel_path: str | None,
        water_path: str | None,
        buildings_path: str | None,
        wui_path: str | None,
        dem_path: str | None = None,
    ) -> tuple:
        """Load fuel grid, WUI modifiers, and terrain grid, caching by path combo.

        Grids are purely spatial — independent of weather/FWI/ignition point,
        so they're safe to reuse across simulations.

        Returns:
            (fuel_grid, spread_modifier_grid, terrain_grid) — any may be None.
        """
        if not fuel_path and not dem_path:
            return None, None, None

        cache_key = (fuel_path, water_path, buildings_path, wui_path, dem_path)

        with self._grid_cache_lock:
            if cache_key in self._grid_cache:
                cached = self._grid_cache[cache_key]
                cached_fuel = cached[0]
                if cached_fuel is not None:
                    logger.info(
                        "Grid cache HIT: %s — serving %dx%d grid from cache",
                        fuel_path, cached_fuel.rows, cached_fuel.cols,
                    )
                else:
                    logger.info("Grid cache HIT (dem-only or empty)")
                return cached

        logger.info("Grid cache MISS: loading fuel=%s dem=%s", fuel_path, dem_path)

        fuel_grid = None
        spread_modifier_grid = None
        terrain_grid = None

        if fuel_path:
            from firesim.data.fuel_loader import load_fuel_grid

            try:
                fuel_grid = load_fuel_grid(
                    fuel_path,
                    water_path=water_path,
                    buildings_path=buildings_path,
                )
            except FileNotFoundError:
                logger.error("Fuel grid file not found: %s", fuel_path)
                raise
            except ValueError as exc:
                logger.error("Fuel grid rejected (%s): %s", fuel_path, exc)
                raise
            except Exception as exc:
                logger.error(
                    "Failed to load fuel grid from %s: %s — "
                    "file may be corrupt or in an unsupported format",
                    fuel_path, exc,
                )
                raise

            if wui_path:
                from firesim.data.wui_loader import load_wui_modifiers

                spread_modifier_grid = load_wui_modifiers(
                    wui_path,
                    bounds=(fuel_grid.lat_min, fuel_grid.lat_max,
                            fuel_grid.lng_min, fuel_grid.lng_max),
                    rows=fuel_grid.rows,
                    cols=fuel_grid.cols,
                )

        if dem_path:
            from firesim.data.dem_loader import load_terrain_grid

            try:
                terrain_grid = load_terrain_grid(dem_path)
                logger.info(
                    "DEM loaded: %dx%d terrain grid for slope-adjusted spread",
                    terrain_grid.rows, terrain_grid.cols,
                )
            except FileNotFoundError:
                logger.error("DEM file not found: %s", dem_path)
                raise
            except Exception as exc:
                logger.error("Failed to load DEM from %s: %s", dem_path, exc)
                raise

        result = (fuel_grid, spread_modifier_grid, terrain_grid)

        with self._grid_cache_lock:
            self._grid_cache[cache_key] = result
            logger.info(
                "Grid cache STORE: fuel=%s dem=%s wui=%s",
                fuel_path is not None, dem_path is not None, wui_path is not None,
            )

        return result

    def _execute(
        self,
        run: SimulationRun,
        on_frame: Callable[[str, SimulationFrame], None] | None,
    ) -> None:
        """Execute a simulation run."""
        run.status = SimulationStatus.RUNNING
        params = run.config

        try:
            # Resolve fuel type
            try:
                fuel_type = FuelType(params.fuel_type)
            except ValueError:
                fuel_type = FuelType.C2

            # Build engine config
            fwi = params.fwi_overrides
            config = SimulationConfig(
                ignition_lat=params.ignition_lat,
                ignition_lng=params.ignition_lng,
                weather=WeatherInput(
                    temperature=params.weather.temperature,
                    relative_humidity=params.weather.relative_humidity,
                    wind_speed=params.weather.wind_speed,
                    wind_direction=params.weather.wind_direction,
                    precipitation_24h=params.weather.precipitation_24h,
                ),
                duration_hours=params.duration_hours,
                snapshot_interval_minutes=params.snapshot_interval_minutes,
                ffmc=fwi.ffmc if fwi else 85.0,
                dmc=fwi.dmc if fwi else 40.0,
                dc=fwi.dc if fwi else 200.0,
            )

            from firesim_api.settings import settings

            # Resolve DEM path: per-request overrides env-var default
            dem_path = getattr(params, "dem_path", None) or settings.dem_path

            # Load spatial grids (cached — only loads once per unique path combo)
            fuel_grid, spread_modifier_grid, terrain_grid = self._load_grids(
                params.fuel_grid_path,
                params.water_path,
                params.buildings_path,
                getattr(params, "wui_zones_path", None),
                dem_path,
            )

            # CA mode: load real grid from settings env var, fall back to synthetic
            if fuel_grid is None and getattr(params, "use_ca_mode", False):
                default_fuel_path = settings.fuel_grid_path
                if default_fuel_path and os.path.exists(default_fuel_path):
                    logger.info("CA mode: loading real fuel grid from %s", default_fuel_path)
                    real_grid, real_wui, real_terrain = self._load_grids(
                        default_fuel_path,
                        params.water_path or settings.water_path,
                        params.buildings_path or settings.buildings_path,
                        getattr(params, "wui_zones_path", None),
                        dem_path,
                    )
                    fuel_grid = real_grid
                    if real_wui is not None and spread_modifier_grid is None:
                        spread_modifier_grid = real_wui
                    if real_terrain is not None and terrain_grid is None:
                        terrain_grid = real_terrain
                    logger.info(
                        "Real CA grid loaded: %dx%d (%.4f-%.4fN, %.4f-%.4fE)",
                        fuel_grid.rows, fuel_grid.cols,
                        fuel_grid.lat_min, fuel_grid.lat_max,
                        fuel_grid.lng_min, fuel_grid.lng_max,
                    )
                else:
                    from firesim.data.synthetic_grid import generate_synthetic_fuel_grid

                    fuel_grid = generate_synthetic_fuel_grid(
                        ignition_lat=params.ignition_lat,
                        ignition_lng=params.ignition_lng,
                        radius_km=5.0,
                        cell_size_m=50.0,
                    )
                    logger.info(
                        "Synthetic CA grid generated: %dx%d around (%.4f, %.4f)",
                        fuel_grid.rows, fuel_grid.cols,
                        params.ignition_lat, params.ignition_lng,
                    )

            simulator = Simulator(
                config,
                fuel_grid=fuel_grid,
                terrain_grid=terrain_grid,
                default_fuel=fuel_type,
                spread_modifier_grid=spread_modifier_grid,
            )

            for frame in simulator.run():
                run.add_frame(frame)
                if on_frame is not None:
                    on_frame(run.id, frame)
                # Block here when paused; unblocks on resume() or cancel()
                run._pause_event.wait()
                if run._cancel_event.is_set():
                    break

            if not run._cancel_event.is_set():
                run.status = SimulationStatus.COMPLETED
                logger.info("Simulation %s completed: %d frames", run.id, len(run.frames))
            else:
                logger.info("Simulation %s cancelled after %d frames", run.id, len(run.frames))

        except Exception as e:
            run.status = SimulationStatus.FAILED
            run.error = str(e)
            logger.exception("Simulation %s failed: %s", run.id, e)
