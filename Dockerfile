# Multi-stage Dockerfile for Metrics Collector
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 metrics && \
    useradd --uid 1000 --gid metrics --shell /bin/bash --create-home metrics

# Set working directory
WORKDIR /app

# Copy requirements files
COPY metric_collector/requirements.txt ./metric_collector/
COPY cloud_ingestion/requirements.txt ./cloud_ingestion/
COPY dashboard/requirements.txt ./dashboard/
COPY alerts/requirements.txt ./alerts/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r metric_collector/requirements.txt && \
    pip install -r cloud_ingestion/requirements.txt && \
    pip install -r dashboard/requirements.txt && \
    pip install -r alerts/requirements.txt

# Copy application code
COPY --chown=metrics:metrics . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R metrics:metrics /app

# Switch to non-root user
USER metrics

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "cloud_ingestion/server.py"]

# Collector stage
FROM base as collector
CMD ["python", "metric_collector/collector.py"]

# Ingestion stage  
FROM base as ingestion
EXPOSE 8000
CMD ["python", "cloud_ingestion/server.py", "--host", "0.0.0.0", "--port", "8000"]

# Dashboard stage
FROM base as dashboard
EXPOSE 8080
CMD ["python", "dashboard/app.py", "--host", "0.0.0.0", "--port", "8080"]
