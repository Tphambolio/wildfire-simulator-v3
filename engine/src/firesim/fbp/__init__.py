"""Canadian Fire Behavior Prediction (FBP) System."""

from firesim.fbp.calculator import calculate_fbp
from firesim.fbp.constants import FuelType, FUEL_TYPES

__all__ = ["calculate_fbp", "FuelType", "FUEL_TYPES"]
