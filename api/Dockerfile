FROM python:3.12-slim

WORKDIR /app

# Install engine
COPY engine/pyproject.toml engine/pyproject.toml
COPY engine/src engine/src
RUN pip install --no-cache-dir engine/

# Install API
COPY api/pyproject.toml api/pyproject.toml
COPY api/src api/src
RUN pip install --no-cache-dir api/

EXPOSE 8000

CMD ["uvicorn", "firesim_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
