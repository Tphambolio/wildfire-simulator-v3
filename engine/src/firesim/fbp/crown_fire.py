"""Crown fire initiation and behavior modeling.

Implements Van Wagner (1977, 1993) crown fire models for determining
when surface fires transition to crown fires and the resulting behavior.

References:
    Van Wagner, C.E. (1977). Conditions for the start and spread of crown fire.
    Canadian Journal of Forest Research, 7(1), 23-34.
"""

from __future__ import annotations

from firesim.fbp.constants import FuelTypeSpec
from firesim.types import FireType


def calculate_critical_surface_intensity(cbh: float, fmc: float = 100.0) -> float:
    """Calculate critical surface fire intensity for crown fire initiation.

    Van Wagner (1977): I_0 = (0.010 * CBH * (460 + 25.9 * FMC))^1.5

    Args:
        cbh: Crown base height (m)
        fmc: Foliar moisture content (%)

    Returns:
        Critical surface intensity (kW/m). Returns 0 if CBH is 0 (no canopy).
    """
    if cbh <= 0.0:
        return 0.0
    return (0.010 * cbh * (460.0 + 25.9 * fmc)) ** 1.5


def calculate_crown_fraction_burned(sfi: float, csi: float) -> float:
    """Calculate crown fraction burned (CFB).

    Args:
        sfi: Surface fire intensity (kW/m)
        csi: Critical surface intensity for crown fire initiation (kW/m)

    Returns:
        Crown fraction burned (0.0 to 1.0)
    """
    if csi <= 0.0 or sfi < csi:
        return 0.0
    cfb = 1.0 - (csi / sfi) ** 0.5
    return max(0.0, min(1.0, cfb))


def classify_fire_type(cfb: float) -> FireType:
    """Classify fire type based on crown fraction burned.

    Args:
        cfb: Crown fraction burned (0-1)

    Returns:
        FireType classification
    """
    if cfb >= 0.9:
        return FireType.ACTIVE_CROWN
    elif cfb > 0.1:
        return FireType.PASSIVE_CROWN
    elif cfb > 0.0:
        return FireType.SURFACE_WITH_TORCHING
    else:
        return FireType.SURFACE


def calculate_crown_ros(surface_ros: float, spec: FuelTypeSpec) -> float:
    """Calculate crown fire rate of spread.

    Active crown fires spread faster than surface fires. The increase
    is based on crown bulk density (CBD).

    Args:
        surface_ros: Surface rate of spread (m/min)
        spec: Fuel type specification

    Returns:
        Crown fire ROS (m/min)
    """
    if spec.cbd <= 0.0:
        return surface_ros

    cbd_critical = 0.05  # kg/m3 threshold for active crown fire
    if spec.cbd < cbd_critical:
        return surface_ros

    crown_factor = 1.0 + (spec.cbd - cbd_critical) / 0.1
    crown_factor = min(crown_factor, 3.0)
    return surface_ros * crown_factor


def calculate_crown_fire(
    spec: FuelTypeSpec,
    surface_intensity: float,
    fmc: float = 100.0,
) -> dict:
    """Calculate complete crown fire behavior for a fuel type.

    Args:
        spec: Fuel type specification
        surface_intensity: Surface fire intensity (kW/m)
        fmc: Foliar moisture content (%)

    Returns:
        Dictionary with crown fire results:
            - cfb: Crown fraction burned (0-1)
            - fire_type: FireType classification
            - crown_ros_factor: Multiplier for surface ROS
            - csi: Critical surface intensity (kW/m)
            - crown_ros: Crown rate of spread (m/min) — placeholder, needs surface_ros
    """
    csi = calculate_critical_surface_intensity(spec.cbh, fmc)

    # Non-canopy fuel types never crown
    if csi <= 0.0:
        return {
            "cfb": 0.0,
            "fire_type": FireType.SURFACE,
            "csi": 0.0,
            "crown_ros": 0.0,
        }

    cfb = calculate_crown_fraction_burned(surface_intensity, csi)
    fire_type = classify_fire_type(cfb)

    # Crown ROS is computed as a factor of surface ROS.
    # We return 0 here; the caller (calculate_fbp) applies this via surface_ros * factor.
    # This is a simplification — the actual crown_ros is calculated in calculate_fbp.
    return {
        "cfb": cfb,
        "fire_type": fire_type,
        "csi": csi,
        "crown_ros": 0.0,  # Populated by caller
    }
