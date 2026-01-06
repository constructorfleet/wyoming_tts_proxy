# Use a multi-stage build to keep the final image small
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Final stage
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY wyoming_tts_proxy /app/wyoming_tts_proxy

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV METRICS_PORT=8000

# Default ports for Wyoming
EXPOSE 10201
# Default port for Metrics/Health
EXPOSE 8000

# Health check using the metrics port
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${METRICS_PORT}/health || exit 1

# Run the application
ENTRYPOINT ["python", "-m", "wyoming_tts_proxy"]
