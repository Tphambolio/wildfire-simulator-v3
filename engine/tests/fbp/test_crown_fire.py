"""Tests for crown fire initiation and behavior."""

import pytest

from firesim.fbp.constants import FuelType, FUEL_TYPES
from firesim.fbp.crown_fire import (
    calculate_critical_surface_intensity,
    calculate_crown_fraction_burned,
    classify_fire_type,
)
from firesim.types import FireType


class TestCriticalSurfaceIntensity:
    """Test Van Wagner (1977) critical intensity calculation."""

    def test_zero_cbh_returns_zero(self):
        """No canopy means no crown fire threshold."""
        csi = calculate_critical_surface_intensity(cbh=0.0)
        assert csi == 0.0

    def test_low_cbh_lower_threshold(self):
        """Lower crown base height should have lower CSI."""
        csi_low = calculate_critical_surface_intensity(cbh=2.0)
        csi_high = calculate_critical_surface_intensity(cbh=10.0)
        assert csi_low < csi_high

    def test_c2_csi_reasonable(self):
        """C2 (CBH=3m) should have CSI between 200-1500 kW/m."""
        csi = calculate_critical_surface_intensity(cbh=3.0, fmc=100.0)
        assert 200.0 < csi < 1500.0

    def test_c5_high_cbh_high_csi(self):
        """C5 (CBH=18m) should have very high CSI (hard to crown)."""
        csi = calculate_critical_surface_intensity(cbh=18.0, fmc=100.0)
        assert csi > 5000.0

    def test_fmc_effect(self):
        """Higher FMC should increase CSI (wetter canopy harder to ignite)."""
        csi_dry = calculate_critical_surface_intensity(cbh=5.0, fmc=80.0)
        csi_wet = calculate_critical_surface_intensity(cbh=5.0, fmc=120.0)
        assert csi_wet > csi_dry


class TestCrownFractionBurned:
    """Test CFB calculation."""

    def test_below_threshold_no_crown(self):
        """SFI below CSI should produce zero CFB."""
        cfb = calculate_crown_fraction_burned(sfi=500.0, csi=1000.0)
        assert cfb == 0.0

    def test_above_threshold_positive_cfb(self):
        """SFI above CSI should produce positive CFB."""
        cfb = calculate_crown_fraction_burned(sfi=2000.0, csi=1000.0)
        assert cfb > 0.0

    def test_cfb_bounded_zero_to_one(self):
        """CFB should always be between 0 and 1."""
        cfb = calculate_crown_fraction_burned(sfi=50000.0, csi=100.0)
        assert 0.0 <= cfb <= 1.0

    def test_zero_csi_no_crown(self):
        """Zero CSI (no canopy) means no crown fire."""
        cfb = calculate_crown_fraction_burned(sfi=5000.0, csi=0.0)
        assert cfb == 0.0


class TestFireTypeClassification:
    """Test fire type classification from CFB."""

    def test_surface_fire(self):
        assert classify_fire_type(0.0) == FireType.SURFACE

    def test_torching(self):
        assert classify_fire_type(0.05) == FireType.SURFACE_WITH_TORCHING

    def test_passive_crown(self):
        assert classify_fire_type(0.5) == FireType.PASSIVE_CROWN

    def test_active_crown(self):
        assert classify_fire_type(0.95) == FireType.ACTIVE_CROWN
