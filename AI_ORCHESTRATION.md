# AI-Orchestrated Development: Building Catwalk Live

**A case study in building production systems without writing code manually.**

---

## The Challenge

Can you build a complex, production-ready platform (backend, frontend, database, deployment) using only AI coding assistants—without writing code yourself?

**Answer: Yes.** This document explains how.

---

## The Workflow

### Stage 1: Prompt Refinement

**Tool**: Custom AI prompt builder (system prompt that expands plain English)

**Input**: Basic idea in plain English
**Output**: Fully-featured development prompt with requirements, constraints, and success criteria

**Example**:

```
Plain English Input:
"I want to deploy MCP servers from GitHub to the cloud"

Refined Prompt Output:
"Build a platform that:
1. Accepts GitHub repo URLs for MCP servers
2. Uses Claude API to analyze repos and extract:
   - MCP server package name (npm or PyPI)
   - Required environment variables (credential schema)
   - Available tools, resources, and prompts
3. Generates dynamic credential forms based on extracted requirements
4. Encrypts credentials with Fernet symmetric encryption
5. Stores deployments in PostgreSQL with encrypted credentials
6. Deploys to Fly.io Machines with isolated environments
7. Implements MCP Streamable HTTP (2025-06-18 spec)
8. Exposes stable endpoint URLs for Claude Desktop

Tech stack:
- Frontend: Next.js 15, React 19, TailwindCSS 4, TypeScript 5+
- Backend: FastAPI (Python 3.12), SQLAlchemy (async), PostgreSQL
- Infrastructure: Fly.io Machines API, Docker
- Security: Fernet encryption, environment isolation

Success criteria:
- Type-safe across the stack (no 'any' types)
- Passes all linters (ruff, eslint) with zero warnings
- Production deployed on Fly.io
- End-to-end MCP tool calling works
"
```

**Why this works**: AI assistants need specificity. Vague prompts = vague code. Detailed prompts with constraints = production-quality code.

---

### Stage 2: Multi-AI Planning

**Tools**: OpenAI GPT-4, Google Gemini, Claude

**Strategy**: Cross-validate architecture across different AI models

**Process**:

1. Submit the refined prompt to all three AIs
2. Compare architectural approaches
3. Identify **consensus patterns** (good design indicators)
4. Flag **discrepancies** (complexity / edge case indicators)
5. Finalize MVP structure based on majority consensus

**Why this works**: Different AI training data = different blind spots. Cross-validation catches issues early.

**Example finding**:
- GPT-4 suggested asyncpg for PostgreSQL
- Claude suggested psycopg3
- Gemini suggested psycopg3

**Result**: Chose psycopg3 (majority + better SSL support for Fly.io). Later proved correct when asyncpg failed with Fly.io's `sslmode` parameters.

---

### Stage 3: Structured Planning (Claude Antigravity IDE)

**Tool**: Google Gemini in "Plan Mode"

**Output**: Complete initialization plan including:
- Repository structure
- Tech stack rationale
- Database schema
- API endpoint design
- Security considerations
- Deployment strategy

**Workflow**:
1. Gemini generates comprehensive plan
2. Export plan as markdown
3. Save to `context/` directory for future AI sessions

**Why this works**: Having a written plan prevents scope creep and keeps AI sessions focused.

---

### Stage 4: Implementation (Claude Code)

**Tool**: Claude Code (Anthropic CLI)

**Role**: Code generation + critique

**Process**:

1. Claude Code reads the Gemini-generated plan
2. **Critiques the plan** (identifies gaps, edge cases, security issues)
3. Begins implementation with validation at each step
4. **Creates memory structure** (markdown files) for context persistence

**Memory Files Created**:

- **`AGENTS.md`** - System prompt and interaction protocols (tells AI how to behave)
- **`context/CURRENT_STATUS.md`** - Current project state, blockers, next steps
- **`context/ARCHITECTURE.md`** - Technical design decisions with rationale
- **`CLAUDE.md`** - Lessons learned, deployment pitfalls, debugging patterns

**Why this works**: AI has limited context windows. Structured markdown files act as "external memory" that persists across sessions.

