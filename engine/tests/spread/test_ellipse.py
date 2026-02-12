"""Tests for fire ellipse geometry."""

import math

import pytest

from firesim.spread.ellipse import (
    calculate_back_ros,
    calculate_eccentricity,
    calculate_ellipse_area,
    calculate_flank_ros,
    calculate_length_to_breadth_ratio,
    generate_ellipse_points,
)


class TestLBR:
    """Test length-to-breadth ratio calculation."""

    def test_zero_wind_circular(self):
        """Zero wind should produce circular fire (LBR = 1)."""
        lbr = calculate_length_to_breadth_ratio(0.0)
        assert lbr == 1.0

    def test_increases_with_wind(self):
        """LBR should increase with wind speed."""
        lbr_low = calculate_length_to_breadth_ratio(10.0)
        lbr_high = calculate_length_to_breadth_ratio(40.0)
        assert lbr_high > lbr_low

    def test_moderate_wind_reasonable(self):
        """LBR at 20 km/h should be between 1 and 5."""
        lbr = calculate_length_to_breadth_ratio(20.0)
        assert 1.0 < lbr < 5.0

    def test_always_at_least_one(self):
        """LBR should never be less than 1."""
        lbr = calculate_length_to_breadth_ratio(-5.0)
        assert lbr >= 1.0


class TestEccentricity:
    """Test fire ellipse eccentricity."""

    def test_circle_zero_eccentricity(self):
        """LBR = 1 (circle) should have eccentricity = 0."""
        assert calculate_eccentricity(1.0) == 0.0

    def test_elongated_high_eccentricity(self):
        """High LBR should have high eccentricity approaching 1."""
        e = calculate_eccentricity(5.0)
        assert 0.9 < e < 1.0

    def test_moderate_eccentricity(self):
        """Moderate LBR should have moderate eccentricity."""
        e = calculate_eccentricity(2.0)
        assert 0.5 < e < 0.95


class TestBackingAndFlankROS:
    """Test backing and flank fire rates of spread."""

    def test_back_ros_less_than_head(self):
        """Backing ROS should be less than head ROS when LBR > 1."""
        back = calculate_back_ros(10.0, 2.0)
        assert back < 10.0

    def test_back_ros_equals_head_no_wind(self):
        """With no wind (LBR=1), backing = head."""
        back = calculate_back_ros(10.0, 1.0)
        assert back == 10.0

    def test_flank_ros_between_head_and_back(self):
        """Flank ROS should be between head and back."""
        head = 10.0
        lbr = 3.0
        back = calculate_back_ros(head, lbr)
        flank = calculate_flank_ros(head, lbr)
        assert back < flank < head


class TestEllipseArea:
    """Test fire ellipse area calculation."""

    def test_area_increases_with_time(self):
        """Area should increase over time."""
        a1 = calculate_ellipse_area(head_ros=5.0, lbr=2.0, time_hours=1.0)
        a2 = calculate_ellipse_area(head_ros=5.0, lbr=2.0, time_hours=2.0)
        assert a2 > a1

    def test_area_increases_with_ros(self):
        """Higher ROS should produce larger area."""
        a_slow = calculate_ellipse_area(head_ros=2.0, lbr=2.0, time_hours=1.0)
        a_fast = calculate_ellipse_area(head_ros=10.0, lbr=2.0, time_hours=1.0)
        assert a_fast > a_slow

    def test_area_positive(self):
        """Area should be positive for any valid inputs."""
        area = calculate_ellipse_area(head_ros=5.0, lbr=2.0, time_hours=1.0)
        assert area > 0.0

    def test_circular_fire_area(self):
        """LBR=1 should produce a circular area: pi * r^2."""
        ros = 5.0  # m/min
        hours = 1.0
        dist = ros * hours * 60  # 300m radius
        expected_ha = math.pi * dist**2 / 10000.0
        actual_ha = calculate_ellipse_area(ros, 1.0, hours)
        assert abs(actual_ha - expected_ha) / expected_ha < 0.01


class TestGenerateEllipsePoints:
    """Test ellipse polygon generation."""

    def test_produces_closed_polygon(self):
        """Generated polygon should be closed (first == last point)."""
        pts = generate_ellipse_points(53.5, -113.5, 5.0, 2.0, 225.0, 1.0)
        assert pts[0] == pts[-1]

    def test_correct_number_of_points(self):
        """Should produce num_points + 1 (closed polygon)."""
        pts = generate_ellipse_points(53.5, -113.5, 5.0, 2.0, 225.0, 1.0, num_points=36)
        assert len(pts) == 37

    def test_points_near_ignition(self):
        """All points should be within reasonable distance of ignition."""
        lat, lng = 53.5, -113.5
        pts = generate_ellipse_points(lat, lng, 5.0, 2.0, 225.0, 1.0)
        for plat, plng in pts:
            assert abs(plat - lat) < 0.1  # Within ~11 km
            assert abs(plng - lng) < 0.2
