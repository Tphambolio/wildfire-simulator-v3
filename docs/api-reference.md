# API Reference

Base URL: `http://localhost:8000`

## Endpoints

### POST /api/v1/simulations

Start a new fire spread simulation.

**Request body:**

```json
{
  "ignition_lat": 51.0,
  "ignition_lng": -114.0,
  "weather": {
    "wind_speed": 20.0,
    "wind_direction": 270.0,
    "temperature": 25.0,
    "relative_humidity": 30.0,
    "precipitation_24h": 0.0
  },
  "fwi_overrides": {
    "ffmc": 90.0,
    "dmc": 45.0,
    "dc": 300.0
  },
  "duration_hours": 4.0,
  "snapshot_interval_minutes": 30.0,
  "fuel_type": "C2"
}
```

- `fwi_overrides` is optional. If omitted, FWI components are computed from weather.
- `fuel_type` must be one of the 18 FBP fuel type codes (C1-C7, D1-D2, M1-M4, O1a, O1b, S1-S3).

**Response (201):**

```json
{
  "simulation_id": "abc123",
  "status": "running",
  "config": { ... },
  "frames": [],
  "error": null
}
```

### GET /api/v1/simulations/{id}

Get simulation status and results.

**Response (200):**

```json
{
  "simulation_id": "abc123",
  "status": "completed",
  "config": { ... },
  "frames": [
    {
      "time_hours": 0.5,
      "perimeter": [[51.001, -114.001], [51.001, -113.999], ...],
      "area_ha": 2.29,
      "head_ros_m_min": 7.82,
      "max_hfi_kw_m": 2298.6,
      "fire_type": "passive_crown",
      "flame_length_m": 2.73,
      "fuel_breakdown": {"C2": 1.0}
    }
  ],
  "error": null
}
```

Status values: `running`, `completed`, `failed`

### WebSocket /api/v1/simulations/ws/{id}

Stream simulation frames in real-time.

**Events received:**

```json
{"type": "simulation.frame", "frame": { ... }}
{"type": "simulation.completed"}
{"type": "simulation.error", "error": "message"}
```

### GET /api/v1/health

Health check endpoint.

**Response (200):**

```json
{
  "status": "healthy",
  "version": "3.0.0",
  "uptime_seconds": 123.4,
  "engine": "firesim"
}
```

## Perimeter format

Perimeters are arrays of `[latitude, longitude]` pairs forming a closed polygon. The first and last points are the same.

## Error responses

```json
{
  "detail": "Error description"
}
```

Common status codes:
- 404: Simulation not found
- 422: Validation error (invalid fuel type, missing fields)
- 500: Internal simulation error
