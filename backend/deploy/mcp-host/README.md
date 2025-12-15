# Generic MCP Host Image

This directory contains the Dockerfile for the "Generic MCP Host" image used by Catwalk Live to run user-deployed MCP servers.

## How it Works
1.  The backend spawns a Fly Machine using this image.
2.  It injects the `MCP_PACKAGE` environment variable (e.g., `@modelcontextprotocol/server-filesystem`).
3.  The container starts `mcp-proxy`, which runs `npx -y ${MCP_PACKAGE}`.
4.  `mcp-proxy` exposes the MCP server via SSE on port 8080.

## Setup Instructions

### 1. Authenticate with Fly.io Registry (Optional)
If you are using Fly.io's registry:
```bash
fly auth docker
```
Or use Docker Hub / GHCR.

### 2. Build and Push
Replace `catwalk-live/mcp-host:latest` with your specific registry tag.

```bash
# Example for Fly.io registry (if you have an app named 'catwalk-live-images')
# fly registry usage varies, check fly docs.

# Example for Docker Hub
docker build -t your-username/mcp-host:latest .
docker push your-username/mcp-host:latest
```

### 3. Configure Backend
Update your `.env` (or Fly Secrets) for the backend:

```bash
FLY_MCP_IMAGE=your-username/mcp-host:latest
FLY_API_TOKEN=your-fly-api-token
```
