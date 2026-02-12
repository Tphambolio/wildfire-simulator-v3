"""Tests for the FBP calculator.

Validates fire behavior predictions for all 18 Canadian fuel types
against expected ranges from ST-X-3 tables and field observations.
"""

import pytest

from firesim.fbp.calculator import (
    calculate_bui,
    calculate_bui_effect,
    calculate_fbp,
    calculate_grass_curing_factor,
    calculate_isi,
)
from firesim.fbp.constants import FuelType
from firesim.types import FireType


class TestISI:
    """Test Initial Spread Index calculation."""

    def test_isi_zero_wind(self):
        """ISI at zero wind should be driven by FFMC only."""
        isi = calculate_isi(ffmc=90.0, wind_speed=0.0)
        assert isi > 0.0
        assert isi < 10.0

    def test_isi_increases_with_wind(self):
        """ISI should increase with wind speed."""
        isi_low = calculate_isi(ffmc=90.0, wind_speed=10.0)
        isi_high = calculate_isi(ffmc=90.0, wind_speed=30.0)
        assert isi_high > isi_low

    def test_isi_increases_with_ffmc(self):
        """Higher FFMC (drier fuel) should produce higher ISI."""
        isi_wet = calculate_isi(ffmc=70.0, wind_speed=20.0)
        isi_dry = calculate_isi(ffmc=95.0, wind_speed=20.0)
        assert isi_dry > isi_wet

    def test_isi_known_value(self):
        """ISI for FFMC=90, wind=20 should be in expected range."""
        isi = calculate_isi(ffmc=90.0, wind_speed=20.0)
        assert 8.0 < isi < 15.0


class TestBUI:
    """Test Buildup Index calculation."""

    def test_bui_zero_inputs(self):
        """BUI should be 0 when both DMC and DC are 0."""
        assert calculate_bui(0.0, 0.0) == 0.0

    def test_bui_low_dmc(self):
        """When DMC << DC, the lower formula applies."""
        bui = calculate_bui(dmc=20.0, dc=200.0)
        assert bui > 0.0
        assert bui < 40.0

    def test_bui_increases_with_dmc(self):
        """BUI should increase as DMC increases."""
        bui_low = calculate_bui(dmc=20.0, dc=200.0)
        bui_high = calculate_bui(dmc=60.0, dc=200.0)
        assert bui_high > bui_low

    def test_bui_never_negative(self):
        """BUI should never be negative."""
        bui = calculate_bui(dmc=1.0, dc=1.0)
        assert bui >= 0.0


class TestBUIEffect:
    """Test BUI effect on rate of spread."""

    def test_bui_effect_at_bui0(self):
        """BUI effect should be ~1.0 at BUI = BUI0."""
        be = calculate_bui_effect(bui=64.0, q=0.70, bui0=64.0)
        assert abs(be - 1.0) < 0.01

    def test_bui_effect_above_bui0(self):
        """BUI effect should be >1.0 above BUI0."""
        be = calculate_bui_effect(bui=100.0, q=0.70, bui0=64.0)
        assert be > 1.0

    def test_bui_effect_below_bui0(self):
        """BUI effect should be <1.0 below BUI0."""
        be = calculate_bui_effect(bui=30.0, q=0.70, bui0=64.0)
        assert be < 1.0

    def test_bui_effect_q_equals_one(self):
        """When q=1.0, BUI has no effect (grass types)."""
        be = calculate_bui_effect(bui=50.0, q=1.0, bui0=1.0)
        assert be == 1.0


class TestGrassCuring:
    """Test grass curing factor for O1a/O1b types."""

    def test_green_grass_no_spread(self):
        """Fully green grass (0% curing) should not spread."""
        cf = calculate_grass_curing_factor(0.0)
        assert cf == 0.0

    def test_moderate_curing(self):
        """60% curing should allow moderate spread."""
        cf = calculate_grass_curing_factor(60.0)
        assert 0.1 < cf < 0.5

    def test_high_curing(self):
        """90% curing should allow significant spread."""
        cf = calculate_grass_curing_factor(90.0)
        assert cf > 0.5

    def test_full_curing(self):
        """100% curing should give maximum curing factor."""
        cf = calculate_grass_curing_factor(100.0)
        assert cf > 0.6

    def test_threshold_at_58(self):
        """Below ~58% curing, fire spread is negligible."""
        cf = calculate_grass_curing_factor(50.0)
        assert cf < 0.05


# FBP validation for each fuel type.
# Expected ROS ranges based on ST-X-3 Table 6 and field observations.
# Conditions: FFMC=90, DMC=45, DC=300, wind=20 km/h, flat terrain.
_STANDARD_CONDITIONS = {
    "ffmc": 90.0,
    "dmc": 45.0,
    "dc": 300.0,
    "wind_speed": 20.0,
}


