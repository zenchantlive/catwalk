# MCP Server Container Deployment

This directory contains the Docker image used for all user-deployed MCP servers.

## Architecture

- **One Image, Many Machines**: This single Docker image is used to create all MCP server containers
- **Dynamic Configuration**: Each machine gets different environment variables:
  - `MCP_PACKAGE`: The npm package to run (e.g., `@alexarevalo.ai/mcp-server-ticktick`)
  - User credentials: Injected as environment variables (e.g., `TICKTICK_TOKEN`)

## Build and Deploy the Image

### Step 1: Build and Push to Fly Registry

```bash
cd deploy
fly deploy --build-only --push --app catwalk-live-mcp-servers
```

This will:
1. Build the Docker image
2. Push it to Fly's container registry
3. Output the image name (e.g., `registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX`)

### Step 2: Set the Image in Backend Secrets

Copy the image name from Step 1 and run:

```bash
fly secrets set FLY_MCP_IMAGE="registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX" \
  --app catwalk-live-backend-dev
```

### Step 3: Deploy Backend (if needed)

If you made backend changes:

```bash
cd ../backend
fly deploy --app catwalk-live-backend-dev
```

## How It Works

### When a User Creates a Deployment:

1. **Frontend → Backend**: User submits deployment with repo analysis
2. **Backend analyzes**: Extracts `MCP_PACKAGE` name (e.g., `@alexarevalo.ai/mcp-server-ticktick`)
3. **Backend calls Fly API**: Creates a new machine with:
   ```json
   {
     "image": "registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX",
     "env": {
       "MCP_PACKAGE": "@alexarevalo.ai/mcp-server-ticktick",
       "TICKTICK_TOKEN": "<encrypted-user-credential>"
     }
   }
   ```
4. **Machine starts**: Docker CMD runs `mcp-proxy -- npx -y $MCP_PACKAGE`
5. **MCP server available**: Claude can now connect to the HTTP endpoint

## Testing Locally (Optional)

You can test the image locally before deploying:

```bash
# Build locally
docker build -t mcp-test .

# Run with a test MCP package
docker run -p 8080:8080 \
  -e MCP_PACKAGE="@modelcontextprotocol/server-filesystem" \
  -e FILESYSTEM_ROOT="/tmp" \
  mcp-test

# Test the endpoint
curl http://localhost:8080/
```

## Troubleshooting

### Image Build Fails

```bash
# Check logs
fly logs --app catwalk-live-mcp-servers

# Rebuild without cache
fly deploy --build-only --push --app catwalk-live-mcp-servers --no-cache
```

### Machine Won't Start

Check the machine logs via backend:
```bash
fly ssh console --app catwalk-live-backend-dev
# Inside the container:
curl https://api.machines.dev/v1/apps/catwalk-live-mcp-servers/machines
```

Or check via Fly dashboard: https://fly.io/apps/catwalk-live-mcp-servers

## What's in the Image

- **Base**: Python 3.12-slim
- **Node.js**: v20.x (for npx/npm)
- **mcp-proxy**: Python package that wraps stdio MCP servers as HTTP/SSE
- **Port**: 8080 (Fly.io standard)
- **Dynamic**: MCP package installed on-demand via `npx -y`

## Cost Optimization

Each machine costs ~$0.0000008/second (~$2/month if running 24/7).

**Optimization ideas**:
- Auto-stop machines after inactivity
- Shared machines for multiple deployments (if security allows)
- Spot instances for non-critical deployments
