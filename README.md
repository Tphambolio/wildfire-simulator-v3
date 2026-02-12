# Wildfire Simulator V3

Research and development tool for Canadian FBP fire spread simulation.

## What this does

Simulates wildfire spread using the Canadian Forest Fire Behavior Prediction (FBP) System:
- All 18 FBP fuel types (ST-X-3 validated)
- Huygens wavelet fire spread (same method as Prometheus)
- FWI System (FFMC, DMC, DC, ISI, BUI, FWI)
- Crown fire initiation (Van Wagner 1977)
- Directional slope effects (Butler 2007 cap, Anderson 1983 downslope)
- Interactive map with click-to-ignite and real-time perimeter streaming

## Stack

| Layer | Technology |
|-------|-----------|
| Fire engine | Python 3.10+ with Numba JIT |
| API | FastAPI + WebSocket |
| Frontend | React + Vite + TypeScript + Mapbox GL JS |
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
# Engine tests (294 tests)
python -m pytest engine/tests/ -v

# API tests (6 tests)
PYTHONPATH=engine/src:api/src python -m pytest api/tests/ -v

# All tests
make test
```

## Project structure

```
engine/     Pure Python fire science (zero web deps, 294 tests)
api/        FastAPI backend with WebSocket streaming (6 tests)
frontend/   React + Vite + TypeScript + Mapbox GL
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
- Butler et al. (2007). Slope effect observations.
- Anderson (1983). Downslope fire spread.
