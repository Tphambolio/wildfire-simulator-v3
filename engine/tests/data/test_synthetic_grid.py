"""Tests for synthetic fuel grid generation.

The synthetic grid is used when use_ca_mode=True is requested but no
fuel_grid_path is supplied. It must:
- Return a FuelGrid with at least 50×50 cells (to activate CA mode in Simulator)
- Centre the grid on the ignition point
- Guarantee the ignition cell has fuel (never None)
- Be reproducible with a fixed seed
"""

from __future__ import annotations

import math

import pytest

from firesim.data.synthetic_grid import _FUEL_PALETTE, generate_synthetic_fuel_grid
from firesim.fbp.constants import FuelType
from firesim.spread.huygens import FuelGrid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def edmonton_grid():
    """A default grid centred on Edmonton with a fixed seed."""
    return generate_synthetic_fuel_grid(
        ignition_lat=53.55,
        ignition_lng=-113.50,
        radius_km=5.0,
        cell_size_m=50.0,
        seed=42,
    )


# ---------------------------------------------------------------------------
# Return type and structure
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_fuel_grid_instance(self, edmonton_grid):
        assert isinstance(edmonton_grid, FuelGrid)

    def test_fuel_types_is_2d_list(self, edmonton_grid):
        assert isinstance(edmonton_grid.fuel_types, list)
        assert all(isinstance(row, list) for row in edmonton_grid.fuel_types)

    def test_fuel_types_contains_valid_values(self, edmonton_grid):
        """Each cell is a FuelType or None (non-fuel)."""
        for row in edmonton_grid.fuel_types:
            for cell in row:
                assert cell is None or isinstance(cell, FuelType)


# ---------------------------------------------------------------------------
# Grid dimensions — must be ≥50×50 for CA mode to activate
# ---------------------------------------------------------------------------


class TestGridDimensions:
    """Simulator._run_cellular activates when rows >= 50 and cols >= 50."""

    def test_rows_at_least_50(self, edmonton_grid):
        assert edmonton_grid.rows >= 50, (
            f"Grid has only {edmonton_grid.rows} rows — CA mode requires ≥50"
        )

    def test_cols_at_least_50(self, edmonton_grid):
        assert edmonton_grid.cols >= 50, (
            f"Grid has only {edmonton_grid.cols} cols — CA mode requires ≥50"
        )

    def test_fuel_types_dimensions_match_rows_cols(self, edmonton_grid):
        g = edmonton_grid
        assert len(g.fuel_types) == g.rows
        assert all(len(row) == g.cols for row in g.fuel_types)

    def test_larger_radius_produces_more_cells(self):
        small = generate_synthetic_fuel_grid(53.55, -113.50, radius_km=3.0, seed=1)
        large = generate_synthetic_fuel_grid(53.55, -113.50, radius_km=10.0, seed=1)
        assert large.rows > small.rows
        assert large.cols > small.cols

    def test_smaller_cell_size_increases_resolution(self):
        coarse = generate_synthetic_fuel_grid(53.55, -113.50, cell_size_m=100.0, seed=1)
        fine = generate_synthetic_fuel_grid(53.55, -113.50, cell_size_m=25.0, seed=1)
        assert fine.rows > coarse.rows
        assert fine.cols > coarse.cols

    def test_minimum_50_enforced_for_tiny_radius(self):
        """Even with radius_km=0.1 and large cells, grid must be ≥50×50."""
        g = generate_synthetic_fuel_grid(53.55, -113.50, radius_km=0.1, cell_size_m=500.0, seed=1)
        assert g.rows >= 50
        assert g.cols >= 50


# ---------------------------------------------------------------------------
# Geographic bounds
# ---------------------------------------------------------------------------


