# Wildfire Simulator V3

Research and development tool for Canadian FBP fire spread simulation.

## Status

**Phase 1: Fire Science Foundation** — Core FBP and FWI calculators implemented and tested.

## What this does

Simulates wildfire spread using the Canadian Forest Fire Behavior Prediction (FBP) System:
- All 18 FBP fuel types (ST-X-3 validated)
- Elliptical fire spread geometry (Huygens wavelet)
- FWI System (FFMC, DMC, DC, ISI, BUI, FWI)
- Crown fire initiation (Van Wagner 1977)
- Directional slope effects (Butler 2007 cap, Anderson 1983 downslope)

## Stack

- **Engine:** Python 3.11+ with Numba JIT
- **API:** FastAPI (coming Phase 4)
- **Frontend:** React + Mapbox GL (coming Phase 5)

## Quick start

```bash
cd engine && pip install -e ".[dev]"
make test-engine
```

## Project structure

```
engine/     Pure Python fire science (zero web deps)
api/        FastAPI backend (Phase 4)
frontend/   React + Vite + TypeScript (Phase 5)
docs/       Architecture and reference docs
```

## References

- Forestry Canada Fire Danger Group (1992). ST-X-3.
- Van Wagner, C.E. (1977). Crown fire initiation.
- Butler et al. (2007). Slope effect observations.
- Anderson (1983). Downslope fire spread.
