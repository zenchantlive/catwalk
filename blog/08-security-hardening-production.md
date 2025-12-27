---
title: "Part 8: Security Hardening & Production Ready"
series: "Catwalk Live Development Journey"
part: 8
date: 2025-12-21
updated: 2025-12-27
tags: [security, testing, production, hardening, deployment]
reading_time: "14 min"
commits_covered: "02f9346...890c67a"
---

## The Final Push

December 21, 2025. The platform works:
- ✅ Users can sign in
- ✅ Analysis extracts MCP config
- ✅ Validation prevents security holes
- ✅ Deployments create Fly machines
- ✅ Claude successfully calls tools

But "works" ≠ "production-ready."

**What's missing**:
- Tests (we have... zero)
- Security hardening (beyond basic validation)
- Error handling for edge cases
- Production deployment (frontend still localhost only)
- Performance optimization

Time to go from **"working prototype"** to **"production system"**.

## PR #12: The Testing Blitz

### The Problem

No tests. Not a single one. Every change was tested manually: deploy, click around, check logs.

**This doesn't scale.**

AI (Claude Code) was prompted:

> Write comprehensive integration tests for all API endpoints. Cover:
> - Health checks
> - Authentication
> - Analysis (cache hit/miss)
> - Deployments (create, list, get)
> - MCP endpoints
> - Settings management
> - Registry search

### The Result: 51 Tests

```python
# backend/tests/integration/test_api_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint should return 200 OK"""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

# backend/tests/integration/test_api_analyze.py
@pytest.mark.asyncio
async def test_analyze_repo_success(client: AsyncClient):
    """Analysis should succeed for valid MCP repo"""
    response = await client.post(
        "/api/analyze",
        json={"repo_url": "https://github.com/hong-hao/mcp-ticktick"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "package" in data
    assert "env_vars" in data

@pytest.mark.asyncio
async def test_analyze_cache_hit(client: AsyncClient, mock_claude_api):
    """Second analysis should hit cache"""
    repo_url = "https://github.com/hong-hao/mcp-ticktick"

    # First request (cache miss)
    response1 = await client.post("/api/analyze", json={"repo_url": repo_url})
    assert mock_claude_api.call_count == 1

    # Second request (cache hit)
    response2 = await client.post("/api/analyze", json={"repo_url": repo_url})
    assert mock_claude_api.call_count == 1  # Still 1 (not called again)
    assert response2.json() == response1.json()

# backend/tests/integration/test_api_deployments.py
@pytest.mark.asyncio
async def test_create_deployment_unauthorized(client: AsyncClient):
    """Creating deployment without auth should return 401"""
    response = await client.post(
        "/api/deployments",
        json={"name": "Test", "repo_url": "..."}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_deployment_success(
    auth_client: AsyncClient,
    mock_analysis,
    mock_fly_api
):
    """Authenticated user can create deployment"""
    response = await auth_client.post(
        "/api/deployments",
        json={
            "name": "My TickTick",
            "repo_url": "https://github.com/hong-hao/mcp-ticktick",
            "credentials": {"TICKTICK_TOKEN": "test-token"}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My TickTick"
    assert data["status"] == "deploying"
    assert "id" in data
    assert "access_token" in data
```

**Unit tests for services**:

```python
# backend/tests/unit/test_registry_service.py
@pytest.mark.asyncio
async def test_validate_npm_package_exists():
    """Should validate existing npm package"""
    service = RegistryService()
    result = await service.validate_npm_package("@modelcontextprotocol/sdk")
    assert result is True

@pytest.mark.asyncio
async def test_validate_npm_package_not_found():
    """Should raise error for non-existent package"""
    service = RegistryService()
    with pytest.raises(ValidationError, match="not found"):
        await service.validate_npm_package("@fake/nonexistent-package-xyz")

# backend/tests/unit/test_mcp_process_manager.py
@pytest.mark.asyncio
async def test_spawn_process_npm():
    """Should spawn npm MCP server process"""
    manager = MCPProcessManager()
    process = await manager.spawn(
        package="@modelcontextprotocol/server-filesystem",
        env={"ALLOWED_DIRECTORIES": "/tmp"}
    )
    assert process.returncode is None  # Running
    await manager.kill(process.pid)
```

### Test Coverage

```bash
pytest --cov=app tests/

Coverage Report:
  app/api/analyze.py          92%
  app/api/deployments.py      88%
  app/api/mcp_streamable.py   85%
  app/services/               91%
  app/middleware/             94%

  Total:                      89%
```

**89% coverage.** Not perfect, but solid.

### What Tests Caught

Running tests revealed bugs:

1. **Cache expiration bug**: Timezone-aware vs naive datetime comparison

```python
# Bug: This fails when database returns timezone-aware datetime
if datetime.now() > cached.expires_at:
    return None

# Fix: Use UTC explicitly
if datetime.utcnow() > cached.expires_at:
    return None
```

2. **Credential validation bug**: Didn't handle optional env vars correctly

