# Current Development Status

**Last Updated**: 2025-12-13
**Current Phase**: Phase 5.5 - Backend Production Deployment (COMPLETED ✅)

---

## 🎯 What We're Building

**Catwalk Live** - A platform that transforms GitHub-hosted MCP servers into remotely accessible Streamable HTTP endpoints, deployable on Fly.io.

**Think**: Vercel for MCP Servers

---

## ✅ Completed Features

### Phase 1-3: Foundation & Analysis
- ✅ FastAPI backend with async SQLAlchemy
- ✅ Next.js 15 frontend (App Router, React 19)
- ✅ GitHub repo analysis using Claude API (OpenRouter)
- ✅ Dynamic form generation from analysis
- ✅ Credential encryption (Fernet) and secure storage
- ✅ PostgreSQL database with async session management

### Phase 4: MCP Streamable HTTP Transport
- ✅ **NEW MCP Spec 2025-06-18** - Streamable HTTP transport (replaces deprecated SSE)
- ✅ Single unified endpoint (`/api/mcp/{deployment_id}`) supporting GET + POST
- ✅ Protocol version negotiation (2025-06-18, 2025-03-26, 2024-11-05)
- ✅ Session management with `Mcp-Session-Id` header
- ✅ Proper JSON-RPC 2.0 handling (requests vs notifications)
- ✅ Tools/resources/prompts exposed to Claude
- ✅ **Connection verified**: Claude successfully connects and sees tools!

### Phase 5: Deployment Orchestration (Local)
- ✅ Analysis prompt extracts tools, resources, prompts from MCP server repos
- ✅ Frontend collects and stores MCP config in `schedule_config.mcp_config`
- ✅ Backend returns configured tools to Claude (not mock tools)
- ✅ MCP server subprocess manager implemented (works on Linux/WSL2)
- ⚠️ **NOTE**: Subprocess spawning doesn't work on Windows (asyncio limitation)

### Phase 5.5: Backend Production Deployment (NEW - COMPLETED!)
- ✅ **Backend deployed to Fly.io**: https://catwalk-live-backend-dev.fly.dev
- ✅ PostgreSQL database on Fly.io with Alembic migrations
- ✅ Health checks passing at `/api/health`
- ✅ All API endpoints publicly accessible
- ✅ Frontend configured to use production backend
- ✅ Docker image built and deployed successfully
- ✅ High availability: 2 machines for zero-downtime deployments

---

## 🎉 What Works Right Now

### Production Backend (Fly.io)
**URL**: https://catwalk-live-backend-dev.fly.dev

**Working Endpoints**:
- `GET /api/health` - Health checks (returns `{"status": "healthy"}`)
- `POST /api/analyze` - GitHub repo analysis via Claude
- `GET/POST /api/deployments` - Create and list deployments
- `GET/POST /api/mcp/{deployment_id}` - MCP Streamable HTTP endpoints
- `GET /api/forms/generate/{service}` - Dynamic credential forms

**Infrastructure**:
- PostgreSQL database (catwalk-live-db-dev)
- 512MB RAM, shared CPU
- Always-on (auto_stop_machines = "off")
- Region: San Jose (sjc)

### Local Frontend
**Running**: `npm run dev` at localhost:3000
**Backend Connection**: Configured via `.env.local` to point to Fly.io

**What You Can Test**:
1. ✅ Analyze GitHub repos
2. ✅ Create deployments (stored in database)
3. ✅ View deployment list
4. ✅ Generate credential forms
5. ✅ MCP endpoints exist and respond

---

## 🚧 What's NOT Working Yet

### Phase 6: MCP Server Container Deployment

**The Gap**: The backend creates deployment records but doesn't actually deploy MCP servers to Fly.io yet.

**Current Behavior**:
- Creates deployment in database ✅
- Stores encrypted credentials ✅
- Generates MCP endpoint URL ✅
- Returns tools/resources to Claude ✅
- **Missing**: Actual MCP server container running on Fly.io ❌

**What Needs to Be Built**:
1. `app/services/fly_deployment_service.py` - Fly Machines API client
2. Container deployment logic using Fly Machines API
3. Use `remote-mcp-pilot/deploy/Dockerfile` pattern
4. Each deployment → separate Fly machine with MCP server
5. Environment variable injection (encrypted credentials → container env)
6. Health checks and auto-restart for MCP containers

---

## 📚 Critical Lessons Learned (Fly.io Deployment)

### 1. PostgreSQL Driver Issues

**Problem**: SQLAlchemy 2.0+ requires specific driver formats for async Postgres.

**Solution Implemented**:
- ❌ `asyncpg` - Doesn't support Fly.io's SSL parameters (`sslmode`)
- ✅ `psycopg[binary]>=3.1.0` - Modern async driver, supports all SSL params
- URL format validator in `app/core/config.py` converts `postgres://` → `postgresql+psycopg://`

**Code Location**: `backend/app/core/config.py:19-32`

```python
@field_validator("DATABASE_URL")
@classmethod
def fix_postgres_url(cls, v: str) -> str:
    """Convert Fly.io's postgres:// URL to postgresql+psycopg://"""
    if v.startswith("postgres://"):
        return v.replace("postgres://", "postgresql+psycopg://", 1)
    return v
```

