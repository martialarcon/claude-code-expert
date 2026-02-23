# AI Architect v2 - Dockerfile
# Target: Jetson Orin Nano (ARM64)

FROM python:3.11-slim-bookworm

# Labels
LABEL maintainer="AI Architect"
LABEL description="Automated technical intelligence system for Claude Code ecosystem"
LABEL architecture="ARM64"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
# Using the official installation method
RUN curl -fsSL https://claude.ai/install.sh | sh || \
    echo "Claude CLI installation note: May need manual install on ARM64"

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/snapshots /app/data/transcripts /app/data/packages \
    /app/data/chromadb \
    /app/output/daily /app/output/weekly /app/output/monthly \
    /app/output/topics /app/output/competitive

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default command - keep container running for exec commands
# Actual processing is triggered by cron scripts via docker compose exec
ENTRYPOINT ["sleep"]
CMD ["infinity"]
