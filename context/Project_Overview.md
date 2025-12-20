# Catwalk Live - Project Overview

## Executive Summary

We're building a deployment platform that transforms local-only MCP (Model Context Protocol) servers into cloud-accessible services. Think "Heroku for MCP servers" - users paste a GitHub URL, enter their API keys, and get a URL they can add to Claude to use that MCP server from any device.

## The Problem

### What is MCP?

**MCP (Model Context Protocol)** is Anthropic's open standard for connecting AI assistants to external tools and data sources. It's a universal adapter system that lets Claude interact with services like TickTick, GitHub, Slack, Google Drive, and hundreds of other tools.

**How MCP Works:**
- **MCP Server**: A program that exposes specific capabilities (e.g., "read TickTick tasks", "search GitHub repos")
- **MCP Client**: The AI assistant (Claude) that uses those capabilities  
- **Protocol**: A standardized communication format between them

### The Limitation

MCP was designed for **stdio (standard input/output) communication**, meaning:
```
Claude (on your laptop) ←→ MCP Server (also on your laptop)
                stdio pipes
```

**This creates major limitations:**

1. **Device-locked**: Both Claude and the MCP server must run on the same machine
2. **Desktop-only**: Doesn't work on Claude mobile or web (only desktop app)
3. **Technical barrier**: Users need to install Node.js, configure JSON files, manage processes
4. **Session-bound**: Server dies when laptop closes or app quits
5. **Not shareable**: Can't share access with team members
6. **Maintenance burden**: Each MCP server requires separate local setup

**Real-world impact**: Powerful MCP servers exist for hundreds of services, but 95% of Claude users can't access them because they're not technical enough or don't use Claude Desktop.

## Our Solution

We transform stdio-based MCP servers into **remote Streamable HTTP endpoints** (MCP spec 2025-06-18):
```
Claude (anywhere: desktop/web/mobile)
    ↓ Streamable HTTP (GET/POST)
Catwalk backend (FastAPI on Fly.io)
    ↓ Fly private network (6PN, internal DNS)
MCP machine (mcp-proxy → stdio MCP server)
```

**What this enables:**
- Use MCP servers from Claude mobile/web/desktop
- No local installation required
- Servers run 24/7 in the cloud
- One-time setup, works forever
- Shareable URLs (future: team accounts)

## User Journey

### The Complete Flow:

**Step 1: Discovery**
User finds an MCP server they want to use. Example sources:
- GitHub (e.g., `github.com/modelcontextprotocol/servers`)
- MCP server directory
- Word of mouth

**Step 2: Analysis** 
User pastes GitHub URL into our platform:
```
Input: https://github.com/alexarevalo9/ticktick-mcp-server
```

Platform uses **Claude API with web search** to automatically:
- Read the repository README
- Extract npm package name
- Identify required environment variables
- Determine how to run the server
- Parse API documentation

**[ASSUMPTION: Analysis takes 5-15 seconds. User sees loading state with progress indicator.]**

**Step 3: Review Configuration**
Platform shows what it found:
```
Server: TickTick MCP
Package: @alexarevalo.ai/mcp-server-ticktick
Required credentials:
  - TickTick Client ID
  - TickTick Client Secret  
  - TickTick Access Token
```

**[ASSUMPTION: User can edit this analysis if incorrect. "Edit Configuration" button reveals form fields to manually override detected values.]**

**Step 4: Enter Credentials**
Dynamic form appears based on detected requirements:
- Fields marked as "secret" render as password inputs
- Optional fields show (Optional) label
- Help text explains where to get each credential
- "Where do I find this?" links to relevant documentation

**Step 5: Deploy**
User clicks "Deploy Server"

Backend process (transparent to user):
1. Encrypts credentials with Fernet
2. Stores encrypted data in PostgreSQL
3. Calls Fly.io Machines API
4. Creates isolated container with:
   - mcp-proxy (stdio → Streamable HTTP bridge at `/mcp`)
   - User's chosen MCP server package (`MCP_PACKAGE`)
   - Injected credentials as environment variables
