---
title: "Part 4: First Deployment - Fly.io Adventures"
series: "Catwalk Live Development Journey"
part: 4
date: 2025-12-12
updated: 2025-12-27
tags: [deployment, fly.io, docker, postgresql, infrastructure, debugging]
reading_time: "14 min"
commits_covered: "5d1fb9f...f15370c"
---

## The Moment of Truth

December 12, 2025. The application works perfectly on localhost:
- Backend API responding at `localhost:8000`
- Frontend rendering at `localhost:3000`
- PostgreSQL running in Docker
- Analysis works, forms generate, encryption encrypts

It's time to **ship to production**.

How hard could it be?

## Attempt 1: The Naive Dockerfile

AI (Claude Code) generated a Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

I ran `fly deploy`. It built. It deployed. It... crashed immediately.

```
2025-12-12T14:23:01Z [error] ModuleNotFoundError: No module named 'openai'
```

**What happened**: `requirements.txt` was incomplete. The analysis service imported `openai` but it wasn't listed as a dependency.

**The fix**: Add all missing dependencies:

```txt
# requirements.txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg[binary]>=3.1.0  # PostgreSQL driver
cryptography>=41.0.0    # Fernet encryption
pydantic>=2.0.0
pydantic-settings>=2.0.0
openai>=1.0.0           # For Claude API via OpenRouter
httpx>=0.27.0           # HTTP client
email-validator>=2.1.0  # Required by Pydantic EmailStr
```

**Lesson 1**: AI doesn't always track dependencies correctly. Always verify imports match requirements.

## Attempt 2: The Database Connection Failure

With dependencies fixed, the app started. Then:

```
2025-12-12T14:45:12Z [error] sqlalchemy.exc.ArgumentError:
Could not parse SQLAlchemy URL from string 'postgres://...'
```

**Context**: Fly.io PostgreSQL provides URLs like:
```
postgres://user:pass@db-name.internal:5432/dbname?sslmode=disable
```

SQLAlchemy 2.0 with async requires:
```
postgresql+psycopg://user:pass@db-name.internal:5432/dbname
```

**The problem**: Driver mismatch. Fly gives `postgres://`, SQLAlchemy wants `postgresql+psycopg://`.

**AI's first solution**: Use `asyncpg` driver.

```python
# ❌ AI suggested this
DATABASE_URL = "postgresql+asyncpg://..."
```

Deployed. Crashed.

```
2025-12-12T15:10:33Z [error] asyncpg.exceptions.InvalidParameterValue:
sslmode 'disable' is not supported
```

**The real problem**: Fly.io URLs include `?sslmode=disable`. The `asyncpg` driver doesn't support this parameter format.

**The actual solution**: Use `psycopg3` and transform URLs.

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        """
        Convert Fly.io postgres:// URLs to SQLAlchemy format.

        Fly.io: postgres://user:pass@host:5432/db?sslmode=disable
        SQLAlchemy 2.0 async: postgresql+psycopg://user:pass@host:5432/db?sslmode=disable
        """
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v
```

**Why this works**: `psycopg3` supports all PostgreSQL SSL parameters. It's the modern, async-compatible driver.

**Lesson 2**: Infrastructure details matter. AI suggested a driver that doesn't work with Fly.io's conventions.

## Attempt 3: The Shell Script Disaster

The app connected to the database! But database tables didn't exist.

**Solution**: Run Alembic migrations on startup.

AI generated:

```dockerfile
# ❌ AI's approach
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]
```

```bash
#!/bin/bash
# docker-entrypoint.sh
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Deployed. Crashed.

```
2025-12-12T16:05:44Z [error] /bin/sh: ./docker-entrypoint.sh: not found
```

**What happened**: I created the shell script on Windows. Windows uses CRLF (`\r\n`) line endings. Linux expects LF (`\n`). The script was literally unreadable to the Linux container.

**The fix**: Don't use shell scripts in Docker when developing on Windows.

```dockerfile
# ✅ Inline commands instead
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
```

**Even better**: Use Fly.io's `release_command` feature:

```toml
# fly.toml
[deploy]
  release_command = "alembic upgrade head"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1
```

Now migrations run **before** deployment. If migrations fail, deployment aborts. Much safer.

**Lesson 3**: Avoid shell scripts in Docker when cross-platform development is involved. Use native tooling.

## Attempt 4: The Database Cluster Meltdown

The app started successfully! Then, 6 hours later:

```
2025-12-12T22:34:12Z [error] psycopg.OperationalError:
connection to server at "catwalk-db.internal" failed:
no active leader found
```

**What happened**: Fly.io's single-node PostgreSQL clusters can enter a broken state where there's "no active leader." The cluster becomes completely unusable.

**AI's suggestion**: Restart the database.

```bash
fly machines restart <db-machine-id>
```

Didn't work. Still broken.

**The nuclear option** (from Fly.io docs):

```bash
# Destroy the broken cluster
fly apps destroy catwalk-db

# Create a fresh cluster
fly postgres create --name catwalk-db-v2

# Attach to backend
fly postgres attach catwalk-db-v2 --app catwalk-backend
```

**Result**: New database, clean slate, working again.

**Data loss**: Everything. But this was day 2 of development with no real users, so... acceptable.

**Lesson 4**: Fly.io single-node databases are fragile. For production, use multi-node clusters or managed PostgreSQL (e.g., Supabase, Neon).

**Long-term solution**: We documented the recovery procedure in `CLAUDE.md` so future AI sessions (and humans) know what to do:

