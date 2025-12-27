---
title: "Part 3: Production Baptism - Fly.io Reality Check"
series: "Building Catwalk Live with AI Orchestration"
part: 3
date: 2025-12-12
updated: 2025-12-27
tags: [Fly.io, PostgreSQL, Docker, Infrastructure, Debugging, Production Deployment]
reading_time: "12 min"
status: published
---

# Part 3: Production Baptism - Fly.io Reality Check

**The Story So Far:** Day 2 ended with a working local system. GitHub analysis generated dynamic forms. Credentials encrypted properly. Frontend looked slick. Everything worked... on `localhost`.

Time to deploy to production.

**Narrator voice**: *They were not ready for production.*

## The First Deploy: Pure Optimism

December 12, 2025. I tasked Claude Code with a seemingly simple request:

```
Deploy the FastAPI backend to Fly.io:
- Create Dockerfile
- Set up fly.toml configuration
- Deploy PostgreSQL database
- Run Alembic migrations
- Expose backend API at https://<app-name>.fly.dev
```

Claude Code, ever confident, generated:

```bash
commit 5d1fb9f
Date: 2025-12-12

feat: Enable backend production deployment to Fly.io with
Dockerization and essential configurations.
```

**Files created:**
- `backend/Dockerfile` - Python 3.12 container setup
- `backend/fly.toml` - Fly.io configuration
- `backend/requirements.txt` - Updated dependencies
- Deployment scripts

I ran:
```bash
cd backend
fly launch
```

Fly.io created the app. I set secrets:
```bash
fly secrets set OPENROUTER_API_KEY="sk-..."
fly secrets set ENCRYPTION_KEY="..."
```

Then deployed:
```bash
fly deploy
```

Build succeeded ✅
Deploy initiated ✅
Health checks... ❌ **FAILED**

## The PostgreSQL Driver Nightmare

Logs showed:
```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres
```

Wait, what? The database URL was correct. PostgreSQL was running. What's wrong?

**The problem**: SQLAlchemy 2.0+ requires **explicit async drivers** for PostgreSQL. The connection URL format matters:

```python
# ❌ What Fly.io gives you
DATABASE_URL = "postgres://user:pass@hostname:5432/dbname?sslmode=disable"

# ❌ What SQLAlchemy tries to use
# Tries to import 'postgres' driver → doesn't exist

# ✅ What you actually need
DATABASE_URL = "postgresql+asyncpg://user:pass@hostname:5432/dbname?sslmode=disable"
# OR
DATABASE_URL = "postgresql+psycopg://user:pass@hostname:5432/dbname?sslmode=disable"
```

I asked Claude Code: *"Fix the PostgreSQL connection error"*

It suggested adding `asyncpg`:
```bash
pip install asyncpg
```

Updated requirements, redeployed.

New error:
```
asyncpg.exceptions.InvalidParameterValueError:
SSL parameter 'sslmode' is not supported
```

**The twist**: `asyncpg` doesn't support the `sslmode` parameter that Fly.io includes in database URLs.

I remembered the multi-AI planning session from Day 2. Gemini had suggested **psycopg3**, not asyncpg.

**GPT-4 was wrong. Gemini was right.**

I switched to `psycopg[binary]>=3.1.0` and updated the connection URL:

```python
# backend/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        """Convert Fly.io's postgres:// URL to postgresql+psycopg://"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v
```

**This validator became critical infrastructure.** Fly.io always returns `postgres://` URLs, but SQLAlchemy async needs `postgresql+psycopg://`.

Redeployed. Health checks... ✅ **PASSED**

**Time spent debugging this**: 2 hours
**AI contribution**: Suggested wrong driver first, corrected after I fed it the error
**Human intervention required**: Yes - I had to research SQLAlchemy async drivers and Fly.io's SSL quirks

### Lesson: AI Excels at Known Patterns, Struggles with Infrastructure Quirks

AI knows general PostgreSQL + SQLAlchemy patterns. But **Fly.io-specific** SSL parameters? Not in the training data enough to get it right first try.