```python
# Bug: Required all env vars, even optional ones
missing = [v for v in env_vars if v.name not in credentials]

# Fix: Only check required env vars
missing = [
    v for v in env_vars
    if v.required and v.name not in credentials
]
```

3. **Deployment background task bug**: Credentials not passed to Fly API

```python
# Bug: credentials_data undefined in background task scope
background_tasks.add_task(deploy_to_fly, deployment.id)

# Fix: Pass credentials explicitly
background_tasks.add_task(
    deploy_to_fly,
    deployment.id,
    credentials_data=credentials
)
```

**Lesson**: Tests find bugs that manual testing misses. Always test edge cases.

## PR #13: Security Hardening

### The CodeRabbit Review

After PR #12 merged, CodeRabbit reviewed the entire codebase. Findings:

#### 1. Secrets Leaking in Logs

**Issue**:
```python
logger.info(f"Creating deployment: {deployment.dict()}")
# Logs: {..., "credentials": {"TICKTICK_TOKEN": "secret-value"}}
```

**Fix**: Filter sensitive fields

```python
def safe_dict(obj, exclude_fields=["credentials", "access_token", "encrypted_data"]):
    """Convert model to dict, excluding sensitive fields"""
    data = obj.dict() if hasattr(obj, 'dict') else dict(obj)
    return {k: v for k, v in data.items() if k not in exclude_fields}

logger.info(f"Creating deployment: {safe_dict(deployment)}")
# Logs: {..., "name": "My TickTick", "status": "deploying"}  # No secrets
```

#### 2. CORS Misconfiguration

**Issue**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows ANY origin
    allow_credentials=True
)
```

**Fix**: Restrict to specific origins

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "https://catwalk.vercel.app"  # Production frontend
    ],
    allow_credentials=True
)
```

#### 3. MCP Endpoint Access Control

**Issue**: MCP endpoints were public - anyone with the URL could call tools.

**Fix**: Access token authentication

```python
@router.api_route("/mcp/{deployment_id}", methods=["GET", "POST"])
async def mcp_streamable(
    deployment_id: str,
    request: Request,
    x_access_token: str = Header(None, alias="X-Access-Token")
):
    """MCP endpoint with access token auth"""
    deployment = await get_deployment(deployment_id)

    # Validate access token
    if not x_access_token or x_access_token != deployment.access_token:
        raise HTTPException(401, "Invalid or missing access token")

    # ... rest of MCP proxying
```

Claude Desktop config now includes token:

```json
{
  "mcpServers": {
    "ticktick": {
      "url": "https://backend.fly.dev/api/mcp/{id}",
      "headers": {
        "X-Access-Token": "deployment-specific-token"
      }
    }
  }
}
```

#### 4. Access Token Rotation

**Issue**: If a token leaks, no way to invalidate it.

**Fix**: Token rotation endpoint

```python
@router.post("/deployments/{deployment_id}/rotate-token")
async def rotate_deployment_token(
    deployment_id: str,
    user: User = Depends(get_current_user)
):
    """
    Rotate deployment access token.

    Generates new token, invalidates old one.
    """
    deployment = await get_deployment(deployment_id)

    # Verify ownership
    if deployment.user_id != user.id:
        raise HTTPException(403, "Not your deployment")

    # Generate new token
    new_token = secrets.token_urlsafe(32)
    old_token = deployment.access_token

    # Update deployment
    deployment.access_token = new_token
    await db.commit()

    # Log rotation for security audit
    logger.warning(
        "Access token rotated",
        extra={
            "deployment_id": deployment_id,
            "user_id": user.id,
            "old_token_prefix": old_token[:8],
            "new_token_prefix": new_token[:8]
        }
    )

    return {"access_token": new_token, "message": "Token rotated successfully"}
```

**User workflow**:
1. Token leaked? Click "Rotate Token" in UI
2. New token generated
3. Update Claude Desktop config with new token
4. Old token immediately invalid

### Audit Logging

Added audit trail for security events:

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    action = Column(String)  # "deployment_created", "token_rotated", etc.
    resource_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

# Log security events
async def log_audit(user_id, action, resource_id, metadata=None):
    async with get_session() as db:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_id=resource_id,
            metadata=metadata or {}
        )
        db.add(log)
        await db.commit()

# Example usage
await log_audit(
    user_id=user.id,
    action="deployment_created",
    resource_id=deployment.id,
    metadata={"package": deployment.schedule_config["mcp_config"]["package"]}
)
```

**Why audit logs**: Compliance, security monitoring, debugging.

## Frontend Deployment to Vercel

### The Problem

Frontend ran locally (`localhost:3000`). No production deployment.

**Steps to deploy**:

1. **Environment variables** (Vercel dashboard):

```env
NEXT_PUBLIC_BACKEND_URL=https://catwalk-backend.fly.dev
AUTH_SECRET=<matching-backend-secret>
AUTH_SYNC_SECRET=<matching-backend-secret>
GOOGLE_CLIENT_ID=<oauth-client-id>
GOOGLE_CLIENT_SECRET=<oauth-client-secret>
```

2. **Deploy**: `vercel deploy --prod`

3. **Build failed**:

```
Error: Cannot find module './vitest.config.mts'
```

**Problem**: `tsconfig.json` was trying to compile Vitest config (a dev-only file).

**Fix**: Exclude test configs from production build:

```json
{
  "exclude": [
    "node_modules",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.mts"
  ]
}
```

4. **SSR error**: "useSearchParams must be wrapped in Suspense"

**Problem**: SignInModal used `useSearchParams()` without Suspense boundary.

**Fix**:

```tsx
// app/layout.tsx
import { Suspense } from 'react'
import SignInModal from '@/components/auth/SignInModal'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <Suspense fallback={null}>
          <SignInModal />
        </Suspense>
        {children}
      </body>
    </html>
  )
}
```

5. **Success**: Frontend deployed to Vercel!

**Production URLs**:
- Frontend: `https://catwalk.vercel.app`
- Backend: `https://catwalk-backend.fly.dev`

