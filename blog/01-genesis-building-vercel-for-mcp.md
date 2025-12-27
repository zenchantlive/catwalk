---
title: "Part 1: Genesis - Building a Vercel for MCP Servers"
series: "Catwalk Live Development Journey"
part: 1
date: 2025-12-11
updated: 2025-12-27
tags: [AI, MCP, architecture, vision, orchestration]
reading_time: "8 min"
commits_covered: "215deaa"
---

## The Spark

December 11, 2025. I'm staring at the Model Context Protocol (MCP) documentation, and I see the problem clearly: **MCP servers are powerful but painful to deploy**.

Want to give Claude access to your TickTick tasks? You need to:
1. Clone the MCP server repository
2. Install dependencies locally
3. Configure environment variables
4. Keep the process running
5. Hope your firewall doesn't block it
6. Restart everything when your laptop reboots

There's a better way. **What if deploying an MCP server was as simple as deploying to Vercel?**

Paste a GitHub URL. Enter your credentials. Get a stable endpoint. Done.

That's the vision behind **Catwalk Live**.

## The Meta-Challenge

But here's where it gets interesting: **I decided to build this entire platform without writing code manually.**

Not because I can't code - but because I wanted to answer a question that's been nagging at me:

> **Can AI coding assistants build production-ready systems if orchestrated properly?**

Not toy projects. Not demos. **Production systems** with:
- Backend APIs
- Database migrations
- Encryption
- Authentication
- Infrastructure as code
- Security hardening
- Comprehensive tests

The answer, spoiler alert: **Yes. But with massive caveats.**

This blog series documents the **how** and the **what actually happened** - including all the failures, pivots, and hard-won lessons.

## Why AI Orchestration?

I'm not a traditional backend engineer. I can't write FastAPI from scratch. I don't remember SQLAlchemy patterns off the top of my head. I've never built a Fly.io deployment pipeline before.

But I **can**:
- ✅ Architect systems
- ✅ Validate AI outputs
- ✅ Debug integration issues
- ✅ Understand security implications
- ✅ Ship working products

This is the skill shift happening in software development: from **"writing code line-by-line"** to **"orchestrating AI systems to build what you've designed."**

I wanted to prove it could work. This project is the proof.

## The Technical Vision

Before the first commit, I needed a clear architectural vision. AI needs **structure** - vague prompts produce vague code.

Here's what I designed:

### Three-Layer Architecture

```
┌─────────────────┐
│  Claude Desktop │  (MCP Client)
│   (User)        │
└────────┬────────┘
         │ HTTPS (Streamable HTTP)
         ↓
┌─────────────────┐
│  Catwalk Live   │  (Our Platform)
│  - Frontend     │  Next.js 15, React 19
│  - Backend API  │  FastAPI, PostgreSQL
└────────┬────────┘
         │ Fly.io Machines API
         ↓
┌─────────────────┐
│  MCP Machine    │  (Isolated Container)
│  - mcp-proxy    │  Streamable HTTP adapter
│  - MCP Server   │  User's server package
└─────────────────┘
```

### Core Workflow

1. **Analysis Phase**: User pastes GitHub repo URL → Claude analyzes the MCP server code → extracts package name, required credentials, available tools
2. **Configuration Phase**: Platform generates dynamic credential form based on analysis → user enters API keys securely
3. **Deployment Phase**: Backend encrypts credentials → spins up Fly.io container → injects environment variables → starts MCP server
4. **Usage Phase**: Claude connects to stable endpoint → calls tools → gets results

### Key Technical Decisions

**Frontend: Next.js 15** (App Router, React 19)
- Why: Modern React, server components, excellent TypeScript support
- Risk: Bleeding edge (App Router still maturing)
- Mitigation: Stick to stable patterns, extensive testing

**Backend: FastAPI** (Python 3.12)
- Why: Modern async Python, automatic OpenAPI docs, excellent type hints
- Risk: I don't know Python well
- Mitigation: AI excels at Python - let it generate, I'll validate

**Database: PostgreSQL 15+** (Fly.io managed)
- Why: Production-ready, JSON support, reliable
- Risk: Fly.io clusters can be fragile
- Mitigation: Document recovery procedures (spoiler: I needed them)

**Infrastructure: Fly.io** (Machines API)
- Why: Firecracker VMs, isolated containers, simple API
- Risk: More complex than serverless
- Mitigation: Reference implementations exist

**Encryption: Fernet** (symmetric encryption)
- Why: Simple, secure, audited
- Risk: Key management critical
- Mitigation: Fly.io secrets, never logged

**MCP Transport: Streamable HTTP** (2025-06-18 spec)
- Why: Latest MCP standard, replaces deprecated SSE
- Risk: Very new spec, limited examples
- Mitigation: Close reading of spec, iterative testing