**Example**: After 3 sessions debugging Fly.io PostgreSQL, `CLAUDE.md` contains:
> "CRITICAL: Use psycopg3, not asyncpg. Fly.io URLs have `sslmode` parameter that asyncpg doesn't support. URL converter in `app/core/config.py` transforms `postgres://` → `postgresql+psycopg://`"

This prevents the next AI session from repeating the same mistake.

---

### Stage 5: Quality Control (GitHub Agent Pipeline)

**Agents**: CodeRabbit, Qodo, Gemini Code Assist, Greptile

**PR Review Process**:

1. AI commits phase completion → creates Pull Request
2. **GitHub agents automatically review**:
   - **CodeRabbit**: Security vulnerabilities (SQL injection, XSS, exposed secrets)
   - **Qodo**: Edge cases, error handling, input validation
   - **Gemini Code Assist**: Code quality, best practices, type safety
   - **Greptile**: Integration consistency, breaking changes
3. Agents post review comments on PR
4. **Comments fed back to implementing AI** (copy-paste into Claude Code)
5. AI addresses all comments iteratively
6. PR merged → next phase begins

**Why this works**: Creates a "guardrail system" where AI-generated code must pass multiple automated quality gates before merging.

**Real example from this project**:

```
CodeRabbit comment:
"The package name from user input is not validated before passing to
`npx -y $MCP_PACKAGE`. This allows command injection. Recommend
validating package names against npm/PyPI registries first."

Fed to Claude Code:
"CodeRabbit flagged command injection risk in package handling.
Please implement package validation against npm and PyPI registries
before allowing deployment."

Result:
Claude implemented `PackageValidatorService` with registry checks,
added tests, and updated the deployment flow. Security issue resolved.
```

---

### Stage 6: Iteration & Handoffs

**Challenge**: AI context windows are limited (even 200K tokens)

**Solution**: Structured knowledge base in `context/` directory

**Handoff Protocol**:

1. **End of session**: AI updates `CURRENT_STATUS.md` with:
   - What was accomplished
   - What's blocked / needs attention
   - Next steps

2. **Start of session**: AI reads:
   - `CURRENT_STATUS.md` (where we are)
   - `AGENTS.md` (how to behave)
   - `CLAUDE.md` (known pitfalls)
   - Relevant `context/*.md` files (architecture, design)

3. **During session**: AI references context files when making decisions

**Result**: Smooth multi-session development without "AI amnesia"

**Before context files**:
- AI would forget architectural decisions across sessions
- Repeated the same mistakes (e.g., trying asyncpg again after it failed)
- Lost context on why certain patterns were chosen

**After context files**:
- AI maintains consistency across 20+ sessions
- Respects previous design decisions
- Builds on prior work instead of redoing it

---

## What This Demonstrates

### Skills Proven

1. **System Architecture**: Designed 3-layer platform (frontend, backend, infrastructure)
2. **Strategic Thinking**: Chose Fly.io Machines for isolation, Fernet for encryption, Streamable HTTP over deprecated SSE
3. **Quality Control**: Caught AI failures before production (async bugs, PostgreSQL driver issues, validation gaps)
4. **Integration Debugging**: Fixed Streamable HTTP forwarding, SSL parameter mismatches, credential injection
5. **Production Deployment**: Shipped to Fly.io with health checks, database migrations, auto-scaling

### Where AI Excelled

- ✅ **Boilerplate**: FastAPI routes, React components, database models
- ✅ **API client generation**: Type-safe fetch wrappers from OpenAPI schemas
- ✅ **Database migrations**: Alembic migrations from model changes
- ✅ **TypeScript types**: Generated from Pydantic schemas
- ✅ **Documentation structure**: Markdown files, README templates

### Where AI Struggled (Required Human Intervention)

