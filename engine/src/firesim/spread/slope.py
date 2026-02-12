"""Directional slope factor for fire spread.

Implements scientifically-validated slope effects:
    - ST-X-3 (1992): SF = exp(3.533 * (slope/100)^1.2) for upslope
    - Butler et al. (2007): Maximum observed effect capped at 2.0x
    - Anderson (1983): Downslope spread reduced by 0.7x

Slope factor varies with the angle between fire spread direction
and terrain aspect (upslope direction).
"""

from __future__ import annotations

import math

try:
    from numba import jit

    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    def jit(*args, **kwargs):  # type: ignore[misc]
        """No-op decorator when Numba is not available."""
        def decorator(func):  # type: ignore[return]
            return func
        return decorator


@jit(nopython=True, cache=True)
def calculate_directional_slope_factor(
    slope_percent: float,
    aspect_degrees: float,
    spread_direction_degrees: float,
) -> float:
    """Calculate slope factor based on spread direction relative to terrain.

    Args:
        slope_percent: Terrain slope (%). E.g., 50 = 50% = 26.6 degrees.
        aspect_degrees: Direction of maximum upslope (0-360, 0=North).
        spread_direction_degrees: Direction fire is spreading (0-360).

    Returns:
        Slope factor multiplier:
            - Up to 2.0 for upslope (Butler 2007 cap)
            - 1.0 for flat or crossslope
            - Down to 0.7 for downslope (Anderson 1983)
    """
    if slope_percent < 1.0:
        return 1.0

    # Angle between spread direction and upslope
    angle_diff = abs(spread_direction_degrees - aspect_degrees)
    if angle_diff > 180.0:
        angle_diff = 360.0 - angle_diff

    cos_angle = math.cos(math.radians(angle_diff))

    # ST-X-3 maximum upslope factor
    sf_max = math.exp(3.533 * (slope_percent / 100.0) ** 1.2)
    sf_max = min(sf_max, 2.0)  # Butler (2007) cap

    if cos_angle > 0:
        # Upslope: proportional to upslope component
        return 1.0 + (sf_max - 1.0) * cos_angle
    else:
        # Downslope: Anderson (1983) reduction
        downslope_factor = 0.7
        return 1.0 + (downslope_factor - 1.0) * abs(cos_angle)


@jit(nopython=True, cache=True)
def calculate_slope_factor(slope_percent: float) -> float:
    """Calculate non-directional slope factor (for simple use cases).

    ST-X-3: SF = exp(3.533 * (slope/100)^1.2), capped at 2.0.

    Args:
        slope_percent: Terrain slope (%)

    Returns:
        Slope factor multiplier (1.0 to 2.0)
    """
    if slope_percent <= 0.0:
        return 1.0
    sf = math.exp(3.533 * (slope_percent / 100.0) ** 1.2)
    return min(sf, 2.0)
