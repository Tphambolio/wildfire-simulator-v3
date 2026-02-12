.PHONY: dev dev-api dev-frontend test lint build clean install

install:
	cd engine && pip install -e ".[dev]"
	cd api && pip install -e ".[dev]"
	cd frontend && npm install

test:
	PYTHONPATH=engine/src:api/src python -m pytest engine/tests/ api/tests/ -v --tb=short

test-engine:
	python -m pytest engine/tests/ -v --tb=short

test-api:
	PYTHONPATH=engine/src:api/src python -m pytest api/tests/ -v --tb=short

test-cov:
	python -m pytest engine/tests/ -v --cov=engine/src/firesim --cov-report=term-missing

lint:
	cd frontend && npx tsc --noEmit

dev: dev-api dev-frontend

dev-api:
	PYTHONPATH=engine/src:api/src uvicorn firesim_api.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist
