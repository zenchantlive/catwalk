---
title: "Part 1: Genesis - Choosing AI-First Development"
series: "Building Catwalk Live with AI Orchestration"
part: 1
date: 2025-12-11
updated: 2025-12-27
tags: [AI, Claude Code, MCP, Solo Founder, AI Orchestration, Startup]
reading_time: "8 min"
status: published
---

# Part 1: Genesis - Choosing AI-First Development

**The Story So Far:** Nothing exists yet. Just an idea and a decision to build it entirely with AI.

## The Problem That Wouldn't Let Go

I've been obsessed with the **Model Context Protocol (MCP)** since Anthropic announced it. For the uninitiated, MCP is essentially a universal adapter system that lets AI assistants like Claude interact with external tools and data sources. Think of it as USB-C for AI agents.

The problem? MCP was designed for **stdio (standard input/output) communication**, meaning both Claude and the MCP server had to run on the same machine. This created massive limitations:

- **Device-locked**: Only works on your laptop
- **Desktop-only**: No mobile or web access
- **Technical barrier**: Requires Node.js, JSON config files, process management
- **Session-bound**: Server dies when you close your laptop
- **Not shareable**: Can't give team members access

Real-world impact: Powerful MCP servers existed for TickTick, GitHub, Slack, Google Drive, and hundreds of other services, but **95% of Claude users couldn't access them** because they weren't technical enough or didn't use Claude Desktop.

I saw an opportunity: **What if we could transform local-only MCP servers into remote HTTP endpoints?**

Think "Heroku for MCP servers" - paste a GitHub URL, enter your API keys, get a URL you can use anywhere (desktop, mobile, web).

## The Unconventional Decision

Here's where it gets interesting. **I'm not a traditional backend engineer.**

I can't write FastAPI from scratch. I don't know SQLAlchemy's async patterns by heart. I've never deployed to Fly.io before this project.

But I *can*:
- Architect systems and understand data flow
- Validate AI outputs for logic errors and security issues
- Debug integration problems and infrastructure quirks
- Make product decisions and trade-offs
- **Orchestrate AI agents to build what I design**

So on December 11, 2025, I made a decision: **Build this entire platform using AI coding assistants. Zero manual coding.**

Not as a gimmick. As a **genuine test** of whether AI orchestration could ship production systems.

## The Initial Commit

```bash
commit 215deaa
Author: zenchantlive
Date: 2025-12-11

Initial commit
```

That first commit was generated entirely by Claude Code. No boilerplate written by hand. The AI created:

- Empty repository structure
- Basic `.gitignore`
- Placeholder README

Underwhelming? Absolutely. But it was a stake in the ground.

Within hours, the second commit landed:

```bash
commit f6e024a
Date: 2025-12-11

feat: Implement new Supabase authentication callback routes and pages,
replacing old callback logic.
```

Wait, Supabase? Authentication? We're not even building the core platform yet!

This was my first lesson in AI orchestration: **AI generates what you tell it to, not necessarily what you need first.**

I had fed Claude Code a vague prompt about "building an MCP deployment platform with authentication." The AI, being helpful, started with auth because it seemed foundational. But we didn't need multi-user auth for an MVP. We needed:

1. GitHub repo analysis
2. Credential encryption
3. Deployment orchestration
4. MCP Streamable HTTP transport

Classic product/engineering misalignment - except I was both roles, and I was learning how to communicate with AI.

## The Pivot: Phase 3 First

I stopped the AI mid-stream and refined my approach. Instead of a vague mega-prompt, I broke the project into **phases** and gave Claude Code explicit, structured instructions:

**New prompt** (paraphrased):
```
Build Phase 3: Credential Management Foundation

Requirements:
1. Database models for storing encrypted credentials (Fernet)
2. SQLAlchemy async setup with PostgreSQL
3. Encryption service (cryptography.fernet)
4. Dynamic form schema based on MCP server requirements
5. NO authentication yet - single-user MVP

Tech stack:
- FastAPI with async
- SQLAlchemy 2.0+ (async ORM)
- PostgreSQL (prepare for Fly.io deployment)
- Pydantic for validation
- Fernet encryption for secrets

Success criteria:
- Can store credentials encrypted at rest
- Can decrypt only during deployment
- No plaintext credentials in logs or responses
- Passes `ruff check` with zero warnings
```

This time, Claude Code nailed it:

```bash
commit b92443c
Date: 2025-12-11

feat: Initialize Phase 3 Credential Management models and config
```

```bash
commit 4d6b32b
Date: 2025-12-11

feat(phase-3): Credential Management Foundation and Dynamic Forms
```

Two commits, ~400 lines of code, production-ready credential management. Time elapsed: **maybe 30 minutes** including my review and validation.

## What I Learned in Day 1

### 1. Specificity Matters More Than You Think

**Bad prompt**: "Build an MCP deployment platform"
**Result**: AI generates generic CRUD, guesses at architecture, makes assumptions

**Good prompt**: "Build credential encryption service using Fernet, async SQLAlchemy with PostgreSQL, must pass ruff with zero warnings"
**Result**: AI generates production-quality code following exact constraints

The difference? **Precision eliminates ambiguity.** AI doesn't "understand" your vision - it predicts tokens based on your prompt. Vague prompts = vague code.

### 2. AI Needs External Memory

Within a few hours, I noticed Claude Code would "forget" architectural decisions from earlier in the session. It would try to reintroduce features I'd already rejected or suggest patterns inconsistent with prior code.

This wasn't a bug - it was working as designed. AI context windows are limited, and without persistent memory, each interaction felt like starting over.