### 2. Shell Script Line Ending Issues

**Problem**: Shell scripts created on Windows have CRLF line endings, causing `No such file or directory` errors in Linux containers.

**Solution**:
- Avoid shell scripts entirely in Dockerfile
- Use inline commands in CMD: `CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080"]`

**Code Location**: `backend/Dockerfile:26-29`

### 3. Missing Python Dependencies

**Dependencies that caused failures**:
- `openai>=1.0.0` - Required by `app/services/analysis.py`
- `sse-starlette>=2.0.0` - Required by `app/api/mcp.py` (legacy SSE)
- `psycopg[binary]>=3.1.0` - PostgreSQL async driver

**Always verify**: All imports in the codebase have corresponding packages in `requirements.txt`

### 4. Fly.io Postgres Cluster Instability

**Problem**: Single-node Postgres clusters can enter "no active leader found" state and become unrecoverable.

**Solution**:
1. Destroy broken cluster: `fly apps destroy <db-name>`
2. Create fresh cluster: `fly postgres create`
3. Attach to backend: `fly postgres attach <db-name> --app <backend-app>`
4. Never try to repair a broken cluster - faster to recreate

### 5. Database Attachment and Credentials

**Problem**: `fly postgres attach` sometimes fails or sets wrong credentials.

**Manual Fix**:
```powershell
# If attach fails, manually set DATABASE_URL
fly secrets set DATABASE_URL="postgres://user:pass@db-name.internal:5432/dbname" --app backend-app
```

**Internal DNS**: Use `<app-name>.internal` for Fly.io internal networking

---

## 📁 Key Architecture Decisions

### MCP Transport Evolution
- **OLD** (deprecated 2024-11-05): Separate `/sse` (GET) and `/messages` (POST) endpoints
- **NEW** (2025-06-18): Single `/api/mcp/{id}` endpoint for both GET and POST
- **Why**: Streamable HTTP is more flexible and the current MCP standard

### Data Flow
```
1. User analyzes GitHub repo → Claude extracts tools/config ✅
2. User enters credentials → Encrypted and stored ✅
3. Deployment created → schedule_config.mcp_config stores tools ✅
4. MCP endpoint → Returns configured tools from database ✅
5. Tool call → Forwards to real MCP server (Phase 6 - NOT BUILT YET) ❌
```

### Database Schema
```
Deployment:
  - id (UUID)
  - name (str)
  - schedule_config (JSON) → { mcp_config: { package, tools, resources, prompts } }
  - status (str)
  - connection_url (str) → e.g., "https://catwalk-live-backend-dev.fly.dev/api/mcp/{id}"
  - created_at, updated_at

Credential:
  - id (UUID)
  - deployment_id (FK)
  - service_name (str)
  - encrypted_data (str) ← Fernet encrypted JSON
```

---

## 🔧 Tech Stack

**Backend**:
- FastAPI 0.115+ (async)
- SQLAlchemy 2.0+ (async with psycopg)
- PostgreSQL 15+ (Fly.io)
- Pydantic 2.0+
- Cryptography (Fernet)
- OpenRouter (Claude API)
- openai>=1.0.0 (for AsyncOpenAI client)
- sse-starlette>=2.0.0 (for SSE transport)

**Frontend**:
- Next.js 15 (App Router)
- React 19
- TailwindCSS 4
- Tanstack Query
- TypeScript 5+

**Infrastructure**:
- **Fly.io** (Backend deployed!)
  - Backend: catwalk-live-backend-dev
  - Database: catwalk-live-db-dev
  - Region: San Jose (sjc)
  - 512MB RAM, shared CPU, always-on

---

## 🎯 Next Steps (Phase 6)

### Immediate: Implement Fly.io MCP Server Deployment

**Goal**: When a user creates a deployment, actually spin up an MCP server container on Fly.io

**Implementation Steps**:

1. **Create Fly Deployment Service** (`app/services/fly_deployment_service.py`):
   ```python
   class FlyDeploymentService:
       async def create_machine(self, deployment_id: str, mcp_config: dict, credentials: dict):
           """Create a Fly machine running the MCP server"""
           # Use Fly Machines API
           # Reference: https://fly.io/docs/machines/api/
   ```

2. **Adapt remote-mcp-pilot Dockerfile**:
   - Base: `remote-mcp-pilot/deploy/Dockerfile` (Python + Node + mcp-proxy)
   - Modify to accept dynamic MCP package name
   - Inject credentials as environment variables
   - Example: `CMD mcp-proxy --host=0.0.0.0 --port=8080 --pass-environment -- npx -y ${MCP_PACKAGE}`

3. **Update Deployment Creation Flow**:
   - After storing deployment in database
   - Call `fly_deployment_service.create_machine()`
   - Store machine ID in deployment record
   - Update status to 'running' when healthy

4. **Implement Health Checks**:
   - Monitor MCP machine health
   - Auto-restart on failures
   - Update deployment status in database

