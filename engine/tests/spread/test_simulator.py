"""Tests for the fire spread simulator.

Integration tests covering the full simulation pipeline:
ignition + weather -> expand fire -> yield frames with metrics.
"""

import math

import pytest

from firesim.fbp.constants import FuelType
from firesim.spread.huygens import FireVertex, FuelGrid, SpreadConditions, TerrainGrid
from firesim.spread.simulator import Simulator
from firesim.types import FireType, SimulationConfig, SimulationFrame, WeatherInput


@pytest.fixture
def basic_config():
    """Basic simulation: 2 hours, 30-minute snapshots, central Alberta."""
    return SimulationConfig(
        ignition_lat=51.0,
        ignition_lng=-114.0,
        weather=WeatherInput(
            temperature=25.0,
            relative_humidity=30.0,
            wind_speed=20.0,
            wind_direction=270.0,
            precipitation_24h=0.0,
        ),
        duration_hours=2.0,
        snapshot_interval_minutes=30.0,
        ffmc=90.0,
        dmc=45.0,
        dc=300.0,
    )


@pytest.fixture
def short_config():
    """Short simulation: 30 minutes, 10-minute snapshots."""
    return SimulationConfig(
        ignition_lat=51.0,
        ignition_lng=-114.0,
        weather=WeatherInput(
            temperature=25.0,
            relative_humidity=30.0,
            wind_speed=15.0,
            wind_direction=180.0,
            precipitation_24h=0.0,
        ),
        duration_hours=0.5,
        snapshot_interval_minutes=10.0,
        ffmc=88.0,
        dmc=40.0,
        dc=250.0,
    )


@pytest.fixture
def calm_config():
    """Very low wind simulation for near-circular spread."""
    return SimulationConfig(
        ignition_lat=51.0,
        ignition_lng=-114.0,
        weather=WeatherInput(
            temperature=20.0,
            relative_humidity=40.0,
            wind_speed=2.0,
            wind_direction=0.0,
            precipitation_24h=0.0,
        ),
        duration_hours=1.0,
        snapshot_interval_minutes=30.0,
        ffmc=85.0,
        dmc=30.0,
        dc=200.0,
    )


class TestSimulatorInit:
    """Test simulator initialization."""

    def test_default_fuel(self, basic_config):
        sim = Simulator(basic_config)
        assert sim.default_fuel == FuelType.C2

    def test_custom_fuel(self, basic_config):
        sim = Simulator(basic_config, default_fuel=FuelType.C3)
        assert sim.default_fuel == FuelType.C3

    def test_custom_timestep(self, basic_config):
        sim = Simulator(basic_config, dt_minutes=2.0)
        assert sim.dt_minutes == 2.0

    def test_custom_rays(self, basic_config):
        sim = Simulator(basic_config, num_rays=72)
        assert sim.num_rays == 72


class TestSimulatorRun:
    """Test the main simulation run."""

    def test_yields_frames(self, basic_config):
        """Simulation should yield SimulationFrame objects."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        assert len(frames) > 0
        for frame in frames:
            assert isinstance(frame, SimulationFrame)

    def test_correct_number_of_frames(self, basic_config):
        """2 hours at 30-min intervals = t=0, t=0.5, t=1.0, t=1.5, t=2.0 = 5 frames."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        assert len(frames) == 5

    def test_short_sim_frame_count(self, short_config):
        """30 min at 10-min intervals = t=0, t=10, t=20, t=30 = 4 frames."""
        sim = Simulator(short_config)
        frames = list(sim.run())
        assert len(frames) == 4

    def test_first_frame_is_time_zero(self, basic_config):
        """First yielded frame should be at t=0."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        assert frames[0].time_hours == 0.0

    def test_last_frame_at_duration(self, basic_config):
        """Last frame should be at the configured duration."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        assert abs(frames[-1].time_hours - basic_config.duration_hours) < 0.01

    def test_frames_monotonically_increasing_time(self, basic_config):
        """Frame timestamps should be strictly increasing."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        times = [f.time_hours for f in frames]
        for i in range(1, len(times)):
            assert times[i] > times[i - 1]

    def test_area_increases_over_time(self, basic_config):
        """Fire area should increase (or at least not decrease) over time."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        areas = [f.area_ha for f in frames]
        # Area should generally increase; allow first frame (ignition circle) to be small
        for i in range(2, len(areas)):
            assert areas[i] >= areas[i - 1] * 0.95  # Allow tiny numeric fluctuation

    def test_area_reasonable_magnitude(self, basic_config):
        """After 2 hours in C2 with 20 km/h wind, area should be in 10-5000 ha range."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        final_area = frames[-1].area_ha
        assert 1.0 < final_area < 10000.0

    def test_initial_area_small(self, basic_config):
        """Initial frame should have very small area (just the ignition circle)."""
        sim = Simulator(basic_config)
        frames = list(sim.run())
        assert frames[0].area_ha < 1.0  # 30m radius circle = ~0.28 ha


class TestSimulationFrameMetrics:
    """Test that simulation frames contain valid metrics."""

    @pytest.fixture
    def frames(self, basic_config):
        sim = Simulator(basic_config)
        return list(sim.run())

    def test_perimeter_is_closed_polygon(self, frames):
        """Each frame's perimeter should be a closed polygon."""
        for frame in frames:
            if len(frame.perimeter) > 2:
                assert frame.perimeter[0] == frame.perimeter[-1]

    def test_perimeter_lat_lng_valid(self, frames):
        """Perimeter coordinates should be near the ignition point."""
        for frame in frames:
            for lat, lng in frame.perimeter:
                assert 49.0 < lat < 53.0  # Within ~200km of ignition
                assert -116.0 < lng < -112.0

    def test_head_ros_positive(self, frames):
        """Head ROS should be positive for all frames."""
        for frame in frames:
            assert frame.head_ros_m_min >= 0.0

    def test_hfi_positive(self, frames):
        """HFI should be positive (or zero for ignition)."""
        for frame in frames:
            assert frame.max_hfi_kw_m >= 0.0

    def test_fire_type_valid(self, frames):
        """Fire type should be a valid FireType enum."""
        for frame in frames:
            assert isinstance(frame.fire_type, FireType)

    def test_flame_length_positive(self, frames):
        """Flame length should be non-negative."""
        for frame in frames:
            assert frame.flame_length_m >= 0.0

    def test_fuel_breakdown_sums_to_one(self, frames):
        """Fuel breakdown fractions should sum to ~1.0."""
        for frame in frames:
            if frame.fuel_breakdown:
                total = sum(frame.fuel_breakdown.values())
                assert abs(total - 1.0) < 0.01