**Your role as orchestrator**: Catch these edge cases, research solutions, feed corrections back to AI.

## The Docker CRLF Disaster

Next deployment attempt:

```bash
fly deploy
```

Build succeeded ✅
Container started ✅
Migrations... ❌ **FAILED**

```
/bin/sh: ./docker-entrypoint.sh: No such file or directory
```

But the file exists! I checked the Dockerfile:

```dockerfile
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]
```

**The problem**: I was developing on **Windows**. Git for Windows, by default, converts line endings:

- **CRLF** (`\r\n`) on Windows
- **LF** (`\n`) on Linux

Shell scripts created on Windows have CRLF, which Linux interprets as:
```bash
#!/bin/bash\r
```

Linux looks for an interpreter at `/bin/bash\r` (with the literal `\r` character). Can't find it. Error.

**Solution 1**: Configure Git to preserve line endings
```bash
git config core.autocrlf false
```

**Solution 2** (better): **Avoid shell scripts in Docker entirely**

I updated the Dockerfile:

```dockerfile
# ❌ BEFORE (shell script approach)
COPY docker-entrypoint.sh ./
CMD ["./docker-entrypoint.sh"]

# ✅ AFTER (inline commands)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
```

No shell script file. No CRLF issues. Cleaner Dockerfile.

**AI didn't catch this.** Claude Code generated the shell script approach because it's "cleaner" in traditional Linux workflows. But it didn't account for cross-platform development.

**Lesson**: AI assumes a Unix development environment. Windows developers need to override patterns.

## The Missing Dependencies Cascade

Third deployment:

```bash
fly deploy
```

Build succeeded ✅
Container started ✅
Migrations passed ✅
Backend running... ❌ **CRASH**

```
ModuleNotFoundError: No module named 'openai'
```

But `openai` was in `requirements.txt`! Or... was it?

I checked:
```txt
# requirements.txt (generated by AI)
fastapi==0.115.0
sqlalchemy==2.0.23
psycopg[binary]==3.1.8
cryptography==41.0.7
pydantic==2.5.0
alembic==1.13.0
```

**No `openai` package.** The analysis service imported it:

```python
# backend/app/services/analysis.py
from openai import AsyncOpenAI  # ← This import
```

But Claude Code never added it to requirements.

**Why?** Because I had installed `openai` locally during testing:
```bash
pip install openai
```

It worked in my local environment, so AI never noticed the dependency was missing from `requirements.txt`.

**The fix**:
```bash
# Regenerate requirements from current environment
pip freeze > requirements.txt
```

But this created a mess: 47 packages, many unnecessary (pip dependencies of dependencies).

I manually cleaned it:
```txt
# requirements.txt (curated)
fastapi==0.115.0
sqlalchemy==2.0.23
psycopg[binary]==3.1.8
cryptography==41.0.7
pydantic==2.5.0
pydantic-settings==2.1.0
alembic==1.13.0
openai>=1.0.0                    # ← Added
sse-starlette>=2.0.0             # ← Added (for SSE transport)
httpx>=0.25.0                    # ← Added (for Fly API calls)
```

**Lesson**: AI can't detect missing dependencies if your local environment already has them installed. **Validation in a clean environment is critical.**

I should've used:
```bash
# Test in clean container
docker build -t test-backend .
docker run test-backend
```

This would've caught the missing dependencies before deployment.

## The Fly.io Postgres Cluster Breakdown

Fourth deployment:

Everything worked! Backend running, database connected, health checks passing.

I tested the analysis endpoint:
```bash
curl https://catwalk-backend.fly.dev/api/analyze \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/alexarevalo9/ticktick-mcp-server"}'
```

Response: `{"status": "healthy"}` ✅

Perfect! I went to bed.

Next morning:

```bash
curl https://catwalk-backend.fly.dev/api/health
```

```
Error: no active leader found
```

**The database was dead.**

Not "unreachable." Not "connection timeout." **Dead.** The Postgres cluster had entered an unrecoverable state.

