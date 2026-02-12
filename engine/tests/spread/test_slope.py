"""Tests for directional slope factor calculation."""

import pytest

from firesim.spread.slope import calculate_directional_slope_factor, calculate_slope_factor


class TestDirectionalSlopeFactor:
    """Test directional slope factor with aspect and spread direction."""

    def test_flat_terrain_no_effect(self):
        """Flat terrain (0% slope) should give factor 1.0."""
        sf = calculate_directional_slope_factor(0.0, 180.0, 180.0)
        assert sf == 1.0

    def test_upslope_increases_ros(self):
        """Spreading directly upslope should give factor > 1.0."""
        sf = calculate_directional_slope_factor(50.0, 180.0, 180.0)
        assert sf > 1.0

    def test_downslope_decreases_ros(self):
        """Spreading directly downslope should give factor < 1.0."""
        sf = calculate_directional_slope_factor(50.0, 180.0, 0.0)
        assert sf < 1.0
        assert sf >= 0.7  # Anderson (1983) minimum

    def test_crossslope_neutral(self):
        """Spreading perpendicular to slope should give factor ~1.0."""
        sf = calculate_directional_slope_factor(50.0, 180.0, 90.0)
        assert abs(sf - 1.0) < 0.01

    def test_butler_cap_at_2(self):
        """Slope factor should not exceed 2.0 (Butler 2007)."""
        sf = calculate_directional_slope_factor(100.0, 0.0, 0.0)
        assert sf <= 2.0

    def test_symmetry(self):
        """Upslope factor should be same regardless of aspect orientation."""
        sf_north = calculate_directional_slope_factor(50.0, 0.0, 0.0)
        sf_south = calculate_directional_slope_factor(50.0, 180.0, 180.0)
        assert abs(sf_north - sf_south) < 0.01

    def test_oblique_upslope_partial_effect(self):
        """45-degree oblique upslope should give partial effect."""
        sf_direct = calculate_directional_slope_factor(50.0, 180.0, 180.0)
        sf_oblique = calculate_directional_slope_factor(50.0, 180.0, 135.0)
        assert 1.0 < sf_oblique < sf_direct


class TestSimpleSlopeFactor:
    """Test non-directional slope factor."""

    def test_flat_no_effect(self):
        assert calculate_slope_factor(0.0) == 1.0

    def test_moderate_slope(self):
        sf = calculate_slope_factor(30.0)
        assert 1.0 < sf <= 2.0

    def test_capped_at_2(self):
        sf = calculate_slope_factor(100.0)
        assert sf == 2.0

    def test_negative_slope_no_effect(self):
        sf = calculate_slope_factor(-10.0)
        assert sf == 1.0
