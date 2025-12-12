# MCP Remote Platform - API Specification

## Base URL

**Development:** `http://localhost:8000`
**Production:** `https://api.mcp-remote.fly.dev` (example)

## Authentication

**MVP:** No authentication (private platform)
**Phase 8:** Bearer token (OAuth)

```
Authorization: Bearer <token>
```

## Common Response Formats

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": { ... },
    "retry_allowed": true
  }
}
```

### Error Codes
- `invalid_request`: Bad request (400)
- `analysis_failed`: Claude API error (503)
- `deployment_failed`: Fly.io error (503)
- `not_found`: Resource doesn't exist (404)
- `rate_limited`: Too many requests (429)

## Endpoints

### 1. Analyze Repository

**POST /api/analyze**

Analyzes a GitHub MCP repository using Claude API with web search.

**Request:**
```json
{
  "github_url": "https://github.com/user/mcp-server-repo",
  "force_refresh": false
}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "github_url": "https://github.com/user/mcp-server-repo",
    "package_name": "@user/mcp-server-ticktick",
    "display_name": "TickTick MCP",
    "env_vars": [
      {
        "name": "TICKTICK_CLIENT_ID",
        "description": "Your TickTick OAuth Client ID from developer portal",
        "required": true,
        "secret": false,
        "default": null
      },
      {
        "name": "TICKTICK_CLIENT_SECRET",
        "description": "Your TickTick OAuth Client Secret",
        "required": true,
        "secret": true,
        "default": null
      },
      {
        "name": "TICKTICK_ACCESS_TOKEN",
        "description": "OAuth access token for your TickTick account",
        "required": true,
        "secret": true,
        "default": null
      }
    ],
    "run_command": "npx -y @user/mcp-server-ticktick",
    "notes": "Requires TickTick OAuth application. Get credentials at: https://developer.ticktick.com",
    "cached": false,
    "analyzed_at": "2025-01-15T10:30:00Z"
  }
}
```

**Errors:**
- `400`: Invalid GitHub URL
- `503`: Claude API unavailable
- `429`: Rate limit exceeded

**Query Parameters:**
- `force_refresh`: Skip cache (default: false)

**[ASSUMPTION: Analysis results editable in frontend before deploying. User can override any field.]**

---

### 2. Get Cached Analysis

**GET /api/analysis/{id}**

Retrieves a previously cached analysis.

**Response (200 OK):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "github_url": "https://github.com/user/mcp-server-repo",
    "package_name": "@user/mcp-server-ticktick",
    "display_name": "TickTick MCP",
    "env_vars": [...],
    "run_command": "npx -y @user/mcp-server-ticktick",
    "notes": "...",
    "cached": true,
    "analyzed_at": "2025-01-15T10:30:00Z",
    "expires_at": "2025-01-16T10:30:00Z"
  }
}
```

**Errors:**
- `404`: Analysis not found or expired

---

### 3. Create Deployment

**POST /api/deployments**

Deploys an MCP server to Fly.io with user credentials.

**Request:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "credentials": {
    "TICKTICK_CLIENT_ID": "abc123",
    "TICKTICK_CLIENT_SECRET": "secret456",
    "TICKTICK_ACCESS_TOKEN": "token789"
  },
  "config_override": {
    "display_name": "My TickTick Server",
    "fly_region": "sjc"
  }
}
```

**Response (202 Accepted):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "deploying",
    "github_url": "https://github.com/user/mcp-server-repo",
    "display_name": "My TickTick Server",
    "package_name": "@user/mcp-server-ticktick",
    "machine_id": null,
    "sse_url": null,
    "fly_region": "sjc",
    "estimated_monthly_cost": 1.94,
    "created_at": "2025-01-15T10:35:00Z"
  }
}
```

**Polling for completion:**
```
GET /api/deployments/{id}/status
```

**Final state (200 OK):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "running",
    "github_url": "https://github.com/user/mcp-server-repo",
    "display_name": "My TickTick Server",
    "package_name": "@user/mcp-server-ticktick",
    "machine_id": "a3f9x2k1",
    "sse_url": "https://a3f9x2k1.fly.dev/sse",
    "fly_region": "sjc",
    "estimated_monthly_cost": 1.94,
    "created_at": "2025-01-15T10:35:00Z",
    "deployed_at": "2025-01-15T10:36:30Z",
    "last_health_check": "2025-01-15T10:37:00Z"
  }
}
```

**Errors:**
- `400`: Invalid credentials (missing required fields)
- `404`: Analysis not found
- `503`: Fly.io API error

**[ASSUMPTION: Deployment takes 30-90 seconds. Frontend polls /status every 2 seconds until status is 'running' or 'failed'.]**

---

### 4. List Deployments

**GET /api/deployments**

Lists all deployments.

**Query Parameters:**
- `status`: Filter by status (running, stopped, failed)
- `limit`: Max results (default: 50)
- `offset`: Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "status": "running",
      "display_name": "My TickTick Server",
      "sse_url": "https://a3f9x2k1.fly.dev/sse",
      "created_at": "2025-01-15T10:35:00Z",
      "last_health_check": "2025-01-15T11:00:00Z"
    },
    {
      "id": "8d1f7890-8536-51ef-b827-f18gd2g01bf8",
      "status": "stopped",
      "display_name": "GitHub MCP",
      "sse_url": "https://b4g0y3l2.fly.dev/sse",
      "created_at": "2025-01-14T09:20:00Z",
      "stopped_at": "2025-01-15T08:00:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "limit": 50,
    "offset": 0
  }
}
```

