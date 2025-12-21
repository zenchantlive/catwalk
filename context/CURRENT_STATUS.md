# Current Development Status

**Last Updated**: 2025-12-21
**Current Phase**: Phase 6 - MCP Server Container Deployment (WORKING ✅) + PR #10 Security Hardening (COMPLETE ✅)

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
- ✅ **Backend deployed to Fly.io**: https://<your-backend-app>.fly.dev
- ✅ PostgreSQL database on Fly.io with Alembic migrations
- ✅ Health checks passing at `/api/health`
- ✅ All API endpoints publicly accessible
- ✅ Frontend configured to use production backend
- ✅ Docker image built and deployed successfully
- ✅ Always-on backend with `min_machines_running = 1`
- ✅ **RegistryService Refactored**: Concurrency safety, timeouts, and robustness improvements

### Phase 6: MCP Server Container Deployment (WORKING ✅)
- ✅ Backend creates Fly Machines for deployments (when `FLY_API_TOKEN` is set)
- ✅ Shared MCP machine image runs `mcp-proxy` exposing Streamable HTTP at `GET/POST /mcp`
- ✅ Backend forwards Streamable HTTP to the MCP machine over Fly private networking
- ✅ End-to-end connectivity verified from backend → machine on `:8080`

### Phase 1: Validation & Error Handling (NEW - COMPLETED! ✅)
- ✅ Package validation (npm and PyPI registries)
- ✅ Credential validation (required fields checked)
- ✅ Structured error responses with actionable help messages
- ✅ Frontend error display (user-visible error messages)
- ✅ Runtime detection (npm vs Python automatic)

### Phase 0: User Settings & Key Management (COMPLETED! ✅)
- ✅ Glassmorphic Sign-In Modal (integrated with NextAuth)
- ✅ User Settings Page (/settings) with API key management
- ✅ Backend Settings API (CRUD + Validation)
- ✅ End-to-end encryption for stored credentials
- ✅ **Security Hardening**:
  - Secrets masked in API responses (never return plaintext)
  - Internal `/auth/sync-user` endpoint secured with `X-Auth-Secret`
  - Audit logging enabled for critical actions

### PR #10: Security & Maintainability Hardening (2025-12-21 - COMPLETED! ✅)
- ✅ **Fixed JWT secret mismatch** - Changed from NEXTAUTH_SECRET to AUTH_SECRET
- ✅ **Consolidated auth modules** - Removed duplicate middleware/auth.py
- ✅ **Removed hardcoded URLs** - Frontend uses relative paths and dedicated NEXT_PUBLIC_BACKEND_URL
- ✅ **Database-managed timestamps** - Migrated to func.now() for reliability
- ✅ **Fixed Alembic migration** - Proper foreign key constraint naming
- ✅ **Updated all tests** - 51 tests passing, zero warnings
- ✅ **Pydantic V2 migration** - ConfigDict instead of class Config
- ✅ **SQLAlchemy 2.0 migration** - Updated declarative_base import
- ✅ All P0 (critical security) and P1 (maintainability) issues resolved

### Serena Memory Organization (2025-12-21 - NEW! 📚)
**Location**: `.serena/` directory in project root

Comprehensive organized memories for efficient project context retrieval:
1. **01-architecture-overview.md** - System design, data flow, tech stack
2. **02-infrastructure-deployment.md** - Fly.io, PostgreSQL, Docker, networking
3. **03-features-and-status.md** - What works, what doesn't, implementation details
4. **04-security-hardening.md** - Auth, encryption, validation, best practices
5. **05-development-workflows.md** - Common tasks, testing, debugging, deployment
6. **06-api-reference.md** - Complete endpoint documentation
7. **07-recent-changes-pr10.md** - PR #10 fixes and learnings

**Access**: If Serena MCP is unavailable, memories exist as markdown files in `.serena/`

**Purpose**: Quick context retrieval for complex questions about architecture, security, APIs, workflows

---

## 🎉 What Works Right Now

### Production Backend (Fly.io)
**URL**: https://<your-backend-app>.fly.dev

**Working Endpoints**:
- `GET /api/health` - Health checks (returns `{"status": "healthy"}`)
- `POST /api/analyze` - GitHub repo analysis via Claude
- `GET/POST /api/deployments` - Create and list deployments
- `GET/POST /api/mcp/{deployment_id}` - MCP Streamable HTTP endpoints
- `GET /api/forms/generate/{service}` - Dynamic credential forms

**Infrastructure**:
- PostgreSQL database (<your-database-app>)
- 512MB RAM, shared CPU
- Always-on (auto_stop_machines = "off")
- Region: San Jose (sjc)

### Local Frontend
**Running**: `bun run dev` at localhost:3000
**Backend Connection**: Configured via `.env.local` to point to Fly.io

**What You Can Test**:
1. ✅ Analyze GitHub repos
2. ✅ Create deployments (stored in database)
3. ✅ View deployment list
4. ✅ Generate credential forms
5. ✅ MCP endpoints exist and respond

---

## 🚧 What's NOT Working Yet

### Hardening + UX (Next - Phase 2)

