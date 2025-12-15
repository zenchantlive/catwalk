# MCP Remote Platform - Architecture

## System Overview

The platform consists of four main layers that transform a GitHub URL into a working cloud-based MCP server.

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                               │
│  - Web Browser (Next.js frontend)                            │
│  - Claude (consumes deployed MCP servers)                    │
└──────────────────────────────────────────────────────────────┘
                            ↓ HTTPS
┌──────────────────────────────────────────────────────────────┐
│                    API LAYER                                  │
│  - FastAPI backend                                            │
│  - Request validation                                         │
│  - Business logic orchestration                               │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                              │
│  ┌────────────────┐ ┌────────────────┐ ┌─────────────────┐  │
│  │   Analysis     │ │   Credential   │ │   Deployment    │  │
│  │   Service      │ │   Service      │ │   Service       │  │
│  │                │ │                │ │                 │  │
│  │ - Claude API   │ │ - Encryption   │ │ - Fly.io API    │  │
│  │ - Web search   │ │ - Storage      │ │ - Lifecycle     │  │
│  │ - Caching      │ │ - Validation   │ │ - Health check  │  │
│  └────────────────┘ └────────────────┘ └─────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                 │
│  - PostgreSQL (deployments, credentials, cache)              │
│  - Fly.io (container runtime)                                │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow: Complete Journey

### Flow 1: Analyze Repository

```
User enters GitHub URL
  ↓
Frontend validates URL format
  ↓
POST /api/analyze {repo_url}
  ↓
Backend checks cache (AnalysisCache table)
  ↓ (cache miss)
Claude API called with:
  - Model: claude-haiku-4-5-20251001
  - Tools: [web_search_20250305]
  - Prompt: "Analyze this MCP repo and extract deployment config"
  ↓
Claude fetches repo via web search
Claude parses README, package.json
Claude extracts: package, env_vars, tools, resources, prompts
  ↓
Backend validates response schema
Backend caches result (24h TTL)
  ↓
Returns JSON config to frontend
  ↓
Frontend renders analysis results
User sees required credentials
```

### Flow 2: Deploy MCP Server

```
User enters credentials in dynamic form
  ↓
Frontend validates (required fields, types)
  ↓
POST /api/deployments {name, schedule_config, credentials}
  ↓
Backend retrieves analysis from cache
Backend validates credentials against env_vars schema
  ↓
Create Deployment record (status: 'deploying')
  ↓
Encrypt credentials with Fernet:
  cipher = Fernet(MASTER_KEY)
  encrypted = cipher.encrypt(json.dumps(credentials))
  ↓
Store Credential record with encrypted blob
  ↓
Call Fly.io Machines API:
  POST /v1/apps/{app}/machines
  {
    "config": {
      "image": "{FLY_MCP_IMAGE}",
      "env": {
        "MCP_PACKAGE": "@user/mcp-server",
        ...decrypted_credentials
      },
      "guest": {"cpu_kind": "shared", "cpus": 1, "memory_mb": 256},
      "restart": {"policy": "always"}
    }
  }
  ↓
Fly creates Firecracker VM
Fly pulls Docker image
Container starts: mcp-proxy (Streamable HTTP) exposing:
  - GET /status (health)
  - GET/POST /mcp (Streamable HTTP)
  ↓
Backend stores machine_id and marks deployment 'running'
  ↓
Return deployment info to frontend
  ↓
Frontend shows URL + instructions
User copies URL to Claude settings
```

### Flow 3: Claude Uses MCP Server

```
User asks Claude a question requiring MCP tool
  ↓
Claude connects to backend Streamable HTTP endpoint:
  https://{backend}/api/mcp/{deployment_id}
  ↓
Backend forwards Streamable HTTP to the machine over Fly private networking:
  http://{machine_id}.vm.{mcp_app}.internal:8080/mcp
  ↓
mcp-proxy receives Streamable HTTP request and spawns:
  npx -y $MCP_PACKAGE
  ↓
mcp-proxy translates Streamable HTTP → stdio
MCP server receives request via stdin
  ↓
MCP server uses injected env vars (user credentials)
MCP server calls external API (e.g., TickTick)
  ↓
MCP server returns result via stdout
mcp-proxy translates stdio → Streamable HTTP response (JSON or SSE stream)
  ↓
Backend returns response to Claude
Claude synthesizes answer for user
```