---

### 5. Get Deployment Details

**GET /api/deployments/{id}**

Get full details of a specific deployment.

**Response (200 OK):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "running",
    "github_url": "https://github.com/user/mcp-server-repo",
    "display_name": "My TickTick Server",
    "package_name": "@user/mcp-server-ticktick",
    "machine_id": "a3f9x2k1",
    "sse_url": "https://a3f9x2k1.fly.dev/sse",
    "fly_region": "sjc",
    "estimated_monthly_cost": 1.94,
    "created_at": "2025-01-15T10:35:00Z",
    "deployed_at": "2025-01-15T10:36:30Z",
    "last_health_check": "2025-01-15T11:00:00Z",
    "health_status": "healthy",
    "uptime_hours": 168.5
  }
}
```

**Errors:**
- `404`: Deployment not found

---

### 6. Get Deployment Status

**GET /api/deployments/{id}/status**

Lightweight endpoint for polling deployment status during creation.

**Response (200 OK):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "deploying",
    "progress": {
      "step": "installing_packages",
      "message": "Installing npm packages...",
      "percentage": 60
    }
  }
}
```

**Status values:**
- `deploying`: In progress
- `running`: Ready to use
- `stopped`: User stopped
- `unhealthy`: Health checks failing
- `failed`: Deployment error

**[ASSUMPTION: Progress tracking is best-effort. Fly.io doesn't expose granular build steps, so we estimate based on time elapsed.]**

---

### 7. Stop Deployment

**POST /api/deployments/{id}/stop**

Stops a running Fly.io machine (preserves data, can restart later).

**Response (200 OK):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "stopped",
    "stopped_at": "2025-01-15T11:30:00Z"
  }
}
```

**Errors:**
- `404`: Deployment not found
- `400`: Deployment already stopped
- `503`: Fly.io API error

---

### 8. Restart Deployment

**POST /api/deployments/{id}/restart**

Restarts a stopped machine.

**Response (202 Accepted):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "starting",
    "message": "Machine restart initiated"
  }
}
```

Poll `/status` endpoint for completion.

**Errors:**
- `404`: Deployment not found
- `400`: Deployment not in stopped state
- `503`: Fly.io API error

---

### 9. Delete Deployment

**DELETE /api/deployments/{id}**

Permanently deletes a deployment (destroys Fly.io machine and credentials).

**Response (200 OK):**
```json
{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "deleted": true,
    "deleted_at": "2025-01-15T11:45:00Z"
  }
}
```

**Errors:**
- `404`: Deployment not found
- `503`: Fly.io API error (machine might still exist)

**[ASSUMPTION: Deletion is idempotent. If Fly.io machine already gone, we still delete our DB record and return success.]**

---

### 10. Health Check

**GET /api/health**

Check if backend API is operational.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": "connected",
    "claude_api": "reachable",
    "fly_api": "reachable"
  },
  "timestamp": "2025-01-15T12:00:00Z"
}
```

---

## External API Integration

### Claude API (Anthropic)

**Endpoint:** `https://api.anthropic.com/v1/messages`

**Request:**
```python
client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    temperature=0,
    messages=[{
        "role": "user",
        "content": analysis_prompt
    }],
    tools=[{
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5
    }]
)
```

**Rate Limits:**
- 50 requests per minute (tier 1)
- 5,000 requests per day

**Error Handling:**
- 429 (rate limit): Exponential backoff, retry after 5s, 10s, 20s
- 500 (server error): Retry up to 3 times
- 400 (bad request): Return error to user

---

### Fly.io Machines API

**Base URL:** `https://api.machines.dev/v1`

**Authentication:**
```
Authorization: Bearer {FLY_API_TOKEN}
```

**Create Machine:**
```
POST /apps/{app_name}/machines

{
  "name": "mcp-{deployment_id_short}",
  "config": {
    "image": "registry.fly.io/mcp-base:latest",
    "env": {...},
    "guest": {"cpu_kind": "shared", "cpus": 1, "memory_mb": 256},
    "services": [{...}]
  }
}
```

**Get Machine Status:**
```
GET /apps/{app_name}/machines/{machine_id}
```

**Stop Machine:**
```
POST /apps/{app_name}/machines/{machine_id}/stop
```

**Start Machine:**
```
POST /apps/{app_name}/machines/{machine_id}/start
```

**Delete Machine:**
```
DELETE /apps/{app_name}/machines/{machine_id}
```

**Rate Limits:**
- 1,000 requests per hour per app

**Error Handling:**
- 503 (service unavailable): Retry after 30s
- 404 (machine not found): Handle gracefully (might be deleted)
- 400 (invalid config): Return error to user

---

## Webhooks (Future)

**POST /api/webhooks/fly**

Receive events from Fly.io (machine crashed, restarted, etc.)

Not implemented in MVP. Phase 9+.

---

## Rate Limiting

**Per IP address:**
- 100 requests per minute
- 1,000 requests per hour

**Response (429 Too Many Requests):**
```json
{
  "error": {
    "code": "rate_limited",
    "message": "Too many requests. Please try again in 60 seconds.",
    "retry_after": 60
  }
}
```

**[ASSUMPTION: For MVP (single user), rate limiting is lenient. Will tighten for multi-user.]**