## Performance Optimizations

### 1. Analysis Cache Improvements

**Before**: Cache expiration checked on every request.

**After**: Background cleanup task.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", hours=1)
async def cleanup_expired_cache():
    """Remove expired cache entries (runs every hour)"""
    async with get_session() as db:
        await db.execute(
            delete(AnalysisCache).where(
                AnalysisCache.expires_at < datetime.utcnow()
            )
        )
        await db.commit()

# Start scheduler on app startup
@app.on_event("startup")
async def startup():
    scheduler.start()
```

**Benefit**: Faster queries (no expiration check), database stays clean.

### 2. Registry Validation Concurrency

**Before**: Validate package sequentially.

```python
# Slow (2 sequential API calls)
syntax_valid = validate_syntax(package)
npm_exists = await validate_npm_package(package)
```

**After**: Validate concurrently.

```python
# Fast (parallel validation)
await asyncio.gather(
    validate_syntax(package),
    validate_npm_package(package)
)
```

**Improvement**: 300ms → 150ms average validation time.

### 3. Database Connection Pooling

**Before**: Create new connection per request.

**After**: Connection pool.

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Max 20 connections
    max_overflow=10,     # Extra 10 if pool full
    pool_pre_ping=True,  # Check connection alive before use
    pool_recycle=3600    # Recycle connections after 1 hour
)
```

**Benefit**: Faster queries, fewer connection errors.

## Production Checklist

Before declaring "production-ready":

- [x] **Tests**: 51 integration + unit tests, 89% coverage
- [x] **Security**: CodeRabbit review passed, secrets masked, CORS restricted
- [x] **Authentication**: JWT + OAuth, user sync working
- [x] **Validation**: Package + credential validation
- [x] **Error handling**: User-friendly messages, audit logging
- [x] **Deployment**: Backend on Fly.io, frontend on Vercel
- [x] **Monitoring**: Health checks, structured logs
- [x] **Documentation**: API docs, troubleshooting guides
- [x] **Performance**: Caching, connection pooling, concurrent validation
- [ ] **Health monitoring loop**: Proactive unhealthy state detection (Phase 8)

**Status**: Production-ready (with known gaps documented).

## What I Learned

### Where AI Excelled ✅
- Test generation (51 tests from prompt)
- Security patterns (secret filtering, CORS config)
- Boilerplate (audit logging, schedulers)

### Where AI Failed ❌
- **Test quality**: Many tests too shallow (only happy path)
- **Security thinking**: Didn't proactively suggest token rotation
- **Edge cases**: Didn't catch timezone datetime bug
- **Deployment**: No guidance on Vercel SSR issues

### Human Expertise Required 🧠
- **Security review**: Reading CodeRabbit feedback, prioritizing fixes
- **Test design**: What scenarios matter? What edge cases exist?
- **Performance tuning**: Where are bottlenecks? How to optimize?
- **Production deployment**: Environment variables, build configs, SSR

**The pattern**: AI generates code. Humans ensure **production quality**.

## Up Next

The platform is production-ready:
- ✅ Comprehensive tests
- ✅ Security hardened
- ✅ Deployed to production (frontend + backend)
- ✅ Performance optimized

But this is just **Part 8**. There's one more story to tell: **Reflections on AI-orchestrated development**.

What worked? What didn't? How has AI changed the role of the engineer? What's next?

That's Part 9: The conclusion.

---

**Key Commits**:
- `02f9346` - Comprehensive API hardening, refactored auth flow, major test suite expansion
- `690fa1d` - Address security, stability, and logic review feedback
- `d0766bf` - Fix security: refine logging, restrict cache, fix proxy
- `27717d1` - PR #12: Testing and cache improvements
- `937f01e` - PR #13: Security hardening
- `890c67a` - Access token rotation for deployments

**Related Files**:
- `backend/tests/` - 51 integration and unit tests
- `backend/app/middleware/logging.py` - Secret filtering
- `backend/app/api/deployments.py` - Token rotation endpoint

**Production URLs**:
- Frontend: https://catwalk.vercel.app
- Backend: https://catwalk-backend.fly.dev

**Next Post**: [Part 9: Reflections - AI-Orchestrated Development](09-reflections-ai-orchestration.md)