5. **Test End-to-End**:
   - Create deployment via frontend
   - Verify Fly machine spins up
   - Connect Claude to MCP endpoint
   - Call a tool and verify it works

---

## 📝 Important Files

**Backend Core**:
- `app/api/mcp_streamable.py` - MCP Streamable HTTP endpoint (NEW spec)
- `app/api/mcp.py` - Legacy SSE transport (backwards compat)
- `app/services/mcp_process_manager.py` - Subprocess orchestration (local only)
- `app/api/deployments.py` - Deployment CRUD + server spawning
- `app/api/forms.py` - Dynamic form generation from analysis
- `app/prompts/analysis_prompt.py` - Claude analysis prompt (extracts tools)
- `app/core/config.py` - Pydantic settings with Fly.io URL converter

**Frontend Core**:
- `app/configure/page.tsx` - Deployment creation form
- `lib/api.ts` - API client (includes mcp_config flow)
- `components/dynamic-form/FormBuilder.tsx` - Dynamic credential forms
- `next.config.ts` - API proxy configuration
- `.env.local` - Backend URL (points to Fly.io)

**Infrastructure**:
- `backend/Dockerfile` - Production container (Python 3.12 + Node.js 20)
- `backend/fly.toml` - Fly.io backend configuration
- `backend/alembic/` - Database migrations
- `remote-mcp-pilot/deploy/` - Reference implementation for MCP containers

---

## 🐛 Known Issues

### 1. Windows Subprocess Limitation (Local Development)
- **Issue**: Python's asyncio doesn't support subprocesses on Windows
- **Impact**: Local MCP server testing doesn't work on Windows
- **Solution**: Run backend in WSL2 for local testing
- **Code**: `backend/app/services/mcp_process_manager.py:76-88`

### 2. No Auto-Restart for MCP Containers (Phase 6)
- **Issue**: If MCP server crashes, deployment breaks permanently
- **Solution**: Implement health checks and auto-restart in Phase 6

### 3. Credential Environment Variable Mapping
- **Issue**: Service names like `env_TICKTICK_TOKEN` need better mapping
- **Current**: Working but not elegant
- **Future**: Clean mapping in Fly deployment service

### 4. Frontend Not Deployed
- **Issue**: Frontend runs locally only
- **Solution**: Deploy to Vercel or Fly.io (future phase)

---

## 💡 Testing Checklist

### Production Backend (Fly.io) - WORKING ✅
- [x] Health endpoint responds: `curl https://catwalk-live-backend-dev.fly.dev/api/health`
- [x] Analyze endpoint works: Test via frontend
- [x] Create deployment: Test via frontend
- [x] List deployments: Test via frontend
- [x] MCP endpoint exists: `curl https://catwalk-live-backend-dev.fly.dev/api/mcp/{id}`
- [x] Database migrations applied
- [x] Credentials stored encrypted

### MCP Server Deployment (Phase 6) - NOT BUILT YET ❌
- [ ] Create deployment → Fly machine spins up
- [ ] MCP server starts in container
- [ ] Claude connects to MCP endpoint
- [ ] Tool calls work end-to-end
- [ ] Credentials injected correctly
- [ ] Health checks working
- [ ] Auto-restart on failure

---

## 🔑 Deployment Secrets (Fly.io)

**Set on catwalk-live-backend-dev**:
```bash
DATABASE_URL       # Auto-set by fly postgres attach
ENCRYPTION_KEY     # Fernet key for credential encryption
OPENROUTER_API_KEY # Claude API for repo analysis
PUBLIC_URL         # https://catwalk-live-backend-dev.fly.dev
```

**Generate Encryption Key**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📊 Deployment URLs

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://catwalk-live-backend-dev.fly.dev | ✅ Live |
| Backend Health | https://catwalk-live-backend-dev.fly.dev/api/health | ✅ Passing |
| Frontend (Local) | http://localhost:3000 | ✅ Working |
| PostgreSQL | catwalk-live-db-dev.internal (Fly private) | ✅ Running |

---

## 🚀 Quick Start (Fresh Session)

### Test Production Backend
```bash
# Health check
curl https://catwalk-live-backend-dev.fly.dev/api/health

# View logs
fly logs --app catwalk-live-backend-dev

# Check status
fly status --app catwalk-live-backend-dev
```

### Run Frontend Locally
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
# Backend proxy configured to use Fly.io
```

### Deploy Backend Changes
```bash
cd backend
fly deploy --app catwalk-live-backend-dev
```

---

## 🎓 For Future Claude Sessions

**You are currently at**: Phase 5.5 Complete, Phase 6 Not Started

**What works**: Full backend API on Fly.io, frontend locally, deployments stored in database

**What doesn't work**: Actual MCP server containers on Fly.io (Phase 6)

**Next task**: Implement `app/services/fly_deployment_service.py` to deploy MCP containers

**Reference code**: `remote-mcp-pilot/deploy/` has working Fly.io deployment

**Critical files to read first**:
1. This file (CURRENT_STATUS.md)
2. `CLAUDE.md` for deployment pitfalls
3. `context/ARCHITECTURE.md` for system design
4. `app/api/deployments.py` to see where Fly deployment should hook in
