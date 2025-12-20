# Deployment Fix Guide

## Critical Issues Fixed

### 1. ✅ FLY_MCP_IMAGE Validation (FAIL-FAST)
**Problem**: The system had a default value `"catwalk-live/mcp-host:latest"` which is not a valid Docker image reference.

**Fix Applied**:
- Removed the invalid default value
- Added validation to reject malformed image names
- Added startup logging to show the image being used
- Added runtime check in `create_machine()` to fail immediately if image is not set

**Files Modified**:
- `backend/app/core/config.py` - Removed default, added validator
- `backend/app/services/fly_deployment_service.py` - Added fail-fast checks

### 2. ✅ Cache Transaction Handling (ANTI-PATTERN REMOVED)
**Problem**: `CacheService` was calling `commit()` and `rollback()` inside service methods, breaking transaction boundaries and causing `InFailedSqlTransaction` errors.

**Fix Applied**:
- Removed `await self.session.commit()` from `set_analysis()`
- Removed `await self.session.rollback()` from error handlers
- Moved transaction control to the route handler (`analyze.py`)
- Added `flush()` instead of `commit()` to stage changes without committing

**Files Modified**:
- `backend/app/services/cache.py` - Removed transaction management
- `backend/app/api/analyze.py` - Added explicit `db.commit()` and `db.rollback()`

### 3. ✅ URL Normalization (CACHE HITS NOW WORK)
**Problem**: Cache keys were sensitive to trailing slashes and case differences, causing cache misses.

**Fix Applied**:
- Created `app/utils/url_helpers.py` with `normalize_github_url()` function
- Normalizes to lowercase and strips trailing slashes
- Applied normalization in `analyze.py` before cache lookups

**Examples**:
- `https://github.com/user/repo` ✅
- `https://github.com/user/repo/` ✅ (normalized to above)
- `https://GitHub.com/user/repo` ✅ (normalized to above)

**Files Created/Modified**:
- `backend/app/utils/url_helpers.py` - New normalization utility
- `backend/app/utils/__init__.py` - Package marker
- `backend/app/api/analyze.py` - Uses normalization

### 4. ✅ Observability Logging
**Added logging throughout**:
- FlyDeploymentService logs image configuration on startup
- Cache service logs hits, misses, and expiration details
- Analyze route logs normalization, cache status, and errors

---

## Required Action: Build and Set FLY_MCP_IMAGE

The backend will now **fail immediately** if `FLY_MCP_IMAGE` is not set when trying to create a deployment.

### Step 1: Build and Push the MCP Server Image

We've created a new Docker image in `deploy/` that will be used for all MCP server containers.

**From Windows PowerShell:**
```powershell
cd catwalk-live\deploy
.\build-and-push.ps1
```

**From WSL/Linux:**
```bash
cd catwalk-live/deploy
./build-and-push.sh
```

**Or manually:**
```bash
cd deploy
fly deploy --build-only --push --app <your-mcp-app>
```

This will output something like:
```
--> Building image with Fly
...
--> Pushing image to registry.fly.io/<your-mcp-app>:deployment-01JEXXX
```

### Step 2: Set the Image in Backend Secrets

Copy the image name from Step 1 (the full `registry.fly.io/...` path) and run:

```bash
fly secrets set FLY_MCP_IMAGE="registry.fly.io/<your-mcp-app>:deployment-01JEXXX" \
  --app <your-backend-app>
```

**Note**: Replace `deployment-01JEXXX` with the actual deployment ID from your build output.

---

## Deploy the Fixes

```bash
cd backend
fly deploy --app <your-backend-app>
```

---

## Verify the Fixes

### 1. Check Startup Logs
```bash
fly logs --app <your-backend-app>
```

**Look for**:
```
FlyDeploymentService initialized:
  - App Name: <your-mcp-app>
  - Image: registry.fly.io/catwalk-live-mcp-host:latest
  - API Token: SET
```

If you see `Image: NOT SET (WILL FAIL!)`, the environment variable is missing.

### 2. Test Cache Behavior

**First request** (cache miss):
```bash
curl -X POST https://<your-backend-app>.fly.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

**Second request** (cache hit):
```bash
curl -X POST https://<your-backend-app>.fly.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo/"}'  # Note trailing slash
```

**Expected**: Second request should return `"status": "cached"` even with the trailing slash.

### 3. Check Cache Table
```bash
fly postgres connect --app <your-database-app>
```

```sql
SELECT repo_url, created_at, updated_at FROM analysis_cache;
```

**Expected**: URLs should all be lowercase with no trailing slashes.

### 4. Test Deployment Creation

Try creating a deployment via the frontend. The error should now be **clear**:

**Before**: `invalid image identifier`
**After**: `FLY_MCP_IMAGE is not configured. Set this environment variable to a valid Docker image...`

---

## Summary of Changes

| Issue | Status | Impact |
|-------|--------|--------|
| Invalid default image | ✅ Fixed | Deployment errors are now clear and actionable |
| Broken transactions | ✅ Fixed | No more `InFailedSqlTransaction` errors |
| Cache misses | ✅ Fixed | Cache now works correctly regardless of URL format |
| Silent failures | ✅ Fixed | All errors now logged with context |

---

## Next Steps

1. **Set FLY_MCP_IMAGE** environment variable (see above)
2. **Deploy the backend**: `fly deploy --app <your-backend-app>`
3. **Monitor logs**: `fly logs --app <your-backend-app>`
4. **Test analysis caching**: Try analyzing the same repo twice
5. **Test deployment creation**: Create a deployment and check for clear error messages

---

## Technical Debt Addressed

### Before
- ✗ Services managed their own transactions (anti-pattern)
- ✗ Configuration had invalid defaults (silent failures)
- ✗ Cache keys were inconsistent (broken caching)
- ✗ No logging (debugging was impossible)

### After
- ✓ Routes manage transactions (proper layering)
- ✓ Configuration fails fast on invalid values (observability)
- ✓ Cache keys are normalized (predictable behavior)
- ✓ Comprehensive logging (easy debugging)

---

## For Future Sessions

**When debugging**:
1. Always check `fly logs` for startup messages
2. Look for "FlyDeploymentService initialized" to verify config
3. Look for "Cache hit/miss" messages to verify caching
4. Transaction errors should now include full stack traces

**When adding new services**:
1. Never call `commit()` or `rollback()` inside service methods
2. Always normalize user input (URLs, etc.) before using as keys
3. Add logging at INFO level for key operations
4. Add logging at DEBUG level for cache hits/misses