I tried:
```bash
fly postgres restart --app catwalk-db
```

No effect. Still dead.

```bash
fly status --app catwalk-db
```

```
Instances
  ID        STATE   HEALTH  REGION
  abc123    dead    -       sjc
```

I spent an hour researching Fly.io Postgres recovery. The docs said:

> **Single-node clusters** can enter "no active leader found" state if they crash during a transaction. Recovery requires destroying and recreating the cluster.

**The solution**: Nuclear option.

```bash
# Destroy broken database
fly apps destroy catwalk-db

# Create fresh database
fly postgres create --name catwalk-db-v2 --region sjc

# Attach to backend
fly postgres attach catwalk-db-v2 --app catwalk-backend
```

This automatically set `DATABASE_URL` secret on the backend app.

Redeployed backend. Migrations ran. Database healthy.

**Lesson learned**: Single-node Postgres clusters are **fragile**. For production, use multi-node with replication. But for MVP? Accept the risk and know how to recover quickly.

**AI contribution here**: Zero. Infrastructure outages require manual debugging and recovery.

## MCP Streamable HTTP Implementation

With backend stable, I moved to the core feature: **MCP Streamable HTTP transport**.

The challenge: Transform stdio-based MCP servers into HTTP endpoints.

**The old MCP spec (deprecated 2024-11-05)**:
- Separate `/sse` (GET) for Server-Sent Events
- Separate `/messages` (POST) for client requests
- Complex session management

**The new MCP spec (2025-06-18)**:
- Single `/api/mcp/{deployment_id}` endpoint
- Supports both GET (for event streams) and POST (for requests)
- Simpler session management via `Mcp-Session-Id` header
- Called "Streamable HTTP"

I tasked Claude Code:

```
Implement MCP Streamable HTTP transport per 2025-06-18 spec:
- Single endpoint: /api/mcp/{deployment_id}
- Support GET (event stream) and POST (JSON-RPC requests)
- Session management via Mcp-Session-Id header
- Protocol version negotiation
- Forward requests to Fly.io MCP machines
```

Claude Code generated `backend/app/api/mcp_streamable.py`:

```python
from fastapi import APIRouter, Request, Response, Header
from typing import Optional
import httpx

router = APIRouter()

@router.api_route("/api/mcp/{deployment_id}", methods=["GET", "POST"])
async def mcp_streamable_endpoint(
    deployment_id: str,
    request: Request,
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
    mcp_protocol_version: Optional[str] = Header(None, alias="Mcp-Protocol-Version")
):
    """
    Unified MCP Streamable HTTP endpoint.

    Forwards requests to Fly.io MCP machine running mcp-proxy.
    """
    # Get deployment from database
    deployment = await get_deployment(deployment_id)

    if not deployment or not deployment.machine_id:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Construct machine URL (Fly.io private network)
    machine_url = f"http://{deployment.machine_id}.vm.mcp-app.internal:8080/mcp"

    # Forward request to machine
    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            # Stream events back
            response = await client.get(machine_url, headers={
                "Mcp-Session-Id": mcp_session_id,
                "Mcp-Protocol-Version": mcp_protocol_version or "2025-06-18"
            })
        else:
            # Forward POST request
            body = await request.json()
            response = await client.post(machine_url, json=body, headers={
                "Mcp-Session-Id": mcp_session_id,
                "Mcp-Protocol-Version": mcp_protocol_version or "2025-06-18"
            })

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
```

**This code worked first try** (after I deployed MCP machines).

**Why AI succeeded here**: The MCP spec is well-documented, and HTTP proxying is a known pattern. AI had enough training data to generate correct code.

## Deploying MCP Machines

The final piece: Creating isolated Fly.io containers running MCP servers.

Each deployment needs:
1. Docker container with `mcp-proxy` (stdio → HTTP bridge)
2. User's chosen MCP package (npm or Python)
3. Injected environment variables (user credentials)
4. Exposed HTTP endpoint on port 8080

