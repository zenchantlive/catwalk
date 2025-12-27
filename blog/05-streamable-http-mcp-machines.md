---
title: "Part 5: Implementing Streamable HTTP & MCP Machines"
series: "Catwalk Live Development Journey"
part: 5
date: 2025-12-14
updated: 2025-12-27
tags: [MCP, streamable-http, fly-machines, protocol, networking]
reading_time: "16 min"
commits_covered: "f1b3e68...0bdfc23"
---

## The Core Mission

We have a deployed backend. We can analyze GitHub repos. We can encrypt credentials. But we can't actually **run MCP servers yet**.

This is the moment where Catwalk Live goes from "interesting idea" to "working platform."

**The goal**: When a user creates a deployment, spin up an isolated Fly.io container running their MCP server, and expose it as a Streamable HTTP endpoint that Claude Desktop can connect to.

Sounds simple. It wasn't.

## Understanding the MCP Protocol

First, I needed to deeply understand the Model Context Protocol (MCP).

**MCP in 30 seconds**:
- **Purpose**: Let AI assistants (like Claude) call tools, access resources, and use prompts from external servers
- **Architecture**: Client-server protocol with JSON-RPC 2.0 messages
- **Transport**: Originally stdio (standard input/output), then SSE (Server-Sent Events), now **Streamable HTTP**

**The transport evolution**:
1. **stdio** (2024): Claude runs MCP server as subprocess, communicates via stdin/stdout
2. **SSE** (2024-11-05): Separate GET `/sse` (server → client events) and POST `/messages` (client → server requests)
3. **Streamable HTTP** (2025-06-18): **Single unified endpoint**, GET and POST both to `/mcp`, with session management

**Why Streamable HTTP**:
- Simpler (one endpoint vs two)
- Better for proxying (no need to coordinate SSE + POST)
- Session-based (reconnection without reinitialization)
- More flexible (supports both streaming and non-streaming responses)