## The AI Orchestration Strategy

This is where it gets interesting. I wasn't just using **one** AI assistant - I orchestrated **multiple AI systems** with different roles:

### Stage 1: Prompt Refinement
**Tool**: Custom prompt builder

I started with a plain English idea:
> "I want to deploy MCP servers from GitHub to the cloud"

Then refined it into a detailed specification:
> "Build a platform that accepts GitHub repo URLs, uses Claude API to analyze and extract MCP server configuration (package name, env vars, tools/resources/prompts), generates dynamic credential forms, encrypts credentials with Fernet, stores in PostgreSQL, deploys to Fly.io Machines with isolated environments, and implements MCP Streamable HTTP (2025-06-18 spec)."

**Why this matters**: Specific prompts = specific code. Vague prompts = vague results.

### Stage 2: Multi-AI Planning
**Tools**: GPT-4, Claude, Google Gemini

I submitted the refined prompt to all three AIs and compared architectural approaches. Where they agreed = probably good design. Where they disagreed = complexity indicator.

**Example consensus**:
- All recommended FastAPI for Python backend
- All suggested Pydantic for validation
- All recommended async SQLAlchemy

**Example discrepancy**:
- GPT-4 suggested asyncpg for PostgreSQL
- Claude & Gemini suggested psycopg3

I chose **psycopg3** (majority vote). Later proved correct when asyncpg failed with Fly.io's SSL parameters.

### Stage 3: Implementation with Claude Code
**Tool**: Claude Code (Anthropic CLI)

Claude Code became the primary implementation agent. But I didn't just say "build it" - I created **structured context files**:

- `AGENTS.md` - System prompt defining behavior and constraints
- `context/ARCHITECTURE.md` - Technical design decisions
- `context/CURRENT_STATUS.md` - Living document of progress and blockers
- `CLAUDE.md` - Lessons learned, known pitfalls, debugging patterns

These files act as **external memory** for the AI. Without them, AI "forgets" architectural decisions across sessions. With them, consistency is maintained.

### Stage 4: Quality Gates
**Tools**: CodeRabbit, Qodo, Gemini Code Assist, Greptile

Every pull request gets reviewed by automated AI agents:
- **CodeRabbit**: Security vulnerabilities
- **Qodo**: Edge cases, error handling
- **Gemini Code Assist**: Code quality, best practices
- **Greptile**: Integration consistency

Their feedback gets fed back to Claude Code for fixes. It's a **multi-agent validation loop**.

## The First Commit

December 11, 2025, 12:00 PM. Commit `215deaa`: "Initial commit"

```bash
$ git log --reverse --oneline | head -1
215deaa Initial commit
```

The repository structure:
```
catwalk/
├── backend/          # FastAPI application
├── frontend/         # Next.js application
├── context/          # AI context files
├── AGENTS.md         # AI system prompt
└── README.md         # Project overview
```

Nothing fancy. Just the scaffolding. But with **clear structure** from day one.

The first real work began immediately after: Supabase authentication setup. Looking back, this was premature - we'd later rip it out for NextAuth.js. But that's the reality of building: some decisions get revisited.

## What I Didn't Know Yet

On day one, I had no idea:

- That I'd fight PostgreSQL drivers for hours (asyncpg vs psycopg3)
- That Fly.io database clusters would break and need recreation
- That implementing Streamable HTTP would require deep spec reading
- That authentication would become a multi-day debugging nightmare
- That security reviews would find command injection vulnerabilities
- That 12 days later I'd have a working production system

But I knew the vision. I knew the architecture. And I had a plan to **orchestrate AI to build it**.

## The Core Insight

Here's what I learned on day one that shaped everything:

> **AI needs structure to build production systems.**

Not just code structure (classes, modules, functions). **Context structure**:

1. **Clear specifications** (detailed prompts, not vague ideas)
2. **Architectural boundaries** (what goes where, why)
3. **Quality constraints** (type safety, security, validation)
4. **Memory systems** (markdown files that persist across sessions)
5. **Validation loops** (automated review, human verification)

Without these, AI generates code that looks right but breaks in production.

With these, AI becomes a **powerful multiplier** that can build things you couldn't build alone.

## Up Next

The foundation was set. The vision was clear. The AI orchestration strategy was designed.

Next came the real work: building the core architecture, implementing Fernet encryption, designing dynamic forms, and creating the Aurora UI.

That's Part 2.

---

**Key Commits**: `215deaa` (Initial commit), `f6e024a` (Supabase auth)
**Related Files**: `/AGENTS.md`, `/context/Project_Overview.md`
**Lines of Code**: ~200 (scaffolding)

**Next Post**: [Part 2: Foundation - Architecture & Encryption](02-foundation-architecture-encryption.md)
