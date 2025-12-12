# Current Development Status

**Last Updated**: 2025-12-12
**Current Phase**: Phase 5 - Deployment Orchestration (In Progress)

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

### Phase 5: Deployment Orchestration (Current)
- ✅ Analysis prompt extracts tools, resources, prompts from MCP server repos
- ✅ Frontend collects and stores MCP config in `schedule_config.mcp_config`
- ✅ Backend returns configured tools to Claude (not mock tools)
- ✅ MCP server subprocess manager implemented
- ⚠️ **BLOCKED**: Windows asyncio subprocess limitation

---

## 🚧 Current Issue: Windows Subprocess Support

### The Problem
When creating a deployment, the backend tries to spawn the MCP server as a subprocess:
```python
await asyncio.create_subprocess_exec("npx", "-y", "@package/name", ...)
# Raises: NotImplementedError on Windows
```

**Root Cause**: Python's asyncio doesn't fully support subprocesses on Windows in the same way as Linux.

### Impact
- Deployments create successfully
- Claude connects and sees tools
- But tool calls fail with "No running MCP server found"
- MCP server process never starts on Windows

### Solutions

**Option A: Use WSL2 (Recommended for local testing)**
```bash
# Run backend in WSL2 where asyncio subprocesses work
wsl
cd /mnt/c/Users/Zenchant/catwalk/catwalk-live/backend
uv run uvicorn app.main:app --reload
```

**Option B: Mock responses for Windows testing**
- Keep mock tool responses for local Windows development
- Real subprocess orchestration only works on Linux (Fly.io production)

**Option C: Use threading instead of asyncio for subprocesses on Windows**
- Implement Windows-specific subprocess handling
- More complex, not recommended

---

## 📁 Key Architecture Decisions

### MCP Transport Evolution
- **OLD** (deprecated 2024-11-05): Separate `/sse` (GET) and `/messages` (POST) endpoints
- **NEW** (2025-06-18): Single `/api/mcp/{id}` endpoint for both GET and POST
- **Why**: Streamable HTTP is more flexible and the current MCP standard

### Data Flow
```
1. User analyzes GitHub repo → Claude extracts tools/config
2. User enters credentials → Encrypted and stored
3. Deployment created → schedule_config.mcp_config stores tools
4. MCP endpoint → Returns configured tools from database
5. Tool call → Forwards to real MCP server subprocess (Linux only)
```

### Database Schema
```
Deployment:
  - id (UUID)
  - name (str)
  - schedule_config (JSON) → { mcp_config: { package, tools, resources, prompts } }
  - status (str)
  - created_at, updated_at

Credential:
  - id (UUID)
  - deployment_id (FK)
  - service_name (str)
  - encrypted_data (str) ← Fernet encrypted
```

---

## 🔧 Tech Stack

**Backend**:
- FastAPI 0.115+ (async)
- SQLAlchemy 2.0+ (async)
- PostgreSQL / SQLite
- Pydantic 2.0+
- Cryptography (Fernet)
- OpenRouter (Claude API)

**Frontend**:
- Next.js 15 (App Router)
- React 19
- TailwindCSS 4
- Tanstack Query
- TypeScript 5+

**Infrastructure** (not yet deployed):
- Fly.io (Linux containers)
- ngrok (local testing)

---

## 🎯 Next Steps

### Immediate (Unblock Development)
1. **Test on WSL2** - Verify subprocess spawning works on Linux
2. **OR** - Implement mock responses for Windows local testing

### Phase 5 Completion
3. Verify real MCP server communication (stdio ↔ JSON-RPC)
4. Test real tool calls with actual MCP servers (TickTick, GitHub, etc.)
5. Handle server crashes and restarts gracefully

### Phase 6: Fly.io Deployment
6. Create Dockerfile for MCP server containers
7. Implement Fly.io Machines API integration
8. Deploy test container to Fly.io
9. Verify remote tool calls work end-to-end

---

## 📝 Important Files

**Backend Core**:
- `app/api/mcp_streamable.py` - MCP Streamable HTTP endpoint (NEW spec)
- `app/api/mcp.py` - Legacy SSE transport (backwards compat)
- `app/services/mcp_process_manager.py` - Subprocess orchestration
- `app/api/deployments.py` - Deployment CRUD + server spawning
- `app/api/forms.py` - Dynamic form generation from analysis
- `app/prompts/analysis_prompt.py` - Claude analysis prompt (extracts tools)

**Frontend Core**:
- `app/configure/page.tsx` - Deployment creation form
- `lib/api.ts` - API client (includes mcp_config flow)
- `components/dynamic-form/FormBuilder.tsx` - Dynamic credential forms

**Infrastructure**:
- `alembic/` - Database migrations
- `infrastructure/docker/` - Dockerfile templates (for Fly.io)

---

## 🐛 Known Issues

1. **Windows asyncio subprocesses don't work** (current blocker)
   - Solution: Use WSL2 or mock responses for Windows

2. **Analysis caching**: Old analyses don't have tools extracted
   - Solution: Re-analyze repos or clear cache

3. **No server restart mechanism**: If MCP server crashes, deployment is broken
   - Solution: Add health checks and auto-restart

4. **Credentials stored as service_name**: Should map to proper env var names
   - Example: `env_TICKTICK_TOKEN` → should become `TICKTICK_TOKEN` env var
   - Current: Working but needs better mapping logic

---

## 💡 Testing Checklist

### Local Testing (WSL2/Linux required)
- [ ] Create deployment via frontend
- [ ] Verify MCP server subprocess starts (check logs)
- [ ] Connect Claude to deployment URL
- [ ] Verify tools appear in Claude
- [ ] Call a tool from Claude
- [ ] Verify real results (not mock)

### Production (Fly.io - not yet implemented)
- [ ] Deploy container to Fly.io
- [ ] Verify public URL works
- [ ] Test from Claude mobile/web
- [ ] Verify credentials are properly injected
- [ ] Test server restarts and health checks
