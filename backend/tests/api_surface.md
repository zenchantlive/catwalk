# API Surface Inventory

## Health
- `GET /api/health`: Health check (Public)

## Authentication
- `POST /api/auth/sync-user`: Sync user from Auth.js (Secret Required: `X-Auth-Secret`)
- `GET /api/auth/me`: Get current user info (JWT Required)

## settings
- `GET /api/settings`: Get user settings status (JWT Required)
- `POST /api/settings`: Update user settings (JWT Required)
- `DELETE /api/settings`: Delete user settings (JWT Required)

## Analysis
- `POST /api/analyze`: Trigger repository analysis (JWT Required)
- `DELETE /api/analyze/cache`: Clear analysis cache (JWT Required)

## Forms
- `GET /api/forms/generate/{service_type}`: Generate dynamic form (Public, optional `repo_url`)
- `GET /api/forms/generate/registry/{registry_id}`: Generate form from Glama registry (Public)

## Deployments
- `POST /api/deployments`: Create a new deployment (JWT Required)
- `GET /api/deployments`: List user's deployments (JWT Required)

## Registry
- `GET /api/registry/search`: Search Glama registry (Public)
- `GET /api/registry/{server_id}`: Get Glama server details (Public)

## MCP (Streamable HTTP - 2025-06-18)
- `GET /api/mcp/{deployment_id}`: MCP SSE stream (Public)
- `POST /api/mcp/{deployment_id}`: MCP JSON-RPC messages (Public)

## MCP (Legacy SSE)
- `GET /api/mcp/{deployment_id}/sse`: Legacy SSE stream (Public)
- `POST /api/mcp/{deployment_id}/messages`: Legacy JSON-RPC messages (Public)