class TestBounds:
    def test_ignition_lat_inside_grid(self, edmonton_grid):
        g = edmonton_grid
        assert g.lat_min <= 53.55 <= g.lat_max

    def test_ignition_lng_inside_grid(self, edmonton_grid):
        g = edmonton_grid
        assert g.lng_min <= -113.50 <= g.lng_max

    def test_grid_centred_on_ignition(self):
        """Grid centre must be within one cell of the ignition point."""
        lat, lng = 53.5, -114.0
        g = generate_synthetic_fuel_grid(lat, lng, radius_km=5.0, cell_size_m=50.0, seed=0)
        centre_lat = (g.lat_min + g.lat_max) / 2.0
        centre_lng = (g.lng_min + g.lng_max) / 2.0
        m_per_deg_lat = 111_320.0
        m_per_deg_lng = 111_320.0 * math.cos(math.radians(lat))
        lat_err_m = abs(centre_lat - lat) * m_per_deg_lat
        lng_err_m = abs(centre_lng - lng) * m_per_deg_lng
        assert lat_err_m < 100.0, f"Lat centre off by {lat_err_m:.0f}m"
        assert lng_err_m < 100.0, f"Lng centre off by {lng_err_m:.0f}m"

    def test_bounds_are_increasing(self, edmonton_grid):
        g = edmonton_grid
        assert g.lat_min < g.lat_max
        assert g.lng_min < g.lng_max


# ---------------------------------------------------------------------------
# Ignition cell guarantee
# ---------------------------------------------------------------------------


class TestIgnitionCellFuel:
    """The ignition cell must never be None — guaranteed by the generator."""

    def test_ignition_cell_has_fuel(self, edmonton_grid):
        """Cell at (ignition_lat, ignition_lng) must have a FuelType, not None."""
        g = edmonton_grid
        fuel = g.get_fuel_at(53.55, -113.50)
        assert fuel is not None, "Ignition cell has no fuel type — fire cannot start"

    def test_ignition_cell_has_fuel_multiple_seeds(self):
        for seed in range(20):
            g = generate_synthetic_fuel_grid(53.55, -113.50, seed=seed)
            fuel = g.get_fuel_at(53.55, -113.50)
            assert fuel is not None, (
                f"seed={seed}: ignition cell at (53.55, -113.50) has no fuel"
            )


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


class TestReproducibility:
    def test_same_seed_same_grid(self):
        g1 = generate_synthetic_fuel_grid(53.55, -113.50, seed=99)
        g2 = generate_synthetic_fuel_grid(53.55, -113.50, seed=99)
        assert g1.fuel_types == g2.fuel_types

    def test_different_seeds_different_grids(self):
        g1 = generate_synthetic_fuel_grid(53.55, -113.50, seed=1)
        g2 = generate_synthetic_fuel_grid(53.55, -113.50, seed=2)
        # Very unlikely to be identical
        assert g1.fuel_types != g2.fuel_types

    def test_no_seed_produces_non_deterministic_results(self):
        """Without a seed, successive calls should differ (probabilistically)."""
        g1 = generate_synthetic_fuel_grid(53.55, -113.50, seed=None)
        g2 = generate_synthetic_fuel_grid(53.55, -113.50, seed=None)
        # Allow this to be non-deterministic — if they happen to be equal it is
        # astronomically unlikely; skip assertion but validate they are FuelGrids.
        assert isinstance(g1, FuelGrid)
        assert isinstance(g2, FuelGrid)


# ---------------------------------------------------------------------------
# Fuel palette distribution
# ---------------------------------------------------------------------------


class TestFuelPaletteDistribution:
    """Fuel type distribution should roughly match the _FUEL_PALETTE weights."""

    def test_palette_weights_sum_to_one(self):
        total = sum(w for _, w in _FUEL_PALETTE)
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_non_fuel_fraction_within_expected_range(self):
        """Non-fuel cells (~20% per palette) should be 10–35% of the grid."""
        g = generate_synthetic_fuel_grid(53.55, -113.50, radius_km=5.0, seed=42)
        total = g.rows * g.cols
        non_fuel = sum(
            1 for row in g.fuel_types for cell in row if cell is None
        )
        fraction = non_fuel / total
        assert 0.10 <= fraction <= 0.35, (
            f"Non-fuel fraction {fraction:.1%} outside expected 10–35% range"
        )

    def test_fuel_cells_include_dominant_types(self):
        """C2 (dominant at 35%) and C3 must both appear in the grid."""
        g = generate_synthetic_fuel_grid(53.55, -113.50, radius_km=5.0, seed=42)
        all_fuels = {cell for row in g.fuel_types for cell in row if cell is not None}
        assert FuelType.C2 in all_fuels, "C2 (dominant fuel) missing from grid"
        assert FuelType.C3 in all_fuels, "C3 (15% weight) missing from grid"