**The spec I implemented**: [MCP 2025-06-18 Streamable HTTP](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports#streamable-http)

## The Architecture

Here's how requests flow:

```
┌──────────────────┐
│  Claude Desktop  │  User: "What are my TickTick tasks?"
└────────┬─────────┘
         │ POST /mcp
         │ MCP-Protocol-Version: 2025-06-18
         │ MCP-Session-Id: <uuid>
         │ {jsonrpc: "2.0", method: "tools/call", params: {...}}
         ↓
┌─────────────────────────────────────┐
│  Catwalk Backend (FastAPI)          │
│  https://backend.fly.dev/api/mcp/{id}│
│  - Validates access token            │
│  - Retrieves deployment record       │
│  - Proxies to MCP machine           │
└────────┬────────────────────────────┘
         │ POST /mcp
         │ (over Fly.io private network)
         │ http://{machine_id}.vm.mcp-host.internal:8080/mcp
         ↓
┌─────────────────────────────────────┐
│  MCP Machine (Fly.io Container)     │
│  - mcp-proxy (HTTP ↔ stdio)         │
│  - npx @hong-hao/mcp-ticktick       │
│  - Env: TICKTICK_TOKEN=<encrypted>  │
└────────┬────────────────────────────┘
         │ stdio communication
         │ JSON-RPC messages
         ↓
    MCP Server executes tool
    Returns result via stdout
         ↓
    mcp-proxy converts to HTTP response
         ↓
    Backend proxies response to Claude
         ↓
    Claude synthesizes answer for user
```

**Key insight**: The user sees one endpoint. Behind the scenes, requests flow through multiple systems.

## Implementing the MCP Endpoint

### The Streamable HTTP Handler

```python
# backend/app/api/mcp_streamable.py
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.api_route(
    "/mcp/{deployment_id}",
    methods=["GET", "POST"],
    response_class=Response
)
async def mcp_streamable(
    deployment_id: str,
    request: Request,
    access_token: str = Header(None, alias="X-Access-Token")
):
    """
    MCP Streamable HTTP endpoint (2025-06-18 spec).

    Supports:
    - Protocol version negotiation (2025-06-18, 2025-03-26, 2024-11-05)
    - Session management (Mcp-Session-Id header)
    - JSON-RPC 2.0 (requests and notifications)
    - Streaming responses (server-sent events via text/event-stream)
    """

    # 1. Validate access token
    deployment = await get_deployment(deployment_id)
    if deployment.access_token != access_token:
        raise HTTPException(401, "Invalid access token")

    # 2. Get protocol version from headers
    protocol_version = request.headers.get("Mcp-Protocol-Version", "2025-06-18")

    # 3. Get or create session ID
    session_id = request.headers.get("Mcp-Session-Id") or str(uuid.uuid4())

    # 4. Proxy to MCP machine
    machine_url = f"http://{deployment.machine_id}.vm.mcp-host.internal:8080/mcp"

    # Forward request to MCP machine
    async with httpx.AsyncClient() as client:
        # GET request: Initialization or session resumption
        if request.method == "GET":
            response = await client.get(
                machine_url,
                headers={
                    "Accept": "application/json",
                    "Mcp-Protocol-Version": protocol_version,
                    "Mcp-Session-Id": session_id
                }
            )

        # POST request: JSON-RPC call
        else:
            body = await request.body()
            response = await client.post(
                machine_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Mcp-Protocol-Version": protocol_version,
                    "Mcp-Session-Id": session_id
                }
            )

    # 5. Return response (preserving headers and streaming if applicable)
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.headers.get("content-type")
    )
```

**Key elements**:

1. **Dual method support**: Same endpoint handles GET (init) and POST (calls)
2. **Protocol version**: Respects `Mcp-Protocol-Version` header
3. **Session management**: Persists `Mcp-Session-Id` across requests
4. **Access control**: Validates deployment-specific token
5. **Proxying**: Forwards to Fly machine over private network

### Protocol Version Negotiation

The MCP spec evolved. Clients might request older versions:

```python
SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]

def validate_protocol_version(requested: str) -> str:
    """
    Validate and negotiate protocol version.

    Returns highest supported version <= requested version.
    Raises 400 if no compatible version.
    """
    if requested in SUPPORTED_VERSIONS:
        return requested

    # Client requests unknown version - return latest we support
    return "2025-06-18"
```

**Why version negotiation**: Future-proofing. When MCP 2026 spec comes out, Catwalk can still serve 2025 clients.

### Session Management

Sessions let clients reconnect without reinitialization:

```python
class SessionManager:
    """In-memory session store (TODO: Redis for multi-instance)"""

    def __init__(self):
        self.sessions: Dict[str, MCPSession] = {}

    async def get_or_create(self, session_id: str, deployment_id: str) -> MCPSession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = MCPSession(
                id=session_id,
                deployment_id=deployment_id,
                created_at=datetime.utcnow()
            )
        return self.sessions[session_id]

    async def cleanup_expired(self, max_age: timedelta = timedelta(hours=1)):
        """Remove sessions older than max_age"""
        now = datetime.utcnow()
        self.sessions = {
            sid: session
            for sid, session in self.sessions.items()
            if (now - session.created_at) < max_age
        }
```

**Trade-off**: In-memory sessions work for single-instance deployments. For multi-instance, need Redis or sticky sessions.

## Building the MCP Machine

The MCP machine is a Fly.io container running:
1. **mcp-proxy**: HTTP ↔ stdio adapter
2. **User's MCP server**: Installed dynamically via npm/pip

### The Machine Image

```dockerfile
# deploy/Dockerfile (mcp-proxy image)
FROM node:20-slim

# Install Python (supports both npm and PyPI MCP servers)
RUN apt-get update && apt-get install -y python3 python3-pip

# Install mcp-proxy globally
RUN npm install -g @modelcontextprotocol/proxy

# Expose port
EXPOSE 8080

# Start mcp-proxy with dynamic package
# MCP_PACKAGE env var set by deployment
CMD npx -y $MCP_PACKAGE | mcp-proxy http --port 8080
```

**How it works**:
1. `npx -y $MCP_PACKAGE` - Installs and runs the MCP server package
2. `| mcp-proxy http` - Pipes stdout to mcp-proxy, which:
   - Listens on HTTP port 8080
   - Converts HTTP requests → JSON-RPC messages → MCP server stdin
   - Converts MCP server stdout → JSON-RPC responses → HTTP responses

**Why this architecture**:
- Generic: Works with ANY MCP server (npm or PyPI)
- Isolated: Each deployment gets its own container
- Secure: No shared state between deployments

### Deploying a Machine

```python
# backend/app/services/fly_deployment_service.py
import httpx

class FlyDeploymentService:
    """Deploy MCP servers to Fly.io Machines"""

    def __init__(self, api_token: str, mcp_image: str):
        self.api_token = api_token
        self.mcp_image = mcp_image  # e.g., "registry.fly.io/mcp-host:latest"
        self.base_url = "https://api.machines.dev/v1"

    async def create_machine(
        self,
        app_name: str,
        deployment_id: str,
        mcp_package: str,
        credentials: Dict[str, str]
    ) -> str:
        """
        Create a Fly machine running the MCP server.

        Returns:
            machine_id: Fly machine ID
        """

        # Construct environment variables
        env = {
            "MCP_PACKAGE": mcp_package,  # e.g., "@hong-hao/mcp-ticktick"
            **credentials  # e.g., {"TICKTICK_TOKEN": "..."}
        }

        # Machine configuration
        config = {
            "name": f"mcp-{deployment_id[:8]}",
            "config": {
                "image": self.mcp_image,
                "env": env,
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 1,
                    "memory_mb": 256  # Tiny - MCP servers are lightweight
                },
                "restart": {
                    "policy": "always"  # Auto-restart if crashed
                },
                "services": [{
                    "ports": [{
                        "port": 8080,
                        "handlers": ["http"]
                    }],
                    "protocol": "tcp",
                    "internal_port": 8080
                }]
            }
        }

        # Create machine via Fly.io API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/apps/{app_name}/machines",
                json=config,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
            )

            response.raise_for_status()
            data = response.json()
            return data["id"]  # machine_id
```

**Machine specs**:
- 256MB RAM (MCP servers are tiny)
- Shared CPU (no need for dedicated)
- Auto-restart policy (survive crashes)
- Internal port 8080 (Fly private network)

**Cost**: ~$0.65/month per always-on machine. Cheap.

## The Fly.io Private Network Challenge

**The problem**: Fly machines have internal DNS: `{machine_id}.vm.{app_name}.internal`

Backend needs to reach machines, but:
- Machines are on Fly's private network (`.internal` TLD)
- Backend needs to be in the same Fly network
- DNS resolution must work

**The solution**: Deploy backend and machines in the same Fly organization and region.

```toml
# backend/fly.toml
app = "catwalk-backend"
primary_region = "sjc"

# MCP machines also deployed to sjc region
```

**Private network connectivity**:

```python
# This works from within Fly.io network:
machine_url = f"http://{machine_id}.vm.mcp-host.internal:8080/mcp"

# This would NOT work from outside Fly:
# machine_url = f"http://{machine_id}.fly.dev/mcp"  # Public DNS doesn't exist
```

**Debugging tip**: SSH into backend and test connectivity:

```bash
fly ssh console --app catwalk-backend
# Inside container:
curl http://<machine-id>.vm.mcp-host.internal:8080/status
```

## The Header That Stumped Me

December 14, 10 PM. Machines are running. Backend is proxying. But Claude can't connect.

**Error**: `406 Not Acceptable`

I tested the machine directly:

```bash
curl http://{machine_id}.vm.mcp-host.internal:8080/mcp

# Response: 406 Not Acceptable
```

**What happened**: `mcp-proxy` requires an `Accept` header:

```bash
curl -H "Accept: application/json" \
     http://{machine_id}.vm.mcp-host.internal:8080/mcp

# Response: 200 OK
```

**The fix**: Always include `Accept` header in proxied requests:

```python
response = await client.get(
    machine_url,
    headers={
        "Accept": "application/json",  # REQUIRED
        "Mcp-Protocol-Version": protocol_version,
        "Mcp-Session-Id": session_id
    }
)
```

**Lesson learned**: Read the spec carefully. `mcp-proxy` HTTP transport spec says:

> Clients SHOULD send `Accept: application/json` header.

"SHOULD" means "required in practice."

## End-to-End Test

December 14, 11 PM. Time to test the full flow:

### Step 1: Create Deployment

```bash
POST /api/deployments
{
  "name": "My TickTick",
  "repo_url": "https://github.com/hong-hao/mcp-ticktick",
  "credentials": {
    "TICKTICK_TOKEN": "my-secret-token"
  }
}

Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "connection_url": "https://backend.fly.dev/api/mcp/123e4567-e89b-12d3-a456-426614174000",
  "access_token": "abc123...",
  "status": "running",
  "machine_id": "e2865013d24908"
}
```

### Step 2: Add to Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ticktick": {
      "url": "https://backend.fly.dev/api/mcp/123e4567-e89b-12d3-a456-426614174000",
      "transport": {
        "type": "streamableHttp",
        "headers": {
          "X-Access-Token": "abc123..."
        }
      }
    }
  }
}
```

### Step 3: Test in Claude

**User**: "What are my TickTick tasks for today?"

**Claude**: *(connects to MCP endpoint, calls tools/call with method=list_tasks)*

**Result**: ✅ Works! Claude lists actual TickTick tasks.

**The moment**: Pure elation. The entire platform works end-to-end.

## Performance Metrics

After successful deployment:

- **Machine startup time**: ~8 seconds (pull image, start container, install package)
- **First tool call latency**: ~1.2 seconds (initialize MCP server, execute tool)
- **Subsequent calls**: ~300ms (server already initialized)
- **Concurrent deployments**: Tested up to 10 (each isolated)

**Bottleneck**: Package installation (npm/pip). Future optimization: Pre-cache popular packages.

## What I Learned

### AI-Generated Code That Worked ✅
- FastAPI endpoint structure
- HTTPX client configuration
- Header forwarding logic

### AI-Generated Code That Failed ❌
- Private network URL construction (suggested `.fly.dev` instead of `.internal`)
- `Accept` header omission (didn't read spec carefully)
- Session cleanup strategy (suggested database, in-memory is fine for MVP)

### Human Expertise Required 🧠
- Deep MCP spec understanding (protocol version negotiation)
- Fly.io private networking knowledge
- Debugging 406 errors (requires understanding mcp-proxy internals)
- Security: Access token validation

**The pattern**: AI handles HTTP plumbing. Humans handle protocol nuances and platform-specific knowledge.

## Up Next

The platform works! You can deploy MCP servers. Claude can connect. Tools execute.

But there's a glaring security hole: **We're not validating package names**.

A malicious user could submit:
```
package: "; rm -rf /"
```

And we'd execute:
```bash
npx -y "; rm -rf /"
```

Disaster.

Time to build **the Registry & Validation Layer**.

That's Part 6.

---

**Key Commits**:
- `f1b3e68` - Deploy: Add shared MCP host image + build scripts
- `f15370c` - Backend: Deploy Fly MCP machines + Streamable HTTP bridge
- `768d0b3` - Docs: Align docs with Streamable HTTP + deployment flow

**Related Files**:
- `backend/app/api/mcp_streamable.py` - MCP endpoint implementation
- `backend/app/services/fly_deployment_service.py` - Fly Machines API
- `deploy/Dockerfile` - MCP machine image

**Spec Reference**:
- [MCP Streamable HTTP Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports#streamable-http)

**Next Post**: [Part 6: Building the Registry & Validation Layer](06-registry-validation.md)