class TestFBPAllFuelTypes:
    """Validate FBP output for all 18 fuel types under standard conditions."""

    @pytest.mark.parametrize(
        "fuel_type,min_ros,max_ros",
        [
            (FuelType.C1, 1.0, 15.0),
            (FuelType.C2, 3.0, 25.0),
            (FuelType.C3, 3.0, 20.0),
            (FuelType.C4, 3.0, 25.0),
            (FuelType.C5, 0.5, 10.0),
            (FuelType.C6, 0.5, 12.0),
            (FuelType.C7, 0.5, 10.0),
            (FuelType.D1, 0.5, 8.0),
            (FuelType.D2, 0.1, 5.0),
            (FuelType.M1, 1.0, 18.0),
            (FuelType.M2, 0.5, 12.0),
            (FuelType.M3, 3.0, 60.0),
            (FuelType.M4, 1.0, 15.0),
            (FuelType.O1a, 1.0, 30.0),
            (FuelType.O1b, 1.0, 40.0),
            (FuelType.S1, 1.0, 25.0),
            (FuelType.S2, 0.5, 15.0),
            (FuelType.S3, 1.0, 25.0),
        ],
    )
    def test_ros_within_expected_range(self, fuel_type, min_ros, max_ros):
        """Surface ROS should be within expected range for standard conditions."""
        result = calculate_fbp(
            fuel_type=fuel_type,
            wind_speed=_STANDARD_CONDITIONS["wind_speed"],
            ffmc=_STANDARD_CONDITIONS["ffmc"],
            dmc=_STANDARD_CONDITIONS["dmc"],
            dc=_STANDARD_CONDITIONS["dc"],
        )
        assert min_ros <= result.ros_surface <= max_ros, (
            f"{fuel_type.value}: ROS {result.ros_surface:.2f} outside [{min_ros}, {max_ros}]"
        )

    @pytest.mark.parametrize("fuel_type", list(FuelType))
    def test_all_fuel_types_produce_output(self, fuel_type):
        """Every fuel type should produce a valid FBPResult without errors."""
        result = calculate_fbp(
            fuel_type=fuel_type,
            wind_speed=20.0,
            ffmc=90.0,
            dmc=45.0,
            dc=300.0,
        )
        assert result.ros_surface >= 0.0
        assert result.ros_final >= 0.0
        assert result.hfi >= 0.0
        assert 0.0 <= result.cfb <= 1.0
        assert result.fire_type in FireType
        assert result.flame_length >= 0.0
        assert result.tfc >= 0.0

    @pytest.mark.parametrize("fuel_type", list(FuelType))
    def test_ros_increases_with_wind(self, fuel_type):
        """ROS should generally increase with wind speed for all types."""
        ros_low = calculate_fbp(fuel_type, 5.0, 90.0, 45.0, 300.0).ros_surface
        ros_high = calculate_fbp(fuel_type, 40.0, 90.0, 45.0, 300.0).ros_surface
        assert ros_high >= ros_low, (
            f"{fuel_type.value}: ROS at 40 km/h ({ros_high:.2f}) < ROS at 5 km/h ({ros_low:.2f})"
        )


class TestFBPCrownFire:
    """Test crown fire behavior in FBP results."""

    def test_c2_high_intensity_crowns(self):
        """C2 Boreal Spruce at high intensity should produce crown fire."""
        result = calculate_fbp("C2", 40.0, 95.0, 80.0, 500.0)
        assert result.cfb > 0.0
        assert result.fire_type in (FireType.PASSIVE_CROWN, FireType.ACTIVE_CROWN)

    def test_d1_never_crowns(self):
        """D1 Leafless Aspen has no canopy, should never crown."""
        result = calculate_fbp("D1", 40.0, 95.0, 80.0, 500.0)
        assert result.cfb == 0.0
        assert result.fire_type == FireType.SURFACE

    def test_grass_never_crowns(self):
        """Grass types have no canopy, should never crown."""
        result = calculate_fbp("O1b", 40.0, 95.0, 80.0, 500.0)
        assert result.cfb == 0.0
        assert result.fire_type == FireType.SURFACE

    def test_crown_fire_increases_ros(self):
        """Crown fires should have higher final ROS than surface ROS."""
        result = calculate_fbp("C2", 40.0, 95.0, 80.0, 500.0)
        if result.cfb > 0.0:
            assert result.ros_final >= result.ros_surface


class TestFBPSlope:
    """Test slope integration in FBP."""

    def test_upslope_increases_ros(self):
        """Upslope should increase ROS."""
        flat = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0, slope=0.0)
        slope = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0, slope=50.0)
        assert slope.ros_surface > flat.ros_surface

    def test_slope_capped_at_2x(self):
        """Slope factor should not exceed 2x (Butler 2007 cap)."""
        flat = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0, slope=0.0)
        steep = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0, slope=100.0)
        ratio = steep.ros_surface / flat.ros_surface
        assert ratio <= 2.05  # small tolerance for floating point


class TestFBPMixedwood:
    """Test M1/M2 mixedwood blending."""

    def test_m1_pc100_matches_c2(self):
        """M1 at 100% conifer should approximate C2 behavior."""
        m1 = calculate_fbp("M1", 20.0, 90.0, 45.0, 300.0, pc=100.0)
        c2 = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0)
        assert abs(m1.ros_surface - c2.ros_surface) / c2.ros_surface < 0.1

    def test_m1_pc0_matches_d1(self):
        """M1 at 0% conifer should approximate D1 behavior."""
        m1 = calculate_fbp("M1", 20.0, 90.0, 45.0, 300.0, pc=0.0)
        d1 = calculate_fbp("D1", 20.0, 90.0, 45.0, 300.0)
        assert abs(m1.ros_surface - d1.ros_surface) / max(d1.ros_surface, 0.1) < 0.15

    def test_m1_intermediate_blends(self):
        """M1 at 50% conifer should be between C2 and D1."""
        m1 = calculate_fbp("M1", 20.0, 90.0, 45.0, 300.0, pc=50.0)
        c2 = calculate_fbp("C2", 20.0, 90.0, 45.0, 300.0)
        d1 = calculate_fbp("D1", 20.0, 90.0, 45.0, 300.0)
        assert d1.ros_surface <= m1.ros_surface <= c2.ros_surface