What remains (now that validation and deployment work):
- ✅ ~~Package and credential validation~~ (COMPLETED in Phase 1!)
- Health monitoring loop (beyond Fly restart policy) and better "unhealthy" status reporting
- Clear progress/status surfaced to the frontend during machine start and package install

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
- `email-validator>=2.1.0` - Required by Pydantic for EmailStr (caused crash loop on Fly)


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
fly secrets set DATABASE_URL="postgresql+psycopg://user:pass@db-name.internal:5432/dbname" --app backend-app
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
5. Tool call → Forwarded to deployed MCP machine (Streamable HTTP) ✅
```

### Streamable HTTP Bridging Details (Production)

- Claude-visible URL (stable): `https://<your-backend-app>.fly.dev/api/mcp/{deployment_id}`
- Backend → machine (Fly private network): `http://{machine_id}.vm.<your-mcp-app>.internal:8080/mcp`
- MCP machine endpoints (mcp-proxy):
  - `GET /status` (health)
  - `GET/POST /mcp` (Streamable HTTP)
- When calling `/mcp` directly, mcp-proxy requires `Accept: application/json`

### Database Schema
```
Deployment:
  - id (UUID)
  - name (str)
  - schedule_config (JSON) → { mcp_config: { package, tools, resources, prompts } }
  - status (str)
  - connection_url (str) → e.g., "https://<your-backend-app>.fly.dev/api/mcp/{id}"
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
- sse-starlette>=2.0.0 (legacy SSE transport; Streamable HTTP is primary)

**Frontend**:
- Next.js 15 (App Router)
- React 19
- TailwindCSS 4
- Tanstack Query
- TypeScript 5+

**Infrastructure**:
- **Fly.io** (Backend deployed!)
  - Backend: <your-backend-app>
  - Database: <your-database-app>
  - Region: San Jose (sjc)
  - 512MB RAM, shared CPU, always-on

---

## 🎯 Next Steps

### Immediate: Make “any GitHub link” predictable

Hard requirements for a repo to deploy successfully:
1. Analysis must yield a runnable npm package name in `schedule_config.mcp_config.package`
2. Deployed machine must receive `MCP_PACKAGE` and required env vars
3. Package must run under `npx -y $MCP_PACKAGE` (current MVP assumption)

Operational checks (from within the backend machine):
- `curl http://{machine_id}.vm.<your-mcp-app>.internal:8080/status`
- `curl -H 'accept: application/json' -H 'content-type: application/json' -H 'MCP-Protocol-Version: 2025-06-18' http://{machine_id}...:8080/mcp --data '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{...}}'`

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
- [x] Health endpoint responds: `curl https://<your-backend-app>.fly.dev/api/health`
- [x] Analyze endpoint works: Test via frontend
- [x] Create deployment: Test via frontend
- [x] List deployments: Test via frontend
- [x] MCP endpoint exists: `curl https://<your-backend-app>.fly.dev/api/mcp/{id}`
- [x] Database migrations applied
- [x] Credentials stored encrypted

### MCP Server Deployment (Phase 6) - WORKING ✅
- [x] Create deployment → Fly machine spins up
- [x] MCP server starts in container
- [x] Claude connects to MCP endpoint
- [x] Tool calls work end-to-end
- [x] Credentials injected correctly
- [ ] Health monitoring loop (future)

---

## 🔑 Deployment Secrets (Fly.io)

**Set on <your-backend-app>**:
```bash
DATABASE_URL       # Auto-set by fly postgres attach
ENCRYPTION_KEY     # Fernet key for credential encryption
OPENROUTER_API_KEY # Claude API for repo analysis
PUBLIC_URL         # https://<your-backend-app>.fly.dev
```

**Generate Encryption Key**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📊 Deployment URLs

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://<your-backend-app>.fly.dev | ✅ Live |
| Backend Health | https://<your-backend-app>.fly.dev/api/health | ✅ Passing |
| Frontend (Local) | http://localhost:3000 | ✅ Working |
| PostgreSQL | <your-database-app>.internal (Fly private) | ✅ Running |

---

## 🚀 Quick Start (Fresh Session)

### Test Production Backend
```bash
# Health check
curl https://<your-backend-app>.fly.dev/api/health

# View logs
fly logs --app <your-backend-app>

# Check status
fly status --app <your-backend-app>
```

### Run Frontend Locally
```bash
cd frontend
bun install
bun run dev
# Opens at http://localhost:3000
# Backend proxy configured to use Fly.io
```

### Deploy Backend Changes
```bash
cd backend
fly deploy --app <your-backend-app>
```

---

## 🎓 For Future Claude Sessions

**You are currently at**: Phase 1 Complete! + Phase 6 Working + PR #10 Security Hardening Complete!

**What works**:
- Full backend API on Fly.io (production-ready, secure)
- Frontend locally with error display
- Package validation (npm/PyPI)
- Credential validation
- Deployments with structured error messages
- End-to-end MCP tool calls
- JWT authentication (fixed secret mismatch)
- Database-managed timestamps (reliable)
- All tests passing (51 tests, zero warnings)

**What doesn't work**: Health monitoring loop + richer deployment progress (Phase 2)

**Next task**: Phase 2 - Health Monitoring & Status tracking (see `context/plans/roadmap/phase-2-monitoring.md`)

**Reference code**: `remote-mcp-pilot/deploy/` has working Fly.io deployment

**Serena Memories Available** (`.serena/` directory):
- **Use memories first** for architecture, security, API, workflow questions
- Memories are comprehensive and up-to-date (includes PR #10 fixes)
- Faster than reading entire files
- Example: "What's the architecture?" → Read memory `01-architecture-overview.md`

**Critical files to read first**:
1. This file (CURRENT_STATUS.md)
2. **Serena memories** (`.serena/*.md`) - Quick context on any topic
3. `CLAUDE.md` for deployment pitfalls
4. `context/ARCHITECTURE.md` for detailed system design
5. `app/api/deployments.py` to see validation integration
6. `PR10_FIXES_SUMMARY.md` for recent security fixes