**Solution**: I created `AGENTS.md` - a system prompt that defined:
- Project architecture and tech stack
- Coding standards and quality requirements
- What to avoid (anti-patterns we'd already tried and rejected)
- Current project status and next steps

I instructed Claude Code to **read `AGENTS.md` before every session** and **update it when learning new lessons**.

This single file became the "constitution" that kept AI aligned across sessions.

### 3. Validate Everything

By the end of day 1, I had ~800 lines of AI-generated code. Did I trust it blindly?

**Hell no.**

I ran:
```bash
cd backend
ruff check .        # Linter (must pass with zero warnings)
ruff format .       # Auto-formatter
pytest              # All tests (there weren't many yet, but principle matters)
```

Found issues:
- Missing type hints in a few functions
- Inconsistent import ordering
- One unused variable

I fed the linter errors back to Claude Code: *"Fix these ruff warnings"*

It fixed them in 30 seconds.

**Key insight**: AI generates code fast, but validation is YOUR job. Run linters. Read diffs. Understand what changed. Don't merge code you don't understand.

## The Architecture Takes Shape

By the end of December 11, the foundation existed:

**Database Models** (`backend/app/models/`):
- `Deployment` - Stores deployment metadata and status
- `Credential` - Stores Fernet-encrypted user API keys
- `AnalysisCache` - Caches GitHub repo analysis results

**Services** (`backend/app/services/`):
- `EncryptionService` - Fernet encryption/decryption for credentials
- Schema generation for dynamic credential forms

**Configuration** (`backend/app/core/config.py`):
- Pydantic Settings for environment variables
- PostgreSQL connection setup (preparing for Fly.io)

**Not yet built**:
- GitHub repo analysis (that's Phase 4)
- Deployment orchestration (Phase 5)
- MCP Streamable HTTP transport (Phase 6)
- Frontend UI (Phase 4)

But the foundation was **solid**. Type-safe. Linted. Encrypted credentials working.

## The Moment of Truth

I asked myself: *Is this actually production-quality, or just clever AI-generated demos?*

To test it, I manually inspected the encryption service:

```python
# Generated by Claude Code
from cryptography.fernet import Fernet
import json

class EncryptionService:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())

    def encrypt_credentials(self, creds: dict) -> bytes:
        json_str = json.dumps(creds)
        return self.cipher.encrypt(json_str.encode())

    def decrypt_credentials(self, encrypted: bytes) -> dict:
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())
```

Simple. Correct. Exactly what I would've written manually, but faster.

**The encryption worked.** I tested it:
```python
service = EncryptionService(key="...")
encrypted = service.encrypt_credentials({"API_KEY": "secret123"})
print(encrypted)  # b'gAAAAA...' (encrypted blob)

decrypted = service.decrypt_credentials(encrypted)
print(decrypted)  # {'API_KEY': 'secret123'}
```

Perfect. **This was real.**

## What Didn't Work

Not everything was smooth:

### AI Attempted Authentication Too Early
As mentioned, Claude Code tried to build Supabase auth before core features. I had to redirect it.

**Lesson**: Break projects into explicit phases. Don't let AI prioritize for you.

### Overly Generic Variable Names
AI loves naming things `data`, `result`, `response`. I had to enforce:
```python
# AI's first pass
data = fetch_data()

# After feedback
analysis_result = fetch_repo_analysis()
```

**Lesson**: Prompt for specificity. "Use descriptive variable names" in your system prompt.

### Missing Edge Case Handling
The encryption service didn't handle invalid keys or corrupted data.

I added to my prompt: *"Add error handling for Fernet decryption failures"*

Claude Code added try/except blocks and custom exceptions.

**Lesson**: AI generates the happy path. YOU must prompt for error cases.

## Key Takeaways

**After 1 day of AI-orchestrated development:**

✅ **What worked:**
- Structured prompts with explicit tech stack and constraints
- External memory (`AGENTS.md`) for cross-session consistency
- Validation workflow (linter → AI → fix → repeat)
- Phase-based development (credential management first)

❌ **What didn't work:**
- Vague mega-prompts ("build an MCP platform")
- Trusting AI blindly without validation
- Letting AI prioritize features (it defaults to "foundations" like auth)

📊 **Metrics:**
- **Lines of code**: ~800 (Python backend)
- **Time spent**: ~4 hours (including learning curve)
- **Manual coding**: 0 lines (100% AI-generated)
- **Quality**: Production-ready (passed all linters)

## Coming Next

In **Part 2**, I'll cover the next 48 hours where:
- Multi-AI planning (Claude, GPT-4, Gemini cross-validation)
- Aurora UI implementation (the frontend emerges)
- First attempts at Fly.io deployment (spoiler: PostgreSQL driver hell)
- Creating the `context/` directory structure that became critical

The real challenges hadn't started yet. Day 1 was gentle. Days 2-4 were a **production deployment gauntlet**.

---

**Commit References**:
- `215deaa` - Initial commit
- `f6e024a` - Supabase auth attempt (later abandoned)
- `b92443c` - Phase 3 initialization
- `4d6b32b` - Credential management foundation

**Tools Used**: Claude Code (Anthropic CLI)

**Code**: [backend/app/models/](https://github.com/zenchantlive/catwalk/tree/main/backend/app/models)

---

*This is Part 1 of a 7-part series documenting the complete journey of building Catwalk Live - a production MCP deployment platform - using only AI orchestration. No code written manually.*

**Next**: [Part 2: Foundation - The First 48 Hours →](02-foundation-first-48-hours.md)
