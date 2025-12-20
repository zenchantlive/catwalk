FROM python:3.12-slim

WORKDIR /app

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

# Run the API server. Database migrations run via Fly.io `release_command`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