**Important header note**:
- When calling the machine `/mcp` endpoint directly (or proxying it), include `Accept: application/json`.

## Core Components

### Frontend (Next.js)

**Responsibilities:**
- User interface for all flows
- Form validation before API calls
- Real-time status updates (polling)
- URL copying and instruction display

**Key Components:**
- `GitHubUrlInput`: Validates and submits GitHub URL
- `AnalysisResults`: Displays extracted configuration
- `DynamicCredentialForm`: Generates form from analysis schema
- `DeploymentDashboard`: Lists all user deployments
- `DeploymentCard`: Individual deployment with actions

**State Management:**
- React hooks (useState, useEffect)
- No global state library needed for MVP
- Local storage for "in-progress" deployments

**[ASSUMPTION: Frontend polls /api/deployments/{id}/status every 2 seconds during deployment, then every 30 seconds when running]**

### Backend API (FastAPI)

**Responsibilities:**
- Request validation (Pydantic)
- Business logic orchestration
- External API integration
- Database operations

**Key Endpoints:**
```
POST   /api/analyze              # Analyze GitHub repo
GET    /api/analysis/{id}        # Retrieve cached analysis
POST   /api/deployments          # Create new deployment
GET    /api/deployments          # List all deployments
GET    /api/deployments/{id}     # Get deployment details
POST   /api/deployments/{id}/stop    # Stop machine
POST   /api/deployments/{id}/restart # Restart machine
DELETE /api/deployments/{id}     # Delete deployment
GET    /api/health               # Health check
```

**Error Handling:**
- All endpoints return structured errors:
  ```json
  {
    "error": "deployment_failed",
    "message": "User-friendly explanation",
    "details": {"machine_id": "...", "fly_error": "..."},
    "retry_allowed": true
  }
  ```

### Analysis Service

**Responsibilities:**
- Call Claude API with web search
- Parse and validate LLM responses
- Cache results

**Claude API Configuration:**
```python
client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    temperature=0,  # Deterministic for configs
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

**Analysis Prompt Structure:**
```
Analyze this MCP server repository: {repo_url}

Extract deployment information and return ONLY valid JSON:
{
  "package": "exact npm package name (e.g., '@user/mcp-server')",
  "name": "human-friendly name (e.g., 'TickTick MCP')",
  "description": "short description",
  "env_vars": [
    {
      "name": "UPPERCASE_ENV_VAR_NAME",
      "description": "Clear explanation of what this is",
      "required": true/false,
      "secret": true/false (true if API key/password),
      "default": "optional default value or null"
    }
  ],
  "tools": [],
  "resources": [],
  "prompts": [],
  "notes": "any special requirements, setup steps, or warnings"
}

Use web search to find the repository's README and documentation.
Be thorough in identifying ALL required environment variables.
```

**Validation:**
- Schema enforcement via Pydantic
- Security checks: only allow safe `package` values (no shell metacharacters)
- Completeness: `package` + `env_vars` required

**Caching:**
- Key: normalized `repo_url`
- TTL: 1 week
- Invalidation: Manual via query param `?refresh=true`

**[ASSUMPTION: If analysis fails 3 times, return partial result with warning. User can manually edit before deploying.]**

### Credential Service

**Responsibilities:**
- Encrypt credentials before storage
- Decrypt credentials during deployment only
- Never log plaintext credentials

**Encryption Implementation:**
```python
from cryptography.fernet import Fernet

# Master key from environment (32 bytes, base64-encoded)
MASTER_KEY = os.getenv('MASTER_ENCRYPTION_KEY')
cipher = Fernet(MASTER_KEY)

def encrypt_credentials(creds: dict) -> bytes:
    json_str = json.dumps(creds)
    return cipher.encrypt(json_str.encode())

def decrypt_credentials(encrypted: bytes) -> dict:
    decrypted = cipher.decrypt(encrypted)
    return json.loads(decrypted.decode())
