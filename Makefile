.PHONY: dev test lint build clean install

install:
	cd engine && pip install -e ".[dev]"
	cd api && pip install -e ".[dev]"

test:
	cd engine && python -m pytest tests/ -v --tb=short
	cd api && python -m pytest tests/ -v --tb=short

test-engine:
	cd engine && python -m pytest tests/ -v --tb=short

test-api:
	cd api && python -m pytest tests/ -v --tb=short

test-cov:
	cd engine && python -m pytest tests/ -v --cov=src/firesim --cov-report=term-missing
	cd api && python -m pytest tests/ -v --cov=src/firesim_api --cov-report=term-missing

lint:
	cd engine && ruff check src/ tests/
	cd api && ruff check src/ tests/

typecheck:
	cd engine && mypy src/firesim/
	cd api && mypy src/firesim_api/

format:
	cd engine && ruff format src/ tests/
	cd api && ruff format src/ tests/

dev:
	cd api && uvicorn firesim_api.main:app --reload --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
