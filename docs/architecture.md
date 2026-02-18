# Architecture

## Overview

FireSim V3 simulates wildfire spread using the Canadian FBP System. It is a research/development tool, not a production fire management system.

## Components

```
engine/          Pure Python fire science (zero web deps)
  fbp/           FBP calculator, constants (18 fuel types), crown fire, JIT
  fwi/           FWI calculator (FFMC, DMC, DC, ISI, BUI, FWI)
  spread/        Huygens wavelet simulator, ellipse geometry, slope, perimeter

api/             FastAPI backend
  routers/       HTTP + WebSocket endpoints
  services/      SimulationRunner (background threads)
  schemas/       Pydantic request/response models

frontend/        React + Vite + TypeScript
  components/    MapView, WeatherPanel, FireMetrics, TimeSlider
  hooks/         useSimulation (WebSocket + polling fallback)
  services/      API client
```

## Data flow

1. User clicks map to set ignition point, configures weather and fuel type
2. Frontend POSTs to `/api/v1/simulations` with ignition coords, weather, fuel, duration
3. API creates a `SimulationRunner` in a background thread
4. Engine's `Simulator` yields `SimulationFrame` objects (generator pattern)
5. Each frame is broadcast to connected WebSocket clients as GeoJSON
6. Frontend renders fire perimeters on MapLibre GL map with HFI-based coloring

## Fire spread model

The simulator uses the **Huygens wavelet** method (same as Prometheus):

- The fire front is a vector of `FireVertex` points
- Each vertex is expanded as an ellipse based on FBP head/flank/back ROS
- Ellipse shape comes from the Length-to-Breadth Ratio (LBR), which depends on wind speed
- Slope is applied directionally per vertex using Butler (2007) cap and Anderson (1983) downslope model
- Crown fire initiation follows Van Wagner (1977)

This eliminates grid artifacts that plague cellular automaton approaches.

## Key design decisions

1. **Engine is standalone** - no web framework imports. Can be used independently via `from firesim.spread.simulator import Simulator`
2. **Single source of truth for fuels** - all 18 fuel type parameters in `fbp/constants.py` as frozen dataclasses
3. **Generator-based simulation** - `Simulator.run()` yields frames, allowing streaming without buffering the entire result
4. **WebSocket + polling fallback** - if WebSocket fails, frontend polls GET endpoint every second
5. **MapLibre GL** - open-source map library, no token required for OSM/OpenTopoMap tiles

## What this is NOT

- Not a production fire management tool
- No real-time weather integration (weather is user-specified)
- No fuel raster data (uses uniform fuel type per simulation)
- No WUI analysis, ember transport, or multi-fire interaction
- No authentication or multi-tenancy
