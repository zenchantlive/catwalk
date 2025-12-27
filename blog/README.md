# Catwalk Live: Development Journey

A blog series documenting the development of **Catwalk Live** - a Vercel-like platform for deploying Remote MCP servers to Fly.io - built entirely through AI orchestration in just 12 days.

## About the Project

**What**: Catwalk Live makes deploying Model Context Protocol (MCP) servers as simple as deploying to Vercel. Paste a GitHub repo URL, enter credentials, and get a production-ready MCP endpoint that Claude Desktop can immediately connect to.

**Stack**:
- Frontend: Next.js 15 (App Router), React 19, TailwindCSS 4, TypeScript 5+
- Backend: FastAPI (Python 3.12), SQLAlchemy (async), PostgreSQL 15+
- Infrastructure: Fly.io (Machines API), Docker
- Development: Claude Code, Cursor, Google Gemini (multi-AI orchestration)

**Timeline**: December 11-23, 2025 (12 days, 86 commits)

**Context**: This project was built without manually writing code - instead using strategic AI orchestration, multi-agent coordination, and rigorous quality control. It demonstrates that AI can build production-ready systems when given proper structure, constraints, and validation.

## Series Overview

This series doesn't just document a technical project - it documents a **methodology**. Each post reveals how AI coding assistants can be orchestrated to build complex, production-ready systems, and where human expertise remains critical.

You'll learn:
- ✅ How to architect systems with AI assistance
- ✅ Prompt engineering patterns that produce production-quality code
- ✅ Multi-AI validation techniques
- ✅ Real debugging challenges (and solutions)
- ✅ Where AI excels and where it struggles
- ✅ Context engineering for multi-session consistency

## Posts

### Part 1: [Genesis - Building a Vercel for MCP Servers](01-genesis-building-vercel-for-mcp.md)
**Dec 11, 2025** • *The spark of an idea and the first commit*

The beginning: Why build this? What problem does it solve? How do you start a complex full-stack project with AI assistance? This post covers the initial vision, tech stack decisions, and the critical choice to build with AI orchestration rather than traditional coding.

**Key Topics**: Project vision, AI orchestration methodology, initial architecture, tech stack rationale

### Part 2: [Foundation - Architecture & Encryption](02-foundation-architecture-encryption.md)
**Dec 11, 2025** • *Building the core architecture and security model*

Diving deep into the foundational architecture: three-layer system design, Fernet encryption for credentials, dynamic form generation from AI analysis, and the Aurora UI design system. This is where the project's architectural DNA was established.

**Key Topics**: System architecture, credential encryption, database schema, dynamic forms, Aurora design system

### Part 3: [The AI Analysis Engine](03-ai-analysis-engine.md)
**Dec 11-12, 2025** • *Teaching Claude to analyze MCP repositories*

How do you get an AI to analyze another developer's GitHub repository and extract deployment configuration? This post reveals the prompt engineering, caching strategy, and lessons learned from integrating Claude API with web search plugins.

**Key Topics**: Prompt engineering, Claude API integration, web search plugins, caching, regex extraction

### Part 4: [First Deployment - Fly.io Adventures](04-first-deployment-flyio.md)
**Dec 12-14, 2025** • *From localhost to production*

The reality of deploying to production: PostgreSQL driver nightmares (asyncpg vs psycopg3), Docker CRLF line ending bugs, missing dependencies, and database cluster failures. This post chronicles the hard-won lessons from getting the backend live on Fly.io.

**Key Topics**: Dockerization, PostgreSQL drivers, Fly.io deployment, database debugging, infrastructure lessons

### Part 5: [Implementing Streamable HTTP & MCP Machines](05-streamable-http-mcp-machines.md)
**Dec 14, 2025** • *The technical heart of the platform*

Building the core MCP functionality: implementing the MCP 2025-06-18 Streamable HTTP spec, integrating Fly Machines API, designing the mcp-proxy architecture, and solving Fly.io private networking challenges. This is where the platform truly came alive.

**Key Topics**: MCP protocol, Streamable HTTP, Fly Machines API, mcp-proxy, private networking, protocol version negotiation

### Part 6: [Building the Registry & Validation Layer](06-registry-validation.md)
**Dec 16-19, 2025** • *Security through validation*

Making the platform secure and reliable: package validation against npm/PyPI registries, credential validation, Glama registry integration, and addressing CodeRabbit's security review feedback. Security isn't an afterthought - it's a continuous practice.

