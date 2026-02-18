# Deployment

## Development (recommended)

Start the API and frontend separately for hot-reload:

```bash
# Terminal 1: API backend
PYTHONPATH=engine/src:api/src uvicorn firesim_api.main:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. The Vite dev server proxies `/api` requests to the backend.

## Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3000 (nginx serving Vite build)
- API: http://localhost:8000

The nginx config handles SPA routing and proxies API/WebSocket requests.

## Environment variables

### Frontend (.env.local)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_MAPBOX_TOKEN` | (empty) | Mapbox access token for satellite basemap. Leave empty for free OSM tiles. |
| `VITE_API_URL` | (empty) | API base URL. Empty uses Vite proxy (dev) or relative paths (prod). |

### API

| Variable | Default | Description |
|----------|---------|-------------|
| No environment variables required | | Engine runs with built-in fuel parameters |

## Requirements

### API

- Python 3.10+
- Dependencies: fastapi, uvicorn, pydantic, numpy, numba

```bash
pip install -e engine/
pip install -e api/
# Or use PYTHONPATH:
PYTHONPATH=engine/src:api/src uvicorn firesim_api.main:app
```

### Frontend

- Node.js 18+
- npm

```bash
cd frontend
npm install
npm run dev      # Development
npm run build    # Production build
```

## Production build

```bash
# Build frontend
cd frontend && npm run build
# Output: frontend/dist/

# Serve with any static file server, proxy /api to the Python backend
```

## Testing

```bash
# All tests
make test

# Engine only (294 tests)
cd engine && python -m pytest tests/ -v

# API only (6 tests)
PYTHONPATH=engine/src:api/src python -m pytest api/tests/ -v

# Frontend type check
cd frontend && npx tsc --noEmit
```
