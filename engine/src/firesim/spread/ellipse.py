"""Fire ellipse geometry for Huygens wavelet spread.

Calculates fire ellipse shape parameters from FBP rate of spread
and wind speed. Used by the Huygens spread module to determine
the shape and orientation of fire spread wavelets.

References:
    - Alexander, M.E. (1985). Estimating the length-to-breadth ratio
      of elliptical forest fire patterns.
    - Anderson, K. et al. (2009). Prometheus fire growth model.
"""

from __future__ import annotations

import math


def calculate_length_to_breadth_ratio(wind_speed: float) -> float:
    """Calculate fire ellipse length-to-breadth ratio from wind speed.

    LBR = 1 + 8.729 * (1 - exp(-0.030 * ws))^2.155

    This is the standard LBR equation used in the Canadian FBP System.
    At zero wind, the fire is circular (LBR = 1). As wind increases,
    the fire becomes more elongated.

    Args:
        wind_speed: 10-m open wind speed (km/h)

    Returns:
        Length-to-breadth ratio (>=1.0). Typical range 1.0-8.0.
    """
    if wind_speed <= 0.0:
        return 1.0
    return 1.0 + 8.729 * (1.0 - math.exp(-0.030 * wind_speed)) ** 2.155


def calculate_eccentricity(lbr: float) -> float:
    """Calculate fire ellipse eccentricity from length-to-breadth ratio.

    e = sqrt(1 - 1/LBR^2)

    Args:
        lbr: Length-to-breadth ratio (>=1.0)

    Returns:
        Eccentricity (0.0 to <1.0). 0 = circle, approaching 1 = very elongated.
    """
    if lbr <= 1.0:
        return 0.0
    return math.sqrt(1.0 - 1.0 / (lbr * lbr))


def calculate_back_ros(head_ros: float, lbr: float) -> float:
    """Calculate backing fire rate of spread.

    The backing ROS is the rate of spread at the back of the fire ellipse,
    opposite to the direction of maximum spread.

    back_ros = head_ros / LBR^2

    Args:
        head_ros: Head fire rate of spread (m/min)
        lbr: Length-to-breadth ratio

    Returns:
        Backing ROS (m/min). Always less than head_ros.
    """
    if lbr <= 1.0:
        return head_ros
    return head_ros / (lbr * lbr)


def calculate_flank_ros(head_ros: float, lbr: float) -> float:
    """Calculate flank fire rate of spread.

    The flank ROS is the rate of spread perpendicular to the wind direction.

    flank_ros = head_ros / LBR

    Args:
        head_ros: Head fire rate of spread (m/min)
        lbr: Length-to-breadth ratio

    Returns:
        Flank ROS (m/min)
    """
    if lbr <= 1.0:
        return head_ros
    return head_ros / lbr


def calculate_ellipse_area(head_ros: float, lbr: float, time_hours: float) -> float:
    """Calculate fire ellipse area at a given time.

    The fire is modeled as an ellipse with:
    - semi-major axis a = (head_distance + back_distance) / 2
    - semi-minor axis b = a / LBR

    Area = pi * a * b (converted to hectares)

    Args:
        head_ros: Head fire rate of spread (m/min)
        lbr: Length-to-breadth ratio
        time_hours: Time since ignition (hours)

    Returns:
        Fire area in hectares
    """
    time_min = time_hours * 60.0
    head_dist = head_ros * time_min
    back_dist = calculate_back_ros(head_ros, lbr) * time_min

    # Semi-major and semi-minor axes
    a = (head_dist + back_dist) / 2.0
    b = a / lbr if lbr > 0 else a

    area_m2 = math.pi * a * b
    return area_m2 / 10000.0  # Convert m2 to hectares


def generate_ellipse_points(
    center_lat: float,
    center_lng: float,
    head_ros: float,
    lbr: float,
    wind_direction: float,
    time_hours: float,
    num_points: int = 72,
) -> list[tuple[float, float]]:
    """Generate polygon points for the fire ellipse perimeter.

    Creates an ellipse centered on the ignition point, oriented in the
    wind direction, with semi-axes derived from ROS and LBR.

    Args:
        center_lat: Ignition latitude
        center_lng: Ignition longitude
        head_ros: Head fire ROS (m/min)
        lbr: Length-to-breadth ratio
        wind_direction: Wind direction (degrees, meteorological FROM convention).
            Fire spreads in the opposite direction.
        time_hours: Time since ignition (hours)
        num_points: Number of perimeter vertices

    Returns:
        List of (lat, lng) tuples forming a closed polygon
    """
    time_min = time_hours * 60.0
    head_dist = head_ros * time_min
    back_dist = calculate_back_ros(head_ros, lbr) * time_min

    # Ellipse semi-axes in meters
    semi_major = (head_dist + back_dist) / 2.0
    semi_minor = semi_major / lbr if lbr > 0 else semi_major

    # Offset from center: fire spreads downwind, so the ellipse center
    # is shifted downwind from the ignition point
    offset = (head_dist - back_dist) / 2.0

    # Fire spread direction (opposite of wind FROM direction)
    spread_dir_rad = math.radians((wind_direction + 180.0) % 360.0)

    # Meters to degrees conversion (approximate)
    lat_per_m = 1.0 / 111320.0
    lng_per_m = 1.0 / (111320.0 * math.cos(math.radians(center_lat)))

    # Center offset
    offset_lat = offset * math.cos(spread_dir_rad) * lat_per_m
    offset_lng = offset * math.sin(spread_dir_rad) * lng_per_m
    cx = center_lat + offset_lat
    cy = center_lng + offset_lng

    # Generate ellipse points
    points = []
    for i in range(num_points):
        theta = 2.0 * math.pi * i / num_points

        # Point on unrotated ellipse
        ex = semi_major * math.cos(theta)
        ey = semi_minor * math.sin(theta)

        # Rotate by spread direction
        rx = ex * math.cos(spread_dir_rad) - ey * math.sin(spread_dir_rad)
        ry = ex * math.sin(spread_dir_rad) + ey * math.cos(spread_dir_rad)

        # Convert to lat/lng
        lat = cx + rx * lat_per_m
        lng = cy + ry * lng_per_m
        points.append((lat, lng))

    # Close the polygon
    points.append(points[0])
    return points
