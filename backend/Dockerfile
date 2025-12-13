FROM python:3.12-slim

WORKDIR /app

# Install Node.js 20 (needed for local dev mode subprocess spawning)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy and install dependencies
COPY requirements.txt pyproject.toml ./
RUN uv pip install --system -r requirements.txt

# Copy Alembic configuration and migrations
COPY alembic.ini ./
COPY alembic ./alembic

# Copy application code
COPY app ./app

EXPOSE 8080

# Run migrations and start server directly (no shell script needed)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