I created a shared base image:

```bash
commit f1b3e68
Date: 2025-12-14

deploy: add shared MCP host image + build scripts
```

**Dockerfile** (`deploy/Dockerfile`):
```dockerfile
FROM node:20-alpine

# Install mcp-proxy (hypothetical - actual package may vary)
RUN npm install -g @modelcontextprotocol/mcp-proxy

# Expose HTTP port
EXPOSE 8080

# Environment variables will be injected at runtime
# MCP_PACKAGE: The npm package to run (e.g., @alexarevalo.ai/mcp-server-ticktick)
# USER_CREDENTIALS: Injected as env vars

# Start mcp-proxy which runs the MCP server
CMD ["mcp-proxy", "--package", "$MCP_PACKAGE", "--port", "8080"]
```

Then deployed to Fly.io:
```bash
cd deploy
fly apps create mcp-machines
fly deploy
```

Now the backend could create machines:

```python
# backend/app/services/fly_deployment.py
async def create_machine(deployment_id: str, config: dict, credentials: dict):
    """Create Fly.io machine running MCP server"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.machines.dev/v1/apps/mcp-machines/machines",
            headers={"Authorization": f"Bearer {FLY_API_TOKEN}"},
            json={
                "name": f"mcp-{deployment_id[:8]}",
                "config": {
                    "image": "registry.fly.io/mcp-machines:latest",
                    "env": {
                        "MCP_PACKAGE": config["package"],
                        **credentials  # Inject user credentials
                    },
                    "guest": {
                        "cpu_kind": "shared",
                        "cpus": 1,
                        "memory_mb": 256
                    },
                    "restart": {"policy": "always"}
                }
            }
        )

    machine = response.json()
    return machine["id"]
```

**First machine deployment**:
```bash
commit f15370c
Date: 2025-12-14

backend: deploy Fly MCP machines + Streamable HTTP bridge
```

I created a test deployment via the frontend. Backend:
1. ✅ Encrypted credentials
2. ✅ Called Fly.io API
3. ✅ Created machine
4. ✅ Machine started and responded to health checks

I opened Claude Desktop and added:
```
https://catwalk-backend.fly.dev/api/mcp/abc-123-deployment-id
```

Claude connected. I saw:
```
✅ Connected to TickTick MCP
Tools available: list-tasks, create-task, update-task
```

I asked Claude: *"What tasks do I have today?"*

Claude:
1. Connected to backend
2. Backend forwarded to Fly.io machine
3. Machine ran `npx @alexarevalo.ai/mcp-server-ticktick`
4. MCP server used my injected credentials
5. Called TickTick API
6. Returned my tasks
7. Claude synthesized response

**It worked end-to-end.**

**This was the victory lap.** After 3 days of debugging PostgreSQL, Docker, Fly.io outages, and infrastructure quirks, **AI-assisted development had shipped a working production system.**

## What Worked vs What Didn't

### ✅ What AI Did Well

**Generated infrastructure boilerplate**:
- Dockerfile structure (I fixed CRLF issue)
- Fly.io configuration (mostly correct)
- Alembic migrations (worked first try)
- MCP Streamable HTTP proxy (worked first try)

**HTTP/API patterns**:
- FastAPI endpoints
- HTTPX async client for Fly.io API
- Request forwarding logic

**Known frameworks**:
- SQLAlchemy model relationships
- Pydantic validation schemas
- Error handling patterns

### ❌ What Required Heavy Human Intervention

**Infrastructure-specific quirks**:
- PostgreSQL driver selection (asyncpg vs psycopg3)
- Fly.io SSL parameter handling
- Docker line ending issues (Windows CRLF)
- Fly.io Postgres cluster recovery

**Dependency management**:
- Missing packages in requirements.txt (local env masked the issue)
- Didn't catch this until deployment

**Production debugging**:
- Reading Fly.io logs
- Understanding "no active leader found" error
- Deciding to destroy/recreate database

**Environmental differences**:
- Windows vs Linux shell script compatibility
- Cross-platform Docker builds

