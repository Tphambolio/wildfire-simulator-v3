# Wildfire Simulator V3

Research and development tool for Canadian FBP fire spread simulation.

## What this does

Simulates wildfire spread using the Canadian Forest Fire Behavior Prediction (FBP) System:
- All 18 FBP fuel types (ST-X-3 validated)
- Huygens wavelet fire spread (open wildland) and cellular automaton (urban/WUI)
- FWI System (FFMC, DMC, DC, ISI, BUI, FWI)
- Crown fire initiation (Van Wagner 1977)
- Ember spotting (Albini 1979) with multi-front ignition
- Directional slope effects (Butler 2007 cap, Anderson 1983 downslope)
- Spatial fuel/water/buildings/WUI-zone grids
- Interactive map with click-to-ignite, real-time streaming, pause/resume/cancel

## Stack

| Layer | Technology |
|-------|-----------|
| Fire engine | Python 3.10+ with Numba JIT |
| API | FastAPI + WebSocket |
| Frontend | React + Vite + TypeScript + MapLibre GL |
| Deploy | Docker Compose |

## Quick start

```bash
# Start the API backend
PYTHONPATH=engine/src:api/src uvicorn firesim_api.main:app --port 8000

# In a second terminal, start the frontend
cd frontend && npm install && npm run dev
```

Then open http://localhost:3000, click the map to set an ignition point, adjust weather, and run a simulation.

## Docker

```bash
docker compose up --build
# Frontend: http://localhost:3000
# API: http://localhost:8000/api/v1/health
```

## Testing

```bash
make test           # All 386 tests
make test-engine    # 369 engine tests
make test-api       # 17 API integration tests
```

## Project structure

```
engine/     Pure Python fire science (zero web deps, 369 tests)
api/        FastAPI backend with WebSocket streaming (17 tests)
frontend/   React + Vite + TypeScript + MapLibre GL
```

## API

```
POST /api/v1/simulations          Start a simulation
GET  /api/v1/simulations/{id}     Get status and results
WS   /api/v1/simulations/ws/{id}  Stream frames in real-time
GET  /api/v1/health               Health check
```

## References

- Forestry Canada Fire Danger Group (1992). ST-X-3.
- Tymstra, C. et al. (2010). Prometheus: Canadian Wildland Fire Growth Simulation Model.
- Van Wagner, C.E. (1977). Crown fire initiation.
- Albini, F.A. (1979). Spot fire distance from burning trees.
- Butler et al. (2007). Slope effect observations.
- Anderson (1983). Downslope fire spread.
