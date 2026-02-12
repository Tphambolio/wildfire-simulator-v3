"""Fire spread simulation orchestrator.

The Simulator class accepts configuration (ignition point, weather, fuel grid,
terrain) and runs the Huygens wavelet spread algorithm. It yields SimulationFrame
snapshots at configurable intervals, enabling real-time streaming.

Usage:
    sim = Simulator(config, fuel_grid, terrain_grid)
    for frame in sim.run():
        print(f"Time: {frame.time_hours}h, Area: {frame.area_ha} ha")
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Generator

from firesim.fbp.calculator import calculate_fbp
from firesim.fbp.constants import FuelType
from firesim.spread.ellipse import calculate_length_to_breadth_ratio
from firesim.spread.huygens import (
    FireVertex,
    FuelGrid,
    SpreadConditions,
    TerrainGrid,
    expand_fire_front,
    simplify_front,
)
from firesim.spread.perimeter import calculate_polygon_area_ha, vertices_to_polygon
from firesim.types import FBPResult, FireType, SimulationConfig, SimulationFrame

logger = logging.getLogger(__name__)


class Simulator:
    """Fire spread simulation using Huygens wavelet expansion.

    The simulator runs as a generator, yielding SimulationFrame objects
    at each snapshot interval. This enables streaming to clients.

    Attributes:
        config: Simulation configuration (ignition, weather, duration)
        fuel_grid: Spatial fuel type grid (or None for uniform fuel)
        terrain_grid: Slope/aspect grid (or None for flat terrain)
        default_fuel: Fuel type when grid is None or lookup returns None
    """

    def __init__(
        self,
        config: SimulationConfig,
        fuel_grid: FuelGrid | None = None,
        terrain_grid: TerrainGrid | None = None,
        default_fuel: FuelType = FuelType.C2,
        dt_minutes: float = 5.0,
        num_rays: int = 36,
    ):
        """Initialize simulator.

        Args:
            config: Simulation configuration
            fuel_grid: Spatial fuel types (None = uniform default_fuel)
            terrain_grid: Slope/aspect (None = flat terrain)
            default_fuel: Default fuel type when no grid available
            dt_minutes: Internal timestep (minutes). Controls simulation
                accuracy. Smaller = more accurate but slower.
            num_rays: Number of directional rays per Huygens wavelet.
                More rays = smoother perimeters but slower.
        """
        self.config = config
        self.fuel_grid = fuel_grid
        self.terrain_grid = terrain_grid
        self.default_fuel = default_fuel
        self.dt_minutes = dt_minutes
        self.num_rays = num_rays

    def run(self) -> Generator[SimulationFrame, None, None]:
        """Run the simulation, yielding frames at snapshot intervals.

        Yields:
            SimulationFrame at each snapshot_interval_minutes
        """
        config = self.config

        # Initialize fire front at ignition point
        # Start with a small circle of vertices (avoids single-point issues)
        front = self._create_ignition_front(config.ignition_lat, config.ignition_lng)

        # Build spread conditions from config
        conditions = SpreadConditions(
            wind_speed=config.weather.wind_speed,
            wind_direction=config.weather.wind_direction,
            ffmc=config.ffmc if config.ffmc is not None else 85.0,
            dmc=config.dmc if config.dmc is not None else 40.0,
            dc=config.dc if config.dc is not None else 200.0,
        )

        # Time tracking
        total_minutes = config.duration_hours * 60.0
        snapshot_interval = config.snapshot_interval_minutes
        elapsed_minutes = 0.0
        next_snapshot = snapshot_interval

        logger.info(
            "Starting simulation: ignition=(%.4f, %.4f), duration=%.1fh, fuel=%s",
            config.ignition_lat,
            config.ignition_lng,
            config.duration_hours,
            self.default_fuel.value,
        )

        # Yield initial frame (t=0)
        yield self._create_frame(front, 0.0)

        # Main simulation loop
        while elapsed_minutes < total_minutes:
            # Advance one timestep
            dt = min(self.dt_minutes, total_minutes - elapsed_minutes)

            new_front = expand_fire_front(
                front=front,
                conditions=conditions,
                fuel_grid=self.fuel_grid,
                terrain_grid=self.terrain_grid,
                dt_minutes=dt,
                default_fuel=self.default_fuel,
                num_rays=self.num_rays,
            )

            # Simplify to control vertex count
            front = simplify_front(new_front)

            elapsed_minutes += dt

            # Yield snapshot if we've reached the interval
            if elapsed_minutes >= next_snapshot or elapsed_minutes >= total_minutes:
                time_hours = elapsed_minutes / 60.0
                frame = self._create_frame(front, time_hours)
                yield frame
                next_snapshot += snapshot_interval

        logger.info(
            "Simulation complete: %.1fh, final area=%.1f ha",
            config.duration_hours,
            calculate_polygon_area_ha(front),
        )

    def _create_ignition_front(
        self, lat: float, lng: float, radius_m: float = 30.0, num_points: int = 12
    ) -> list[FireVertex]:
        """Create initial fire front as a small circle around ignition point.

        Starting with a single point causes degenerate geometry. Instead,
        we initialize with a small circle representing the initial fire.

        Args:
            lat: Ignition latitude
            lng: Ignition longitude
            radius_m: Initial fire radius (meters)
            num_points: Number of vertices in the initial circle

        Returns:
            List of FireVertex forming a small circle
        """
        m_per_deg_lat = 111320.0
        m_per_deg_lng = 111320.0 * math.cos(math.radians(lat))

        vertices = []
        for i in range(num_points):
            angle = 2.0 * math.pi * i / num_points
            dlat = radius_m * math.cos(angle) / m_per_deg_lat
            dlng = radius_m * math.sin(angle) / m_per_deg_lng
            vertices.append(FireVertex(lat=lat + dlat, lng=lng + dlng))

        return vertices

    def _create_frame(
        self, front: list[FireVertex], time_hours: float
    ) -> SimulationFrame:
        """Create a SimulationFrame from the current fire front.

        Calculates area, ROS, intensity, and other metrics from the
        current fire front state.
        """
        # Calculate area
        area_ha = calculate_polygon_area_ha(front)

        # Calculate FBP for the head fire direction to get metrics
        fbp = calculate_fbp(
            fuel_type=self.default_fuel,
            wind_speed=self.config.weather.wind_speed,
            ffmc=self.config.ffmc if self.config.ffmc is not None else 85.0,
            dmc=self.config.dmc if self.config.dmc is not None else 40.0,
            dc=self.config.dc if self.config.dc is not None else 200.0,
        )

        # Build fuel breakdown
        fuel_breakdown: dict[str, float] = {}
        if self.fuel_grid is not None:
            counts: dict[str, int] = defaultdict(int)
            total = 0
            for v in front:
                ft = self.fuel_grid.get_fuel_at(v.lat, v.lng)
                if ft is not None:
                    counts[ft.value] += 1
                    total += 1
            if total > 0:
                fuel_breakdown = {k: v / total for k, v in counts.items()}
        else:
            fuel_breakdown = {self.default_fuel.value: 1.0}

        # Perimeter as list of (lat, lng)
        perimeter = vertices_to_polygon(front)

        return SimulationFrame(
            time_hours=time_hours,
            perimeter=perimeter,
            area_ha=area_ha,
            head_ros_m_min=fbp.ros_final,
            max_hfi_kw_m=fbp.hfi,
            fire_type=fbp.fire_type,
            flame_length_m=fbp.flame_length,
            fuel_breakdown=fuel_breakdown,
        )