### The Pattern

**AI excels when:**
- Problem is well-documented (MCP spec, FastAPI patterns)
- Pattern exists in training data (HTTP proxying, database models)
- Environment is standard (Linux, no quirks)

**AI struggles when:**
- Infrastructure has vendor-specific quirks (Fly.io SSL, asyncpg limitations)
- Development environment != production (Windows CRLF, missing deps)
- Debugging requires reading logs and researching outages
- Trade-offs require domain expertise (psycopg3 vs asyncpg)

**Your role**: Architect, debugger, validator, and **infrastructure firefighter**.

## Key Metrics After Production Deploy

**Time Spent**: ~12 hours over 3 days
- AI code generation: 2 hours
- Dockerfile/infra setup: 1 hour
- Debugging PostgreSQL: 3 hours
- Debugging Docker CRLF: 1 hour
- Debugging missing dependencies: 1 hour
- Database recovery: 1 hour
- MCP implementation: 2 hours
- Testing end-to-end: 1 hour

**Lines of Code Added**: ~600 (mostly infrastructure)
- `Dockerfile`: ~25 lines
- `fly.toml`: ~30 lines
- `mcp_streamable.py`: ~150 lines
- `fly_deployment.py`: ~200 lines
- Deployment scripts: ~50 lines
- Config updates: ~100 lines

**Manual Coding**: ~50 lines
- Database URL validator (critical fix)
- Dockerfile CMD (avoiding shell script)
- Requirements.txt cleanup

**AI-Generated**: ~550 lines
- All API endpoints
- Fly.io machine creation logic
- MCP proxy implementation

**Production Status**:
- ✅ Backend deployed: `https://catwalk-backend.fly.dev`
- ✅ PostgreSQL running
- ✅ Health checks passing
- ✅ MCP machines deployable
- ✅ End-to-end tool calling works

## The Realization

By December 14, I had a **production system**:
- FastAPI backend on Fly.io
- PostgreSQL database with encrypted credentials
- Dynamic MCP machine deployment
- Claude Desktop successfully connecting to remote MCP servers

Built in **3 days**. Mostly AI-generated. Heavy manual debugging.

**The truth**: AI **can** build production systems, but:
- You need deep infrastructure knowledge to debug
- Cross-platform quirks still require manual intervention
- Vendor-specific edge cases aren't in training data
- **You're not writing code; you're fighting infrastructure**

And honestly? **I wouldn't have it any other way.** The alternative was weeks of manual coding. AI gave me the foundation in hours, leaving me to focus on the hard problems (architecture, debugging, trade-offs).

## Coming Next

In **Part 4**, the project takes an unexpected turn:
- Decision to pivot from SaaS to open source
- Glama registry integration (12K+ MCP servers)
- Settings UI becomes critical (Phase 0 priority)
- Roadmap complete revision
- Learning to adapt AI when the product vision changes

**Spoiler**: Sometimes the hardest part of AI orchestration isn't the code - it's knowing when to change direction.

---

**Commit References**:
- `5d1fb9f` - First Fly.io deployment
- `f15370c` - MCP machine deployment
- `f1b3e68` - Shared MCP host image
- `768d0b3` - Streamable HTTP docs alignment
- `a594680` - Frontend monorepo vendoring

**Infrastructure**:
- Fly.io: Backend + PostgreSQL
- Docker: Multi-stage builds
- PostgreSQL: psycopg3 driver (NOT asyncpg)

**Code**:
- [backend/Dockerfile](https://github.com/zenchantlive/catwalk/blob/main/backend/Dockerfile)
- [backend/app/api/mcp_streamable.py](https://github.com/zenchantlive/catwalk/blob/main/backend/app/api/mcp_streamable.py)

---

*This is Part 3 of 7. The system works in production. Now we pivot the business model.*

**Previous**: [← Part 2: Foundation](02-foundation-first-48-hours.md)
**Next**: [Part 4: The Pivot →](04-pivot-saas-to-open-source.md)
