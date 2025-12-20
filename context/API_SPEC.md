# Catwalk Live - Backend API Spec (MVP)

## Base URL

- **Development**: `http://localhost:8000`
- **Production (current)**: `https://<your-backend-app>.fly.dev`

## Authentication

- **MVP**: No authentication (private / single-user)

## Endpoints

### 1) Analyze Repository

**POST** ` /api/analyze`

Analyzes an MCP server GitHub repo URL using Claude (via OpenRouter) and caches the result.

**Request**
```json
{ "repo_url": "https://github.com/user/mcp-server-repo" }
```

**Response**
```json
{
  "status": "cached | success | failed",
  "data": {
    "raw_analysis": "{...model output...}"
  },
  "error": null
}
```

Notes:
- Cache key is a normalized GitHub URL (lowercase, trimmed trailing `/`).
- The model output is expected to be JSON-like; the frontend form generator extracts:
  - `package` (or `package_name`/`npm_package` fallbacks)
  - `env_vars` (list of env var names or objects with `{name: ...}`)
  - `tools`, `resources`, `prompts`

### 2) Generate Dynamic Credential Form (Custom Repo)

**GET** `/api/forms/generate/custom?repo_url=...`

Returns a form schema derived from cached analysis. The response includes `mcp_config`, which the frontend should persist into `schedule_config.mcp_config` when creating a deployment.

### 3) Create Deployment

**POST** `/api/deployments`

Creates a deployment record, stores encrypted credentials, and (if configured) starts a Fly machine running the MCP server.

**Request**
```json
{
  "name": "My TickTick",
  "schedule_config": {
    "mcp_config": {
      "package": "@alexarevalo.ai/mcp-server-ticktick",
      "tools": [],
      "resources": [],
      "prompts": [],
      "server_info": { "name": "TickTick MCP", "version": "0.1.0", "description": "" }
    }
  },
  "credentials": {
    "env_TICKTICK_CLIENT_ID": "abc",
    "env_TICKTICK_CLIENT_SECRET": "def",
    "env_TICKTICK_ACCESS_TOKEN": "ghi"
  }
}
```

**Response**
```json
{
  "id": "uuid",
  "name": "My TickTick",
  "status": "running | failed | active",
  "schedule_config": { "mcp_config": { "...": "..." } },
  "connection_url": "https://<your-backend-app>.fly.dev/api/mcp/<deployment_id>",
  "error_message": null,
  "created_at": "2025-12-15T00:00:00Z",
  "updated_at": "2025-12-15T00:00:00Z"
}
```

Notes:
- If Fly is enabled (`FLY_API_TOKEN` is set on the backend), the backend creates a machine using:
  - `FLY_MCP_APP_NAME` (app that hosts MCP machines)
  - `FLY_MCP_IMAGE` (shared image that runs `mcp-proxy` and executes `npx -y $MCP_PACKAGE`)
- Credential keys are prefixed with `env_` in storage and are converted back to real env vars on injection.

### 4) List Deployments

**GET** `/api/deployments`

Returns a list of deployments. Each includes a computed `connection_url`.

### 5) MCP Streamable HTTP (Client-Facing)

**GET/POST** `/api/mcp/{deployment_id}`

This is the URL Claude should use. It implements MCP Streamable HTTP (2025-06-18).

Client headers (recommended):
- `MCP-Protocol-Version: 2025-06-18`
- `Accept: application/json` (some upstreams require explicit JSON acceptance)
- `Content-Type: application/json` (POST)
- `Mcp-Session-Id: ...` (optional, session continuity)

Server behavior:
- For deployments with a Fly `machine_id`, the backend forwards Streamable HTTP to the machine via Fly internal DNS:
  - `http://{machine_id}.vm.{FLY_MCP_APP_NAME}.internal:8080/mcp`
- The MCP machine runs `mcp-proxy` which exposes:
  - `GET /status` (health)
  - `GET/POST /mcp` (Streamable HTTP)

### 6) Health Check

**GET** `/api/health`

Returns backend health.