**Key Topics**: Package validation, npm/PyPI registry checks, credential validation, security review, command injection prevention

### Part 7: [The Authentication Nightmare](07-authentication-crisis.md)
**Dec 20-21, 2025** • *When everything breaks at once*

The darkest moment: implementing JWT authentication seemed straightforward until mysterious 401 errors blocked everything. This post documents the debugging saga that revealed the subtle difference between AUTH_SECRET and AUTH_SYNC_SECRET, and why user sync was silently failing.

**Key Topics**: JWT authentication, debugging 401 errors, NextAuth.js integration, user synchronization, auth troubleshooting methodology

### Part 8: [Security Hardening & Production Ready](08-security-hardening-production.md)
**Dec 21-23, 2025** • *From working to production-ready*

The final sprint: comprehensive test suite (51 tests), security hardening from PR reviews, access token rotation, cache improvements, Vercel deployment fixes, and addressing every piece of automated feedback from CodeRabbit, Qodo, and Gemini Code Assist.

**Key Topics**: Integration testing, security hardening, test coverage, automated PR reviews, production deployment, Vercel configuration

### Part 9: [Reflections - AI-Orchestrated Development](09-reflections-ai-orchestration.md)
**Dec 23, 2025 - Present** • *Lessons learned and the future*

Looking back on 12 intense days: What worked? What didn't? Where did AI excel? Where did it fail? How has AI-assisted development changed the role of the engineer? This post synthesizes the entire journey into transferable lessons and future directions.

**Key Topics**: AI orchestration lessons, context engineering, multi-agent validation, prompt refinement, where AI struggles, the future of development

---

## Reading Paths

### Quick Read (Core Story)
For the essential narrative in ~30 minutes:
→ Posts 1, 3, 7, 9

### Technical Deep-Dive (Full Journey)
For engineers who want all the details:
→ All posts in order (1-9)

### Specific Topics

**AI & Prompt Engineering**: Posts 1, 3, 9
**Infrastructure & DevOps**: Posts 4, 5, 8
**Security & Authentication**: Posts 2, 6, 7, 8
**System Architecture**: Posts 2, 5, 6
**MCP Protocol**: Posts 3, 5
**Debugging War Stories**: Posts 4, 7

---

## Context & Documentation

This blog series complements the project's extensive documentation:

- **[AI_ORCHESTRATION.md](../AI_ORCHESTRATION.md)** - Complete AI methodology case study
- **[AGENTS.md](../AGENTS.md)** - AI agent specifications & interaction protocols
- **[context/](../context/)** - Knowledge base used to guide AI development
- **[CURRENT_STATUS.md](../context/CURRENT_STATUS.md)** - Detailed project status and lessons learned
- **[ARCHITECTURE.md](../context/ARCHITECTURE.md)** - Technical architecture deep-dive

---

## Why This Series Matters

This isn't just another "I built X with AI" post. This is a **reproducible methodology** documented in real-time across an actual production system.

**You'll see**:
- The actual prompts that produced production code
- The mistakes AI made (and how to catch them)
- The architectural decisions that AI can't make
- The debugging process when AI-generated code fails
- The quality gates that prevent bad AI code from shipping

**You'll learn**:
- How to structure context for AI consistency across sessions
- Multi-AI validation patterns
- When to trust AI output and when to validate carefully
- How to orchestrate AI agents for complex projects
- The skill shift from "writing code" to "validating systems"

---

## The Result

After 12 days and 86 commits:

- ✅ Full-stack platform deployed to production
- ✅ Working end-to-end MCP tool calling
- ✅ 51 automated tests passing
- ✅ Security hardened through multi-agent review
- ✅ ~3,400 lines of production-quality code
- ✅ Complete methodology documented

**Live**: [GitHub Repository](https://github.com/zenchantlive/catwalk)

---

## Start Reading

**New to this project?** Start with [Part 1: Genesis](01-genesis-building-vercel-for-mcp.md)

**Want the technical heart?** Jump to [Part 5: Streamable HTTP](05-streamable-http-mcp-machines.md)

**Interested in AI methodology?** Read [Part 9: Reflections](09-reflections-ai-orchestration.md)

---

**Questions? Feedback?** Open an issue on [GitHub](https://github.com/zenchantlive/catwalk/issues)

**Want to build your own AI-orchestrated project?** This series is your guide. 🚀