5. Waits for the machine to start and respond on `/status`
6. Returns a backend `connection_url` for Claude to use

**[ASSUMPTION: Deployment takes 30-90 seconds. User sees real-time status: "Creating container..." → "Installing packages..." → "Starting server..." → "Testing connection..." → "Ready!"]**

**Step 6: Get URL**
Platform displays:
```
✅ Your TickTick MCP server is ready!

URL: https://<your-backend-app>.fly.dev/api/mcp/<deployment_id>

[Copy URL] button

Instructions:
1. Open Claude (desktop/mobile/web)
2. Go to Settings → Connectors  
3. Click "Add Custom Connector"
4. Paste URL above
5. Give it a name: "My TickTick"
```

**[ASSUMPTION: Instructions adapt based on user's device. Mobile users see mobile-specific screenshots. Desktop users see desktop screenshots.]**

**Step 7: Use in Claude**
User adds URL to Claude, then:
```
User: "What are my TickTick tasks for today?"

Claude: [connects to https://<your-backend-app>.fly.dev/api/mcp/<deployment_id>]
        [Streamable HTTP → backend → mcp-proxy (/mcp) → MCP server → TickTick API]
        [receives tasks]
        
        "You have 3 tasks today:
         1. Review Q4 budget (due 2pm)
         2. Call dentist 
         3. Finish project proposal"
```

**Step 8: Manage Deployments**
User returns to dashboard to see:
- All active MCP servers
- Status (running/stopped/failed)
- Quick actions (copy URL, stop, restart, delete)
- Cost per deployment

## Concrete Example Flow

### Scenario: Developer wants to use GitHub MCP on mobile

**Current state (without our platform):**
1. Developer can only use GitHub MCP from desktop
2. Must have Node.js installed
3. Must configure `claude_desktop_config.json`
4. Laptop must be running and Claude Desktop app open
5. Can't access from phone while commuting

**With our platform:**
```
9:00 AM - At desk
  User: Visits platform, pastes github.com/some/github-mcp-server
  Platform: Analyzes → "Needs GitHub Personal Access Token"
  User: Enters token from GitHub settings
  Platform: Deploys → Returns URL
  User: Adds URL to Claude Desktop settings

9:05 AM - Tested on desktop
  User (to Claude): "Show my open PRs"
  Claude: "You have 3 open PRs: [lists them]"
  
11:30 AM - On train, using phone
  User (to Claude mobile): "What PRs need my review?"
  Claude: [same MCP server, same access] "2 PRs awaiting review..."
  
3:00 PM - Laptop closed, Claude web
  User (to Claude web): "Close PR #451"
  Claude: [works] "PR #451 closed successfully"
```

**Key difference**: One-time setup, works everywhere, no local infrastructure.

## Success Criteria (MVP)

### Functional Requirements:
- ✅ Accepts any GitHub URL to an MCP server
- ✅ Automatically extracts configuration requirements
- ✅ Deploys to cloud within 60 seconds
- ✅ Returns working Streamable HTTP URL compatible with Claude
- ✅ URL works from Claude desktop, mobile, and web
- ✅ Credentials stored encrypted at rest
- ✅ Can stop/restart/delete deployments
- ✅ Shows deployment status and costs

### Quality Requirements:
- ✅ Analysis completes in <15 seconds
- ✅ Deployment completes in <90 seconds  
- ✅ 99% uptime for deployed servers
- ✅ Zero credential leaks (audit: no plaintext in logs/db)
- ✅ All critical paths have automated tests
- ✅ Clear error messages for all failure modes

### User Experience Requirements:
- ✅ Non-technical users can complete flow
- ✅ Works on first try (no debugging needed)
- ✅ Error messages are actionable
- ✅ Instructions are copy-paste simple

## “Any GitHub link” assumptions (MVP)

For a different MCP server repo URL to deploy cleanly, the analysis + runtime pipeline assumes:
- The repo corresponds to an MCP server that can be run as an npm package via `npx -y <package>`
- Analysis extracts a non-empty package name into `schedule_config.mcp_config.package`
- Required credentials are represented as env vars and can be injected into the machine environment

### Economic Requirements (MVP - single user):
- ✅ Claude API costs: <$0.02 per analysis
- ✅ Fly.io costs: ~$2-5 per deployment per month
- ✅ PostgreSQL: <$5/month total
- ✅ Total MVP burn rate: <$50/month for 10+ deployments

**[ASSUMPTION: For MVP (just you), we don't enforce quotas. When we add multi-user, we'll implement rate limiting and deployment caps.]**

## What We're NOT Building (Yet)

### Deferred to Later Phases:

**Phase 8 - Multi-User (Future):**
- User accounts and authentication
- OAuth login (Google, GitHub)
- Per-user deployment isolation
- Team collaboration features
- Role-based access control

**Phase 9 - Scale-to-Zero (Future):**
- Valkey/Redis session store
- Dynamic machine scaling
- Request-based wake-up
- Cost optimization through auto-shutdown

**Phase 10 - Monetization (Future):**
- Billing and payment processing
- Usage-based pricing
- Subscription tiers
- Cost analytics dashboard

**Phase 11+ - Advanced Features (Future):**
- Custom domains for deployment URLs
- MCP server marketplace
- One-click deploy from marketplace
- Monitoring and alerting
- Logs viewer
- Performance analytics
- Team workspaces

### Explicitly Out of Scope (Never):

**We are NOT building:**
- Our own MCP servers (we deploy existing ones)
- A fork or modification of MCP protocol (we use it as-is)
- Claude itself (we're infrastructure for MCP)
- A replacement for claude.ai (we complement it)
- Local MCP management (focused on cloud)

### The stdio ↔ HTTP Bridge:

**We are NOT building mcp-proxy** - this exists as open source.

What `mcp-proxy` does (we just use it):
- Exposes MCP over Streamable HTTP at `/mcp` (and legacy SSE at `/sse`)
- Spawns MCP server as subprocess
- Translates Streamable HTTP ↔ stdio (and SSE ↔ stdio for legacy clients)
- Handles session management (via MCP session headers)

What we DO build:
- Infrastructure to run mcp-proxy + MCP servers in cloud
- Credential management and injection
- Deployment orchestration
- User interface for the whole flow

## Key Mental Models

### Think of the platform as three layers:

**Layer 1: Intelligence (Analysis Engine)**
- Input: GitHub URL
- Process: LLM reads docs and code
- Output: Structured deployment configuration

**Layer 2: Security (Credential Vault)**  
- Input: User API keys
- Process: Encrypt with Fernet, store in PostgreSQL
- Output: Encrypted blob, decrypted only during deployment

**Layer 3: Orchestration (Container Manager)**
- Input: Config + Encrypted credentials
- Process: Create Fly.io machine, inject env vars, start server
- Output: Backend `connection_url` (Streamable HTTP)

### The Core Loop:
```
Repo URL → LLM Analysis → User Credentials → Deploy Machine → connection_url → Claude
```

### What Actually Runs in the Cloud:
```
┌─────────────────────────────────────┐
│  Fly.io Machine (per deployment)    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ Docker Container               │ │
│  │                                │ │
│  │  [mcp-proxy]                  │ │
│  │       ↓ stdio                 │ │
│  │  [npx @user/mcp-server]       │ │
│  │       ↓ uses                  │ │
│  │  [env vars with user creds]   │ │
│  │                                │ │
│  └────────────────────────────────┘ │
│                                      │
│  Exposed: Port 8080 → mcp-proxy (/mcp, /status) │
└─────────────────────────────────────┘
         ↓
   Internal URL (backend only): http://{machine_id}.vm.{mcp_app}.internal:8080/mcp

Claude-visible URL (stable):
  https://{backend}/api/mcp/{deployment_id}
```

## Why This Matters

### The Bigger Picture:

MCP is incredibly powerful but has a **distribution problem**. Hundreds of high-quality MCP servers exist, but they're inaccessible to most users due to technical barriers.

**Our platform solves distribution:**
- Turns MCP into a cloud service (not just local tool)
- Makes advanced Claude capabilities accessible to non-technical users
- Enables mobile/web use cases that were impossible before
- Creates foundation for MCP marketplace/ecosystem

**Analogy**: We're like Heroku was to web apps, or Netlify to static sites - taking something that requires infrastructure knowledge and making it one-click.

### Market Opportunity:

**Conservative estimate:**
- 1M+ Claude users (actually much higher)
- 5% might want MCP servers (~50k users)
- Average 3 MCP servers per user
- At $5/server/month = $750k MRR potential

**But more importantly**: This enables use cases that don't exist today:
- Claude mobile power users
- Teams sharing MCP server access
- Non-technical users accessing advanced tools
- Always-on automation with MCP

## Risk Mitigation

### Technical Risks:

**Risk: Claude API changes analysis quality**
- Mitigation: Version-specific prompts, fallback to GPT-4
- Monitoring: Track analysis success rate

**Risk: Fly.io API changes**
- Mitigation: Abstract behind interface, easy to swap providers
- Monitoring: Integration tests against live Fly.io API

**Risk: mcp-proxy has bugs**
- Mitigation: Can fork and maintain if needed, it's open source
- Monitoring: Health checks on deployed containers

**Risk: Security breach (credentials leaked)**
- Mitigation: Encryption at rest, audit logging, no plaintext anywhere
- Monitoring: Security scanning, penetration testing

### Product Risks:

**Risk: Users don't understand how to use deployed URLs**
- Mitigation: Crystal clear instructions with screenshots/videos
- Monitoring: Track success rate (deployed → actually used)

**Risk: MCP servers are too diverse to auto-analyze**
- Mitigation: Allow manual configuration override
- Monitoring: Track analysis accuracy, improve prompts

**Risk: Costs too high per user**
- Mitigation: Start with always-on (simple), add scale-to-zero later
- Monitoring: Track Fly.io costs per deployment

### Business Risks:

**Risk: Anthropic changes MCP protocol**
- Mitigation: Track MCP spec closely, participate in community
- Impact: Would affect all MCP tooling, not just us

**Risk: Claude adds built-in remote MCP**
- Mitigation: We'd still provide easier UX + credential management
- Impact: Validate quickly whether users want our abstraction

## Next Steps (MVP Development)

**Week 1-2: Foundation**
- Set up repos (frontend, backend)
- Configure CI/CD
- Deploy "hello world" to Fly.io
- Test mcp-proxy locally

**Week 3-4: Analysis Engine**
- Integrate Claude API
- Build analysis prompt
- Test on 10+ real MCP repos
- Cache implementation

**Week 5-6: Credential Management**
- Database schema + migrations
- Encryption service
- Dynamic form generation
- Security audit

**Week 7-8: Deployment Orchestration**  
- Fly.io API integration
- Docker base image
- Container lifecycle management
- URL generation

**Week 9-10: Frontend**
- Landing page + URL input
- Analysis results display
- Credential form
- Dashboard

**Week 11-12: Polish**
- Error handling
- Instructions/documentation  
- Cost tracking
- User testing

**Week 13: Launch**
- Deploy to production
- Use with your own MCP servers
- Document learnings
- Plan multi-user (Phase 8)

---

**This platform transforms MCP from a desktop-only developer tool into a cloud service accessible to everyone. We're not changing how MCP works - we're making it actually usable.**