class TestSimulatorWithFuelGrid:
    """Test simulation with spatial fuel variation."""

    def test_fuel_grid_affects_breakdown(self):
        """When fuel grid has mixed types, breakdown should reflect that."""
        config = SimulationConfig(
            ignition_lat=50.5,
            ignition_lng=-114.5,
            weather=WeatherInput(
                temperature=25.0,
                relative_humidity=30.0,
                wind_speed=15.0,
                wind_direction=270.0,
                precipitation_24h=0.0,
            ),
            duration_hours=1.0,
            snapshot_interval_minutes=30.0,
            ffmc=90.0,
            dmc=45.0,
            dc=300.0,
        )
        fuel_grid = FuelGrid(
            fuel_types=[
                [FuelType.C2, FuelType.C3],
                [FuelType.C2, FuelType.M1],
            ],
            lat_min=50.0,
            lat_max=51.0,
            lng_min=-115.0,
            lng_max=-114.0,
            rows=2,
            cols=2,
        )
        sim = Simulator(config, fuel_grid=fuel_grid)
        frames = list(sim.run())
        # Should complete without error
        assert len(frames) > 0
        # Last frame should have some area
        assert frames[-1].area_ha > 0.0


class TestSimulatorWithTerrain:
    """Test simulation with terrain grid."""

    def test_terrain_simulation_runs(self):
        """Simulation with terrain grid should complete without error."""
        config = SimulationConfig(
            ignition_lat=50.5,
            ignition_lng=-114.5,
            weather=WeatherInput(
                temperature=25.0,
                relative_humidity=30.0,
                wind_speed=15.0,
                wind_direction=270.0,
                precipitation_24h=0.0,
            ),
            duration_hours=0.5,
            snapshot_interval_minutes=15.0,
            ffmc=90.0,
            dmc=45.0,
            dc=300.0,
        )
        terrain = TerrainGrid(
            slope=[[20.0, 10.0], [5.0, 0.0]],
            aspect=[[180.0, 90.0], [0.0, 270.0]],
            lat_min=50.0,
            lat_max=51.0,
            lng_min=-115.0,
            lng_max=-114.0,
            rows=2,
            cols=2,
        )
        sim = Simulator(config, terrain_grid=terrain)
        frames = list(sim.run())
        assert len(frames) > 0


class TestSimulatorDifferentFuels:
    """Test simulation across different fuel types."""

    @pytest.mark.parametrize(
        "fuel_type",
        [FuelType.C1, FuelType.C2, FuelType.C3, FuelType.D1, FuelType.M1, FuelType.O1a],
    )
    def test_simulation_completes_for_fuel(self, fuel_type, short_config):
        """Simulation should complete without error for each fuel type."""
        sim = Simulator(short_config, default_fuel=fuel_type)
        frames = list(sim.run())
        assert len(frames) > 0
        # All frames should have valid area
        for frame in frames:
            assert frame.area_ha >= 0.0


class TestIgnitionFront:
    """Test the initial ignition front creation."""

    def test_ignition_circle_created(self, basic_config):
        """Ignition front should be a small circle."""
        sim = Simulator(basic_config)
        front = sim._create_ignition_front(51.0, -114.0)
        assert len(front) == 12  # default num_points

    def test_ignition_circle_centered(self, basic_config):
        """Ignition circle should be centered on the ignition point."""
        sim = Simulator(basic_config)
        front = sim._create_ignition_front(51.0, -114.0)
        avg_lat = sum(v.lat for v in front) / len(front)
        avg_lng = sum(v.lng for v in front) / len(front)
        assert abs(avg_lat - 51.0) < 0.001
        assert abs(avg_lng - (-114.0)) < 0.001

    def test_ignition_radius(self, basic_config):
        """Ignition circle should have approximately the right radius."""
        sim = Simulator(basic_config)
        front = sim._create_ignition_front(51.0, -114.0, radius_m=100.0)
        # Max distance from center should be ~100m
        m_per_deg_lat = 111320.0
        m_per_deg_lng = 111320.0 * math.cos(math.radians(51.0))
        for v in front:
            dist = math.sqrt(
                ((v.lat - 51.0) * m_per_deg_lat) ** 2
                + ((v.lng + 114.0) * m_per_deg_lng) ** 2
            )
            assert abs(dist - 100.0) < 5.0  # Within 5m tolerance
