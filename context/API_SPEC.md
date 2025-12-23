# Catwalk Live - Backend API Spec (MVP)

## Base URL

- **Development**: `http://localhost:8000`
- **Production (current)**: `https://<your-backend-app>.fly.dev`

## Authentication

- **JWT Required**: All authenticated endpoints require a valid JWT in the `Authorization: Bearer <token>` header.
- **Service Secret**: `/api/auth/sync-user` requires `X-Auth-Secret` header.

## Endpoints

### 1) Analyze Repository

**POST** `/api/analyze` (JWT Required)

Analyzes an MCP server GitHub repo URL using Claude (via OpenRouter).

**Request**
```json
{ "repo_url": "https://github.com/user/mcp-server-repo", "force": false }
```

**Response**
```json
{
  "status": "cached | success | failed",
  "data": { ...extracted config... },
  "error": null
}
```

**DELETE** `/api/analyze/cache?repo_url=...` (JWT Required)

Clears analysis cache for a specific repository.

### 2) Generate Dynamic Credential Form

**GET** `/api/forms/generate/custom?repo_url=...` (Public)

**GET** `/api/forms/generate/registry/{registry_id}` (Public)

### 3) Deployments (JWT Required)

**POST** `/api/deployments`
**GET** `/api/deployments`

### 4) Registry (Public)

**GET** `/api/registry/search?q=...`
**GET** `/api/registry/{server_id}`

### 5) Authentication (Internal)

**POST** `/api/auth/sync-user` (Secret: `X-Auth-Secret`)
**GET** `/api/auth/me` (JWT Required)

### 6) MCP (Public)

**GET/POST** `/api/mcp/{deployment_id}` (Streamable HTTP 2025-06-18)
**GET/POST** `/api/mcp/{deployment_id}/sse` (Legacy SSE)

### 7) Health Check

**GET** `/api/health` (Public)

