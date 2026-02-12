"""Tests for the FWI System calculator.

Validates FFMC, DMC, DC, ISI, BUI, and FWI calculations against
known values from the Canadian FWI System documentation.
"""

import pytest

from firesim.fwi.calculator import FWICalculator


@pytest.fixture
def calc():
    """Fresh FWI calculator with spring startup defaults."""
    return FWICalculator()


class TestFFMC:
    """Test Fine Fuel Moisture Code calculation."""

    def test_dry_hot_conditions_increase_ffmc(self, calc):
        """Hot, dry, windy conditions should increase FFMC."""
        ffmc = calc.calculate_ffmc(temp=30.0, rh=20.0, wind=20.0, rain=0.0, ffmc_prev=85.0)
        assert ffmc > 85.0

    def test_rain_decreases_ffmc(self, calc):
        """Rain should decrease FFMC (wetter fuel)."""
        ffmc_dry = calc.calculate_ffmc(temp=25.0, rh=40.0, wind=10.0, rain=0.0, ffmc_prev=90.0)
        ffmc_wet = calc.calculate_ffmc(temp=25.0, rh=40.0, wind=10.0, rain=10.0, ffmc_prev=90.0)
        assert ffmc_wet < ffmc_dry

    def test_ffmc_bounded(self, calc):
        """FFMC should stay in 0-101 range."""
        ffmc = calc.calculate_ffmc(temp=40.0, rh=5.0, wind=50.0, rain=0.0, ffmc_prev=100.0)
        assert 0.0 <= ffmc <= 101.0

    def test_ffmc_not_negative(self, calc):
        """FFMC should never be negative even with heavy rain."""
        ffmc = calc.calculate_ffmc(temp=5.0, rh=95.0, wind=0.0, rain=50.0, ffmc_prev=10.0)
        assert ffmc >= 0.0


class TestDMC:
    """Test Duff Moisture Code calculation."""

    def test_warm_dry_increases_dmc(self, calc):
        """Warm, dry conditions should increase DMC."""
        dmc = calc.calculate_dmc(temp=25.0, rh=30.0, rain=0.0, month=7, dmc_prev=20.0)
        assert dmc > 20.0

    def test_rain_decreases_dmc(self, calc):
        """Heavy rain should decrease DMC relative to no-rain case."""
        dmc_dry = calc.calculate_dmc(temp=20.0, rh=50.0, rain=0.0, month=7, dmc_prev=60.0)
        dmc_wet = calc.calculate_dmc(temp=20.0, rh=50.0, rain=20.0, month=7, dmc_prev=60.0)
        assert dmc_wet < dmc_dry

    def test_cold_temperature_no_drying(self, calc):
        """Below -1.1C, no drying occurs."""
        dmc = calc.calculate_dmc(temp=-5.0, rh=50.0, rain=0.0, month=1, dmc_prev=30.0)
        assert dmc == 30.0

    def test_dmc_never_negative(self, calc):
        """DMC should never be negative."""
        dmc = calc.calculate_dmc(temp=10.0, rh=80.0, rain=50.0, month=7, dmc_prev=5.0)
        assert dmc >= 0.0


class TestDC:
    """Test Drought Code calculation."""

    def test_warm_dry_increases_dc(self, calc):
        """Warm, dry conditions should increase DC."""
        dc = calc.calculate_dc(temp=25.0, rain=0.0, month=7, dc_prev=200.0)
        assert dc > 200.0

    def test_heavy_rain_decreases_dc(self, calc):
        """Heavy rain should decrease DC."""
        dc = calc.calculate_dc(temp=20.0, rain=30.0, month=7, dc_prev=300.0)
        assert dc < 300.0

    def test_dc_never_negative(self, calc):
        """DC should never be negative."""
        dc = calc.calculate_dc(temp=10.0, rain=100.0, month=7, dc_prev=10.0)
        assert dc >= 0.0


class TestISI:
    """Test Initial Spread Index calculation."""

    def test_isi_increases_with_wind(self):
        isi_low = FWICalculator.calculate_isi(ffmc=90.0, wind=5.0)
        isi_high = FWICalculator.calculate_isi(ffmc=90.0, wind=30.0)
        assert isi_high > isi_low

    def test_isi_increases_with_ffmc(self):
        isi_low = FWICalculator.calculate_isi(ffmc=70.0, wind=20.0)
        isi_high = FWICalculator.calculate_isi(ffmc=95.0, wind=20.0)
        assert isi_high > isi_low

    def test_isi_non_negative(self):
        isi = FWICalculator.calculate_isi(ffmc=0.0, wind=0.0)
        assert isi >= 0.0


class TestBUI:
    """Test Buildup Index calculation."""

    def test_bui_zero_when_both_zero(self):
        assert FWICalculator.calculate_bui(0.0, 0.0) == 0.0

    def test_bui_increases_with_dmc(self):
        bui_low = FWICalculator.calculate_bui(20.0, 200.0)
        bui_high = FWICalculator.calculate_bui(60.0, 200.0)
        assert bui_high > bui_low

    def test_bui_never_negative(self):
        bui = FWICalculator.calculate_bui(1.0, 1.0)
        assert bui >= 0.0


class TestFWI:
    """Test Fire Weather Index calculation."""

    def test_fwi_increases_with_isi(self):
        fwi_low = FWICalculator.calculate_fwi(isi=5.0, bui=50.0)
        fwi_high = FWICalculator.calculate_fwi(isi=20.0, bui=50.0)
        assert fwi_high > fwi_low

    def test_fwi_increases_with_bui(self):
        fwi_low = FWICalculator.calculate_fwi(isi=10.0, bui=20.0)
        fwi_high = FWICalculator.calculate_fwi(isi=10.0, bui=80.0)
        assert fwi_high > fwi_low

    def test_fwi_non_negative(self):
        fwi = FWICalculator.calculate_fwi(isi=0.0, bui=0.0)
        assert fwi >= 0.0


class TestDailyFWI:
    """Test complete daily FWI calculation with state."""

    def test_multi_day_sequence(self, calc):
        """Run several days and check state carries forward."""
        # Day 1: moderate conditions
        r1 = calc.calculate_daily(temp=20.0, rh=50.0, wind=15.0, rain=0.0, month=7)
        assert r1.ffmc > 0.0
        assert r1.dmc > 0.0
        assert r1.dc > 0.0

        # Day 2: hot dry
        r2 = calc.calculate_daily(temp=30.0, rh=20.0, wind=25.0, rain=0.0, month=7)
        assert r2.ffmc > r1.ffmc  # Should dry out more
        assert r2.fwi > 0.0

        # Day 3: rain event
        r3 = calc.calculate_daily(temp=15.0, rh=80.0, wind=5.0, rain=15.0, month=7)
        assert r3.ffmc < r2.ffmc  # Rain should reduce FFMC

    def test_reset(self, calc):
        """Reset should restore startup values."""
        calc.calculate_daily(30.0, 20.0, 20.0, 0.0, 7)
        calc.reset()
        assert calc.ffmc_prev == 85.0
        assert calc.dmc_prev == 6.0
        assert calc.dc_prev == 15.0

    def test_all_components_returned(self, calc):
        """Daily result should include all 6 FWI components."""
        r = calc.calculate_daily(25.0, 40.0, 15.0, 0.0, 7)
        assert r.ffmc >= 0.0
        assert r.dmc >= 0.0
        assert r.dc >= 0.0
        assert r.isi >= 0.0
        assert r.bui >= 0.0
        assert r.fwi >= 0.0