- ❌ **Fly.io PostgreSQL driver**: Tried asyncpg first (doesn't support `sslmode`), had to switch to psycopg3
- ❌ **Async edge cases**: Race conditions in registry service (concurrent requests to npm/PyPI)
- ❌ **Streamable HTTP spec nuances**: Session management (`Mcp-Session-Id` header), protocol version negotiation
- ❌ **Infrastructure debugging**: Fly.io private networking (`.internal` DNS), SSL certificate issues
- ❌ **Security assumptions**: Didn't validate package names, allowing potential command injection

**The pattern**: AI is great at "known patterns" (CRUD, API clients, forms) but struggles with:
- Infrastructure-specific quirks (Fly.io, cloud providers)
- Security edge cases (validation, injection attacks)
- Async concurrency bugs
- Newly released specs (Streamable HTTP 2025-06-18 was very new)

---

## Lessons Learned

### 1. Context Engineering is 80% of Success

Without `AGENTS.md` and `context/` files, AI "forgets" architectural decisions across sessions.

**Bad**: Each session starts fresh, AI makes different choices, codebase becomes inconsistent.

**Good**: Structured knowledge base ensures AI maintains architectural vision across sessions.

**Analogy**: Think of context files as a "codebase constitution" that AI must respect.

### 2. Multi-Agent Validation Catches Bugs AI Alone Misses

Different AI models have different strengths:

| Issue | Caught By | Example |
|-------|-----------|---------|
| Security vulnerabilities | CodeRabbit | Package injection, exposed secrets |
| Missing error handling | Qodo | Edge cases, input validation |
| Package validation gaps | Gemini Code Assist | npm/PyPI registry checks |
| Integration consistency | Greptile | Breaking changes, API mismatches |

**Result**: Using 4 AI review agents prevented 15+ security/quality issues from reaching production.

### 3. Prompt Refinement is Non-Negotiable

**Bad prompt**: "Build me an API for deploying MCP servers"

**Result**: AI generates basic CRUD, no security, no validation, generic patterns.

**Good prompt**: "Build a FastAPI backend with async SQLAlchemy, PostgreSQL + psycopg3, Fernet encryption for credentials, health checks at `/api/health`, Pydantic validation for all inputs, and Streamable HTTP transport per MCP spec 2025-06-18."

**Result**: AI generates production-ready code with proper patterns.

**Time spent refining prompt**: 30 minutes
**Time saved debugging bad code from vague prompt**: 10+ hours

### 4. Git History is Your Debugging Friend

When AI makes mistakes:

```bash
git diff               # See what changed
git log --oneline      # Track commits
git checkout HEAD~1    # Rollback if needed
```

**Structured commits** (one feature per commit) make debugging AI-generated code dramatically easier.

**Good commit**: "Add package validation for npm and PyPI registries"

**Bad commit**: "Update backend" (contains 10 different changes, impossible to debug)

### 5. AI Can't Replace System Thinking

You still need to:
- ✅ Choose the right architecture (microservices vs monolith, REST vs GraphQL)
- ✅ Understand security implications (encryption, auth, validation)
- ✅ Debug integration issues (Fly.io networking, SSL, DNS)
- ✅ Validate AI assumptions (is this package name safe to execute?)
- ✅ Make product decisions (features, UX, trade-offs)

**The Role Shift**: From "writing code" → "validating systems"

You become a **systems architect + quality engineer** rather than a line-by-line coder.

---

## Reproducible Methodology

Want to build your own AI-orchestrated project? Here's the template:

### 1. Start with .md files, not .py files

Before writing any code:

- Create **`AGENTS.md`** - AI interaction spec (system prompt)
- Create **`context/ARCHITECTURE.md`** - Design decisions
- Create **`context/CURRENT_STATUS.md`** - Living status doc

These files are your "source of truth" that keeps AI aligned across sessions.

### 2. Use Structured Prompts

**Bad**: "Build me a deployment platform"

**Good**:
```
Build a platform for deploying MCP servers to Fly.io:

Requirements:
1. User provides GitHub repo URL
2. Backend analyzes repo with Claude API
3. Extract package name, env vars, tools/resources/prompts
4. Store encrypted credentials (Fernet)
5. Deploy to Fly.io Machines with isolated networking

Tech Stack:
- Frontend: Next.js 15, React 19, TailwindCSS 4, TypeScript 5+
- Backend: FastAPI, PostgreSQL + psycopg3, SQLAlchemy (async)
- Infrastructure: Fly.io Machines API

Security:
- Input validation (Pydantic)
- Credential encryption (Fernet)
- No SQL injection (use ORM)
- Package name validation (npm/PyPI registries)

Success Criteria:
- Passes `ruff check` with zero warnings
- Passes `bun run typecheck` with no errors
- End-to-end MCP tool calling works
```

### 3. Set Up Automated Quality Gates

- Add **CodeRabbit** to your GitHub repo (free for open source)
- Configure **pre-commit hooks**: `ruff`, `eslint`, `prettier`
- Use **AI PR review agents** (Qodo, Gemini Code Assist, Greptile)

### 4. Maintain Context Across Sessions

**End of session checklist**:
- [ ] Update `CURRENT_STATUS.md` (what was done, what's next)
- [ ] Update `CLAUDE.md` if you learned a pitfall
- [ ] Commit changes with clear message

**Start of session checklist**:
- [ ] Read `CURRENT_STATUS.md`
- [ ] Read `AGENTS.md` (refresh AI on rules)
- [ ] Review `CLAUDE.md` (avoid known pitfalls)

**Never assume AI "remembers"** - make it explicit in markdown.

### 5. Validate AI Outputs Religiously

**Before merging any AI-generated code**:

```bash
# Backend
pytest                 # Run all tests
ruff check .           # Lint (must pass with zero warnings)
ruff format .          # Auto-format

# Frontend
bun run typecheck      # TypeScript checks
bun run lint           # ESLint
bun run test           # Vitest tests
```

**Deploy to staging before production** (if you have one).

**Review diffs manually** - Don't blindly trust AI, but don't rewrite everything either. Review with an eye for logic errors, security issues, and architectural consistency.

---

## Results

### Quantitative

- **Built in**: ~20 AI sessions over 2 weeks
- **Lines of Code**: ~3,400 (Python + TypeScript)
- **Test Coverage**: Partial (critical paths covered)
- **Production Status**: Deployed to Fly.io, working end-to-end
- **Time Saved**: Estimated 100+ hours vs manual coding

### Qualitative

- **System Architecture**: Comparable to senior engineer design
- **Code Quality**: Passes strict linters, type-safe throughout
- **Security**: Fernet encryption, input validation, package checks
- **Production Ready**: Health checks, migrations, error handling

### Proof

Working deployment (as of December 2025):
- GitHub: https://github.com/zenchantlive/catwalk
- Methodology documented in this file
- All context files available in `context/` directory

---

## Conclusion

**Can AI build production systems without human coding?**

**Yes**, with heavy caveats:

1. ✅ AI can generate production-quality code **if given proper structure and constraints**
2. ✅ AI excels at boilerplate, patterns, and known paradigms
3. ❌ AI struggles with infrastructure quirks, security edge cases, and async concurrency
4. ✅ **Humans are still critical** for architecture, validation, debugging, and product decisions

**The skill shift**:
- Old: Writing code line-by-line
- New: Architecting systems, validating outputs, orchestrating AI agents

**Is this the future?** Probably. AI coding is getting better every month. The developers who learn to **orchestrate AI effectively** will have a massive productivity advantage.

**This project proves it's possible**. The methodology is documented. The results are in production.

Now it's your turn. 🚀

---

## Appendix: Tools Used

### AI Coding Assistants
- **Claude Code** (primary) - Architecture, system design, implementation
- **Cursor** - Refactoring, iterative development
- **Google Gemini** - Planning, cross-validation
- **ChatGPT (GPT-4)** - Cross-validation, problem-solving

### GitHub Review Agents
- **CodeRabbit** - Security analysis
- **Qodo** - Edge case detection
- **Gemini Code Assist** - Code quality
- **Greptile** - Integration checks

### Development Tools
- **VS Code** with Claude Code extension
- **Git** for version control
- **Fly.io** for deployment
- **PostgreSQL** for database
- **Bun** for frontend tooling

---

**Questions? Feedback?** Open an issue on GitHub!

**Want to learn more?** See `CONTRIBUTING.md` for how to contribute using AI tools.
