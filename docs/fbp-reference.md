# FBP System Reference

## Source

All equations are from: Forestry Canada Fire Danger Group (1992). "Development and Structure of the Canadian Forest Fire Behavior Prediction System." Information Report ST-X-3.

## Fuel types

The 18 Canadian FBP fuel types implemented in `engine/src/firesim/fbp/constants.py`:

| Code | Name | Group |
|------|------|-------|
| C1 | Spruce-Lichen Woodland | Conifer |
| C2 | Boreal Spruce | Conifer |
| C3 | Mature Jack/Lodgepole Pine | Conifer |
| C4 | Immature Jack/Lodgepole Pine | Conifer |
| C5 | Red/White Pine | Conifer |
| C6 | Conifer Plantation | Conifer |
| C7 | Ponderosa Pine/Douglas-Fir | Conifer |
| D1 | Leafless Aspen | Deciduous |
| D2 | Green Aspen (with BUI effect) | Deciduous |
| M1 | Boreal Mixedwood (leafless) | Mixedwood |
| M2 | Boreal Mixedwood (green) | Mixedwood |
| M3 | Dead Balsam Fir Mixedwood (leafless) | Mixedwood |
| M4 | Dead Balsam Fir Mixedwood (green) | Mixedwood |
| O1a | Matted Grass | Open |
| O1b | Standing Grass | Open |
| S1 | Jack/Lodgepole Pine Slash | Slash |
| S2 | White Spruce/Balsam Slash | Slash |
| S3 | Coastal Cedar/Hemlock/Douglas-Fir Slash | Slash |

## Key equations

### Rate of spread (ROS)

For most fuel types: `ROS = a * (1 - e^(-b * ISI))^c`

Where a, b, c are fuel-type-specific constants from ST-X-3 Table 6.

### Length-to-Breadth Ratio (LBR)

`LBR = 1.0 + 8.729 * (1 - e^(-0.030 * ws))^2.155`

Where ws is wind speed in km/h (ST-X-3 Eq. 80).

### Head Fire Intensity (HFI)

`HFI = 300 * TFC * ROS` (Byram 1959)

Where TFC is total fuel consumption in kg/m^2.

### Crown fire initiation

Uses Van Wagner (1977) critical surface intensity:
`CSI = 0.001 * (CBH)^1.5 * (460 + 25.9 * FMC)^1.5`

Fire type classification: Surface → Intermittent Crown → Active Crown

## FWI System

The Fire Weather Index System provides ISI (Initial Spread Index) and BUI (Buildup Index) inputs to FBP:

| Component | Depends on | Updates |
|-----------|-----------|---------|
| FFMC | Temperature, RH, Wind, Rain | Daily (noon) |
| DMC | Temperature, RH, Rain | Daily |
| DC | Temperature, Rain | Daily |
| ISI | FFMC, Wind Speed | Derived |
| BUI | DMC, DC | Derived |
| FWI | ISI, BUI | Derived |

## Validation

Engine tests are parametrized across all 18 fuel types and validated against published ST-X-3 tables. See `engine/tests/` for the full test suite.
