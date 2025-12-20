# Catwalk Live

**A Vercel-like platform for deploying MCP servers to Fly.io, built entirely through AI orchestration.**

> 🤖 **This project was built using a multi-stage AI development pipeline** (Claude Code, Cursor, Gemini Code Assist) **without manually writing code.** It demonstrates strategic prompt engineering, multi-agent coordination, and quality control of AI-generated systems.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tech Stack](https://img.shields.io/badge/Stack-Next.js%20%7C%20FastAPI%20%7C%20PostgreSQL-blue)]()
[![Built with AI](https://img.shields.io/badge/Built%20with-AI%20Orchestration-purple)]()

---

## What It Does

Catwalk Live makes deploying [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers as simple as deploying to Vercel:

1. **Paste a GitHub repo URL** → AI analyzes the MCP server automatically
2. **Enter credentials** → Securely encrypted with Fernet
3. **Click deploy** → Spins up isolated Fly.io container
4. **Get endpoint** → Connect Claude Desktop immediately

**Live Demo**: [Video Walkthrough](link-to-video) (coming soon)

---

## Features

- 🔍 **Auto-Analysis**: Paste any GitHub MCP server repo → AI extracts config (tools, resources, prompts, env vars)
- 🔐 **Secure Credentials**: Fernet encryption for API keys/tokens stored in PostgreSQL
- 🚀 **One-Click Deploy**: Automated deployment to Fly.io with isolated containers
- 🌐 **Streamable HTTP**: Implements MCP 2025-06-18 spec (latest standard)
- 📊 **Real-Time Status**: Track deployment health and logs
- ✅ **Package Validation**: Checks npm/PyPI registries before deployment
- 🛡️ **Input Validation**: Prevents SQL injection, XSS, command injection

---

## 🤖 Built with AI Orchestration

**This project is a case study in AI-assisted development.** Here's the workflow:

### Development Pipeline

```
Prompt Refinement (Plain English → Detailed Spec)
         ↓
Multi-AI Planning (Claude + GPT-4 + Gemini)
         ↓
Implementation (Claude Code + Cursor)
         ↓
Quality Gates (CodeRabbit, Qodo, Gemini Code Assist, Greptile)
         ↓
Iteration (Feedback → AI → Fixes)
         ↓
Production Deployment (Fly.io)
```

**Key insight**: AI needs **structure** to build production systems. Context files (`AGENTS.md`, `context/*.md`) act as "external memory" that persists across AI sessions.

### Meta-Documentation (The Real Value)

This repo contains not just code, but a **reproducible methodology** for AI-orchestrated development:

- **[`AGENTS.md`](AGENTS.md)** - AI agent specifications & interaction protocols
- **[`context/`](context/)** - Knowledge base for guiding AI development
- **[`CLAUDE.md`](CLAUDE.md)** - Lessons learned, deployment pitfalls, debugging patterns
- **[`AI_ORCHESTRATION.md`](AI_ORCHESTRATION.md)** - **Full methodology case study** (read this!)

**See [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) for the complete story** - how to build production systems with AI, what works, what doesn't, and lessons learned.

---

## Tech Stack

**Frontend**: Next.js 15 (App Router), React 19, TailwindCSS 4, TypeScript 5+
**Backend**: FastAPI (Python 3.12), SQLAlchemy (async), PostgreSQL 15+
**Infrastructure**: Fly.io (Machines API), Docker
**MCP Transport**: Streamable HTTP (2025-06-18 spec)
**Security**: Fernet encryption, Pydantic validation, environment isolation

---

## Quick Start

See [SETUP.md](SETUP.md) for detailed instructions.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs at: **http://localhost:8000**

### Frontend

```bash
cd frontend
bun install
cp .env.local.example .env.local
bun run dev
```

Frontend runs at: **http://localhost:3000**

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment to Fly.io.

**TLDR**:
```bash
# Create Fly apps
fly apps create <your-backend-app>
fly postgres create --name <your-database-app>
fly postgres attach <your-database-app> --app <your-backend-app>

# Set secrets
fly secrets set ENCRYPTION_KEY="..." OPENROUTER_API_KEY="..." --app <your-backend-app>

# Deploy
cd backend && fly deploy --app <your-backend-app>
```

**Current deployment** (as of December 2025):
Backend: `https://<your-backend-app>.fly.dev` (replace with your deployment)

---

## How It Works

### 1. User Analyzes GitHub Repo

```
User → https://github.com/user/mcp-server
     ↓
Claude analyzes package.json or pyproject.toml
     ↓
Extracts: package name, env vars, tools, resources
```

### 2. Dynamic Form Generation

Based on extracted env vars, frontend generates a credential input form:

```typescript
{
  "env_API_KEY": { type: "password", required: true },
  "env_BASE_URL": { type: "url", required: false }
}
```

### 3. Secure Storage

Credentials encrypted with Fernet before storage:

```python
cipher = Fernet(settings.ENCRYPTION_KEY)
encrypted = cipher.encrypt(json.dumps(credentials).encode())
# Stored in PostgreSQL, decrypted only at deployment time
```

### 4. Deployment to Fly.io

Creates isolated Fly Machine running:
- **mcp-proxy** (Streamable HTTP adapter)
- **User's MCP server package** (npm or PyPI)
- **Injected credentials** as environment variables

### 5. Claude Connects

Stable endpoint: `https://<your-backend-app>.fly.dev/api/mcp/{deployment_id}`

Claude Desktop → Backend → Fly Machine → MCP Server → Tool Execution

---

## Architecture

```
┌─────────────────┐
│  Claude Desktop │
│   (MCP Client)  │
└────────┬────────┘
         │ Streamable HTTP
         │ (2025-06-18)
         ↓
┌─────────────────┐
│   Catwalk Live  │
│    (Backend)    │
│  FastAPI + PG   │
└────────┬────────┘
         │ Fly Private Network
         ↓
┌─────────────────┐
│  MCP Machine    │
│  mcp-proxy +    │
│  MCP Server     │
└─────────────────┘
```

See [context/ARCHITECTURE.md](context/ARCHITECTURE.md) for detailed system design.

---

## Contributing

**We welcome contributions - especially AI-assisted ones!**

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to contribute using AI tools (Claude Code, Cursor, ChatGPT, etc.)
- Quality standards and automated review process
- Expectations for contributors

**TL;DR**:
1. Fork the repo
2. Use AI assistants with `AGENTS.md` as context
3. Submit PR (automated agents will review)
4. Iterate with AI based on feedback
5. Merge!

---

## About This Project

**I didn't write this code manually—I orchestrated AI systems to build it.**

This demonstrates:
- ✅ Strategic prompt engineering for complex systems
- ✅ Multi-agent coordination across backend, frontend, infrastructure
- ✅ Quality control and validation of AI-generated code
- ✅ Shipping production-ready AI-assisted projects

**I'm not a traditional backend engineer**—I'm an **AI Orchestrator** and **Technical Product Builder**. I can't write FastAPI from scratch, but I can architect systems, validate AI outputs, catch integration bugs, and ship working products.

**If you're hiring for**:
- AI Engineering Manager roles
- Technical Product Management (AI tools)
- AI-Assisted Development positions
- Developer Experience (AI tools)

**Let's talk!** Email: zenchant@users.noreply.github.com

---

## Project Status

**Current Phase**: Phase 1 Complete (Validation) + Phase 6 Working (Streamable HTTP)

**What Works**:
- ✅ Full backend deployed on Fly.io
- ✅ GitHub repo analysis with AI
- ✅ Package validation (npm + PyPI)
- ✅ Credential validation and encryption
- ✅ Deployment to Fly Machines
- ✅ End-to-end MCP tool calling

**What's Next**:
- Health monitoring loop
- Rich deployment progress reporting
- Frontend deployment (currently local only)

See [context/CURRENT_STATUS.md](context/CURRENT_STATUS.md) for detailed status.

---

## Resources

**Documentation**:
- [SETUP.md](SETUP.md) - Local development guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment to Fly.io
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute (with AI!)
- [SECURITY.md](SECURITY.md) - Security policy and best practices
- [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) - **Full AI methodology case study**

**MCP Resources**:
- [Model Context Protocol Spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Fly.io Machines API](https://fly.io/docs/machines/api/)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

Copyright (c) 2024-2025 Jordan Hindo

---

## Acknowledgments

Built with:
- **Claude Code** (Anthropic) - Primary AI coding assistant
- **Cursor** - Refactoring and iterative development
- **Google Gemini** - Planning and cross-validation
- **CodeRabbit, Qodo, Gemini Code Assist, Greptile** - Automated PR review

Inspired by:
- Vercel's developer experience
- The MCP ecosystem
- The future of AI-assisted development

---

**⭐ If this project helped you understand AI orchestration, please star the repo!**

**🚀 Ready to build your own AI-orchestrated project?** Read [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) and start experimenting!