```

**Storage:**
- Credentials table has foreign key to Deployment
- Only encrypted_data column stores credentials
- Decryption only happens in memory during deployment
- Encrypted data never returned in API responses

**Validation:**
- Check credentials match analysis schema
- Verify required fields present
- Type validation (string, number, boolean)

### Deployment Service

**Responsibilities:**
- Create/stop/delete Fly.io machines
- Manage machine lifecycle
- Health checking

**Fly.io Machine Specification:**
```json
{
  "name": "mcp-{deployment_id_short}",
  "config": {
    "image": "{FLY_MCP_IMAGE}",
    "env": {
      "MCP_PACKAGE": "@user/mcp-server",
      "USER_CREDENTIAL_1": "decrypted_value",
      "USER_CREDENTIAL_2": "decrypted_value"
    },
    "guest": {
      "cpu_kind": "shared",
      "cpus": 1,
      "memory_mb": 256
    },
    "restart": {
      "policy": "always"
    }
  }
}
```

**Health Checking:**
```
Backend-to-machine checks (private network):
  GET http://{machine_id}.vm.{mcp_app}.internal:8080/status

Expected: 200 OK (JSON)
If connect fails or non-200:
  mark deployment status as 'unhealthy' (future enhancement)
```

**[ASSUMPTION: Machines run always-on for MVP. No scale-to-zero until Phase 9 (Valkey integration).]**

## Data Models

### Deployment Table
```sql
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id TEXT UNIQUE,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'active', 'running',
        'stopped', 'failed'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);
```

### Credential Table
```sql
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL UNIQUE REFERENCES deployments(id) ON DELETE CASCADE,
    encrypted_data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### AnalysisCache Table
```sql
CREATE TABLE analysis_cache (
    id SERIAL PRIMARY KEY,
    repo_url TEXT NOT NULL UNIQUE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Security Architecture

### Defense in Depth:

**Layer 1: Network**
- HTTPS only (TLS 1.3)
- CORS restricted to frontend domain
- Rate limiting on all endpoints (100 req/min per IP)

**Layer 2: Input Validation**
- GitHub URL regex: `^https://github\.com/[\w-]+/[\w-]+$`
- All user inputs validated via Pydantic
- SQL injection prevented by SQLAlchemy (parameterized queries)
- XSS prevented by React (auto-escaping)

**Layer 3: Credential Protection**
- Encrypted at rest (Fernet with 256-bit key)
- Master key stored in Fly.io secrets (not in code/env files)
- Decrypted only in memory during deployment
- Never logged (credential fields filtered from logs)
- Never returned in API responses

**Layer 4: Container Isolation**
- Each deployment in separate Fly.io machine (Firecracker VM)
- No network connectivity between machines
- Resource limits enforced (256MB RAM, 1 CPU)
- Read-only filesystem except /tmp

**Layer 5: Monitoring**
- All API requests logged (without sensitive data)
- Failed auth attempts tracked
- Suspicious patterns alert (future: Sentry integration)

**[ASSUMPTION: For MVP, no authentication. Phase 8 adds OAuth. Until then, platform is private (only you have access).]**

## Cost Tracking

### Per-Deployment Costs:

**Fly.io Machine:**
- shared-cpu-1x: 256MB RAM
- Cost: ~$1.94/month if always-on
- Calculation: $0.0000008/second × 2,592,000 seconds/month

**Displayed to User:**
```
Monthly cost estimate: $1.94
  - Fly.io compute: $1.94
  - Storage (negligible): $0.00
  
Note: This assumes 24/7 uptime. Scale-to-zero coming soon!
```

**Platform Overhead:**
- PostgreSQL: $0 (Fly.io free tier: 3GB)
- Backend API: $1.94/month (single shared-cpu-1x machine)
- Claude API: ~$0.01 per analysis

**Total MVP costs (for you, 10 deployments):**
- Deployments: 10 × $1.94 = $19.40
- Backend: $1.94
- Database: $0
- Claude API: ~$0.10 (10 analyses)
- **Total: ~$21.50/month**

**[ASSUMPTION: We display cost estimate before deployment. User confirms they understand cost before proceeding.]**
