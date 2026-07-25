# Relay Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests
COPY pyproject.toml requirements.txt README.md ./
COPY relay/ ./relay/

# Install Relay and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Expose FastAPI server port
EXPOSE 8000

# Default command: run FastAPI backend server
CMD ["python3", "-m", "uvicorn", "relay.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