```markdown
## Fly.io Postgres Cluster Recovery

If you see "no active leader found":

1. Don't try to repair - faster to recreate
2. `fly apps destroy <db-name>` (accepts data loss)
3. `fly postgres create --name <new-db-name>`
4. `fly postgres attach <new-db-name> --app <backend-app>`
5. Run migrations: `fly ssh console` → `alembic upgrade head`
```

## The Successful Deployment

December 12, late evening. After fixing:
- ✅ Missing dependencies
- ✅ Database driver (asyncpg → psycopg3)
- ✅ URL transformation
- ✅ Shell script line endings
- ✅ Database cluster recreation

The deployment succeeded:

```bash
fly status --app catwalk-backend

ID              = catwalk-backend
Status          = running
Hostname        = catwalk-backend.fly.dev
Platform        = machines
Region          = sjc (San Jose)
Machines        = 1 (1 running)

VM Resources:
  CPUs:   1x shared
  Memory: 512 MB
```

**The moment**: `curl https://catwalk-backend.fly.dev/api/health`

```json
{"status": "healthy"}
```

**Pure joy**. The backend was live.

## The Dockerfile (Final Version)

```dockerfile
# Use official Python runtime
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (documentation only, Fly.io uses internal_port from fly.toml)
EXPOSE 8080

# Run uvicorn (migrations handled by release_command)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Key elements**:
- `python:3.12-slim` - Smaller image
- System dependencies in one RUN - fewer layers
- `requirements.txt` copied first - Docker layer caching
- No shell scripts - just `uvicorn`

## The Fly.io Configuration

```toml
# fly.toml
app = "catwalk-backend"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[deploy]
  release_command = "alembic upgrade head"

[env]
  PORT = "8080"
  PUBLIC_URL = "https://catwalk-backend.fly.dev"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

**Configuration decisions**:

- **`auto_stop_machines = "off"`**: Backend stays running 24/7. No cold starts.
- **`min_machines_running = 1`**: Always one instance running.
- **`release_command`**: Migrations before deployment (safer).
- **`force_https`**: All HTTP → HTTPS redirects.
- **512MB RAM**: Plenty for FastAPI + SQLAlchemy.

## Secrets Management

Fly.io secrets are environment variables encrypted at rest:

```bash
# Set secrets (never commit these!)
fly secrets set \
  DATABASE_URL="postgresql+psycopg://..." \
  ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  OPENROUTER_API_KEY="sk-or-..." \
  AUTH_SECRET="$(openssl rand -base64 32)" \
  --app catwalk-backend
```

**Secrets set this way**:
- Encrypted at rest
- Available as environment variables in the app
- Not logged
- Rotatable (set new value, old value overwritten)

**What we learned**: Never log secrets. Never return secrets in API responses. Decrypt only in memory.

## Database Setup

```bash
# Create PostgreSQL cluster
fly postgres create \
  --name catwalk-db \
  --region sjc \
  --vm-size shared-cpu-1x \
  --volume-size 10

# Attach to backend (sets DATABASE_URL automatically)
fly postgres attach catwalk-db --app catwalk-backend
```

**Attachment benefits**:
- `DATABASE_URL` secret automatically set
- Uses Fly.io internal DNS (`.internal`)
- No public internet exposure

**Database specs**:
- PostgreSQL 15
- 10GB volume
- Shared CPU (free tier)
- Single node (fragile, but fine for MVP)

## The Cost Reality

Running on Fly.io:

| Resource | Specs | Monthly Cost |
|----------|-------|--------------|
| Backend VM | 512MB, shared CPU, always-on | ~$1.94 |
| PostgreSQL | 10GB, single-node | $0 (free tier) |
| **Total** | | **~$1.94/month** |

Cheaper than a coffee. **Production infrastructure for $2/month**.

## Monitoring & Debugging

```bash
# Real-time logs
fly logs --app catwalk-backend

# Check app status
fly status --app catwalk-backend

# SSH into container (debugging)
fly ssh console --app catwalk-backend

# Database console
fly postgres connect --app catwalk-db
```

**Log watching became a habit**. Every deploy: `fly logs` in a terminal, watch for errors.

## What Worked vs What Didn't

### AI-Generated Code That Worked ✅
- FastAPI app structure
- Pydantic models
- Database migrations (Alembic)
- Environment variable configuration

### AI-Generated Code That Failed ❌
- Database driver choice (asyncpg)
- Shell script approach (CRLF issues)
- Dependency tracking (missing packages)
- Error handling (too generic)

### Human Intervention Required 🧠
- PostgreSQL driver debugging
- Fly.io-specific configuration
- Database cluster recovery
- Secrets management strategy

**The pattern**: AI handles **known patterns** well. AI fails at **infrastructure quirks** and **platform-specific issues**.

## Up Next

The backend is deployed. The database is running. The health endpoint responds.

But the platform doesn't **do** anything yet. We can analyze repos, but we can't deploy MCP servers.

Time to build the core: **Streamable HTTP and MCP Machines**.

That's Part 5: Implementing Streamable HTTP & MCP Machines.

---

**Key Commits**:
- `5d1fb9f` - Enable backend production deployment to Fly.io
- `f15370c` - Backend: deploy Fly MCP machines + Streamable HTTP bridge

**Related Files**:
- `backend/Dockerfile` - Production container
- `backend/fly.toml` - Fly.io configuration
- `backend/app/core/config.py` - Database URL transformer

**Debugging Resources**:
- `CLAUDE.md` - Deployment pitfalls and solutions
- `context/CURRENT_STATUS.md` - Database recovery procedures

**Next Post**: [Part 5: Implementing Streamable HTTP & MCP Machines](05-streamable-http-mcp-machines.md)
