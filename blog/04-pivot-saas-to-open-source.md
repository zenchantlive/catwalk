---
title: "Part 4: The Pivot - From SaaS to Open Source"
series: "Building Catwalk Live with AI Orchestration"
part: 4
date: 2025-12-19
updated: 2025-12-27
tags: [Open Source, Product Strategy, Glama Registry, API Integration, AI Orchestration]
reading_time: "9 min"
status: published
---

# Part 4: The Pivot - From SaaS to Open Source

**The Story So Far:** Production deployment works. Claude Desktop connects to remote MCP servers. The core vision is validated. Time to scale, right?

Not quite.

## The Original Plan: SaaS Monetization

My initial vision for Catwalk Live:

**SaaS Business Model**:
- Users create accounts (OAuth with Google/GitHub)
- We host their MCP servers on our Fly.io infrastructure
- Subscription pricing: $5/server/month or $20/month unlimited
- We manage encryption keys, database, scaling
- Revenue = (users × servers × $5) - Fly.io costs

**Projected economics** (conservative):
- 100 users × 3 servers each = 300 deployments
- Revenue: $1,500/month
- Costs: $600/month (Fly.io: $2/deployment)
- Margin: $900/month (60%)

**Sounds great, right?**

## The Realization

December 19, 2025. I'm looking at the working production system and asking: **"Who is this for?"**

**Target user profile**:
- Technical enough to understand MCP
- Wants remote MCP servers (mobile/web access)
- Willing to pay $5/month per server
- Trusts us with API credentials

**The problem**: Anyone technical enough to want remote MCP servers is **also technical enough to self-host**.

Why would they pay me $5/month when they could:
- Deploy to their own Fly.io account (same $2/month cost)
- Keep full control of credentials
- Customize deployment configuration
- Avoid vendor lock-in

**The uncomfortable truth**: The market for "paid MCP hosting" is tiny. Power users want control. Casual users don't know what MCP is.

I was building a **solution looking for a problem**.

## The Pivot Decision

I spent December 19-20 rethinking the strategy. Three options:

**Option A: Double down on SaaS**
- Build multi-tenancy (user isolation, billing, subscriptions)
- Add enterprise features (teams, SSO, audit logs)
- Market heavily to non-technical users

**Risk**: Months of work for an unvalidated market. If users don't convert, it's wasted effort.

**Option B: Abandon the project**
- Recognize the market doesn't exist
- Move on to something else

**Risk**: Throwing away a working system and valuable learnings.

**Option C: Open source + self-hosting**
- MIT license, public GitHub repo
- Users bring their own Fly.io accounts and API keys
- Vercel-style demo deployment (try before self-hosting)
- Build community instead of revenue

**Upside**:
- Immediate value to the MCP community
- No vendor lock-in concerns
- Contributors can extend the platform
- Proof of concept for AI orchestration methodology
- Portfolio piece showing end-to-end system design

**Downside**: No revenue (at least not directly)

I chose **Option C**.

Not because I gave up on monetization forever, but because **validation comes before revenue**. If the open-source version gains traction, monetization opportunities emerge (hosted version, enterprise support, premium features).

If it doesn't? I learned AI orchestration methodology and built a portfolio piece. Not wasted.

## The Strategic Shift

**Old vision** (SaaS):
```
User → Sign up → Pay → Deploy → Use
         ↓
    We manage everything
```

**New vision** (Open Source):
```
User → Fork repo → Set up Fly.io → Deploy → Contribute
                     ↓
                Bring own keys
```

**What this changed:**

### 1. Authentication Became Optional

**Old**: Multi-user auth required (OAuth, sessions, user isolation)

**New**: Single-user mode (one row in database, optional auth)

I removed the half-built Supabase authentication:

```bash
# Old code (deleted)
- app/api/auth.py (Supabase callbacks)
- app/models/user.py (User table)
- Frontend sign-in modals
```

**Impact**: Simplified architecture, faster iteration, fewer dependencies.

### 2. Settings UI Became Critical (Phase 0)

**Old**: We store encryption keys, Fly.io tokens, OpenRouter API keys

**New**: **Users must provide their own keys**

This required building a Settings page:

```bash
commit 9ac544c
Date: 2025-12-20

feat: Implement Settings Page, Auth Modal, and Fix Backend Deployment
```

UI for users to paste:
- **Fly.io API Token**: For deploying MCP machines
- **OpenRouter API Key**: For GitHub repo analysis
- **Encryption Key**: For credential encryption

Vercel-style UX: `.env` paste interface with validation.

This became **Phase 0** - the highest priority blocker for the open-source version.

### 3. Documentation Became As Important As Code

**Old**: Minimal docs (devs can figure it out)

**New**: Over-invest in documentation

I created:
- `SETUP.md` - Local development guide
- `DEPLOYMENT.md` - Production deployment to Fly.io
- `CONTRIBUTING.md` - How to contribute using AI tools
- `AI_ORCHESTRATION.md` - Complete methodology case study

**Why?** Open source lives or dies by documentation. If setup is confusing, nobody self-hosts.

### 4. Roadmap Completely Revised

I created a new roadmap document:

```bash
# Created: context/plans/roadmap/OPEN_SOURCE_ROADMAP.md
# Created: context/plans/roadmap/6_MONTH_PLAN.md
# Created: ROADMAP_REVISION_SUMMARY.md
```

**New priorities**:

| Phase | Old Priority | New Priority | Why |
|-------|--------------|--------------|-----|
| Settings UI | Not planned | **P0** | Required for BYOK |
| Documentation | P2 | **P0** | Critical for adoption |
| Health Monitoring | P1 | **P1** | Still important |
| Cost Optimization | P1 | **P2** | Users pay own costs |
| Teams/Enterprise | Planned | **P3** | Not relevant for open source MVP |

**The new 3-month plan**:

- **Month 1**: Settings UI + Health Monitoring
- **Month 2**: Multi-runtime support (Python) + Container logs
- **Month 3**: Frontend polish + Documentation blitz → **Vercel Demo Launch**

## Glama Registry Integration

With open source decided, I tackled a new feature: **MCP server discovery**.

Problem: Users need to find MCP servers to deploy. Currently, they have to:
1. Search GitHub manually
2. Read README files
3. Guess package names
4. Hope it's compatible

**Better UX**: Integrate with **Glama.ai** - a registry of 12,000+ MCP servers with metadata.

I tasked Claude Code:

```
Integrate Glama MCP registry:
- API: https://glama.ai/api/mcp/servers
- Search endpoint: /api/mcp/servers?q={query}
- Display results with:
  - Server name, description, author
  - Trust signals (GitHub stars, last updated)
  - Environment variables needed
  - Click to auto-fill GitHub URL

Tech:
- Backend: RegistryService with httpx
- Frontend: Search component with debounced input
- Cache results (1 hour TTL)
```

Claude Code generated:

```bash
commit 7c2fa06
Date: 2025-12-14

feat(backend): implement registry service and api
```

**Backend** (`backend/app/services/registry_service.py`):
```python
import httpx
from typing import List, Dict

class RegistryService:
    def __init__(self):
        self.base_url = "https://glama.ai/api/mcp"
        self._client = None

    async def search_servers(self, query: str) -> List[Dict]:
        """Search Glama registry for MCP servers"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/servers",
                params={"q": query, "limit": 20}
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return data.get("servers", [])
```

**Frontend** (`frontend/components/RegistrySearch.tsx`):
```typescript
'use client'

import { useState } from 'react'
import { useDebounce } from '@/hooks/useDebounce'

export function RegistrySearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])

  const debouncedQuery = useDebounce(query, 300)

  useEffect(() => {
    if (debouncedQuery) {
      fetch(`/api/registry/search?q=${debouncedQuery}`)
        .then(res => res.json())
        .then(data => setResults(data.servers))
    }
  }, [debouncedQuery])

  return (
    <div>
      <input
        type="text"
        placeholder="Search MCP servers..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {results.map(server => (
        <ServerCard key={server.id} server={server} />
      ))}
    </div>
  )
}
```

**This worked beautifully.** Users could now:
1. Type "github" in search
2. See 20 GitHub-related MCP servers
3. Click one → auto-fills GitHub URL
4. Backend analyzes → generates credential form
5. Deploy

**Time to implement**: ~3 hours (including frontend UI)

**AI contribution**: 90% (I tweaked debounce timing and result styling)

## The Concurrency Bug AI Missed

Testing the registry integration heavily, I noticed:

```
RuntimeError: dictionary changed size during iteration
```

Only happened under load (multiple concurrent searches).

**The bug** (in `registry_service.py`):

```python
class RegistryService:
    def __init__(self):
        self._cache = {}  # Shared dict, no locking!

    async def search_servers(self, query: str):
        # Check cache
        if query in self._cache:
            return self._cache[query]

        # Fetch from API
        results = await self._fetch_from_glama(query)

        # Update cache (RACE CONDITION!)
        self._cache[query] = results
        return results
```

**The problem**: Multiple async requests modifying `_cache` simultaneously → dictionary corruption.

**AI didn't catch this** because:
- The code looks correct in isolation
- Concurrency bugs require thinking about race conditions
- Training data has more single-threaded examples

**The fix** I implemented:

```python
import asyncio

class RegistryService:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()  # Thread-safe lock

    async def search_servers(self, query: str):
        # Check cache (read-only, safe)
        if query in self._cache:
            return self._cache[query]

        # Acquire lock for write
        async with self._lock:
            # Double-check (another request may have filled cache)
            if query in self._cache:
                return self._cache[query]

            # Fetch and cache
            results = await self._fetch_from_glama(query)
            self._cache[query] = results
            return results
```

**Lesson**: AI generates async code correctly, but **concurrency safety requires manual review**.

**How to catch this**:
- Load testing (multiple concurrent requests)
- Code review with concurrency in mind
- Ask AI: "Is this code thread-safe under high concurrency?"

## README Revision for Open Source

With the pivot decided, the README needed rewriting:

**Old README**:
```markdown
# Catwalk Live

A platform for deploying MCP servers remotely.

## Quick Start
Sign up at https://catwalk.live
Deploy your first MCP server
```

**New README**:
```markdown
# Catwalk Live

**A Vercel-like platform for deploying Remote MCP servers to Fly.io,
built entirely through AI orchestration.**

> 🤖 This project was built using a multi-stage AI development pipeline
> (Claude Code, Cursor, Gemini Code Assist) without manually writing code.

## 🤖 Built with AI Orchestration

**This project is a case study in AI-assisted development.**

See [AI_ORCHESTRATION.md](AI_ORCHESTRATION.md) for the complete story
of how to build production systems with AI.

## Quick Start

1. Fork this repo
2. Set up Fly.io account
3. Deploy backend: `fly deploy`
4. Add your API keys in Settings
5. Deploy MCP servers!

## Contributing

We welcome AI-assisted contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).
```

I **leaned into the AI orchestration story**. This wasn't just an MCP deployment platform - it was **proof that AI can build production systems**.

The meta-narrative became part of the value proposition.

## What I Learned About AI and Pivots

### 1. AI Follows Your Vision - You Must Change It

When I decided to pivot to open source, AI didn't magically understand the new strategy. I had to:

1. Update `AGENTS.md` with new context:
   ```markdown
   ## Project Strategy (UPDATED 2025-12-20)

   **OLD**: SaaS with multi-user auth and subscriptions
   **NEW**: Open source with BYOK (Bring Your Own Keys)

   **Impact on Development**:
   - Remove multi-user auth (use single-user mode)
   - Build Settings UI for API key management (NEW - P0)
   - Prioritize documentation over features
   - Focus on self-hosting UX
   ```

2. Update `CURRENT_STATUS.md`:
   ```markdown
   ## Critical New Priority: Phase 0

   **Phase 0: Settings & Key Management**
   - Status: NEW - Immediate priority
   - Why: Vercel demo cannot work without user-provided keys
   ```

3. Give explicit instructions:
   ```
   We've pivoted to open source. Remove Supabase auth.
   Build a Settings page where users paste their own API keys.
   Follow Vercel's .env paste UI pattern.
   ```

**Lesson**: Strategic pivots require **updating AI context files**, not just telling AI what to build next.

### 2. AI Is Great at Adapting Code, Not Strategy

AI helped me:
- ✅ Remove authentication code quickly
- ✅ Generate Settings UI based on new requirements
- ✅ Update README to reflect open source positioning

AI didn't help me:
- ❌ Decide whether to pivot
- ❌ Evaluate market fit
- ❌ Choose between SaaS vs open source
- ❌ Prioritize new features

**Product strategy is still human work.** AI executes your vision - it doesn't create it.

### 3. Open Source Changed How I Used AI

**Before pivot** (SaaS mindset):
- Optimize for feature velocity
- "Move fast and break things"
- Internal docs sufficient

**After pivot** (Open source mindset):
- Optimize for code clarity (others will read it)
- Comprehensive error messages (can't debug users' environments)
- Documentation-first (setup friction kills adoption)

I started prompting AI differently:

**Old prompt**:
```
Build a deployment service that creates Fly.io machines
```

**New prompt**:
```
Build a deployment service that creates Fly.io machines.

Add extensive error handling for:
- Invalid Fly.io API tokens
- Network timeouts
- Machine creation failures
- Insufficient Fly.io quota

Include detailed error messages that tell users:
- What went wrong
- Why it failed
- How to fix it (with links to docs)

Add inline code comments explaining the Fly.io API flow.
```

Result: More maintainable code, better error UX, easier for contributors.

## Key Metrics After the Pivot

**Time Spent on Pivot**: ~8 hours over 2 days
- Strategy thinking: 2 hours
- Removing auth code: 1 hour
- Glama registry integration: 3 hours
- README and docs rewrite: 2 hours

**Code Changes**:
- **Removed**: ~400 lines (Supabase auth, user models)
- **Added**: ~600 lines (Settings UI, registry service, docs)
- **Net**: +200 lines, but -15% complexity

**Documentation Growth**:
- **Before**: README (300 words)
- **After**:
  - README (1,200 words)
  - AI_ORCHESTRATION.md (3,500 words)
  - CONTRIBUTING.md (800 words)
  - SETUP.md (600 words)
  - DEPLOYMENT.md (900 words)

**Total**: ~7,000 words of documentation (3x the code volume)

## The Unexpected Benefit

The pivot to open source forced me to **document the AI orchestration methodology**.

`AI_ORCHESTRATION.md` became:
- A how-to guide for others building with AI
- Proof that this wasn't just "ChatGPT autocomplete"
- A case study in structured AI development
- The most valuable artifact of the project

People could fork the repo and replicate the approach. The **methodology became as valuable as the platform itself**.

## Coming Next

In **Part 5**, things get messy:
- Building the Settings page (Phase 0)
- JWT authentication crisis
- The `AUTH_SECRET` vs `NEXTAUTH_SECRET` vs `AUTH_SYNC_SECRET` disaster
- 401 errors everywhere
- Creating `AUTH_TROUBLESHOOTING.md` after days of debugging
- How unclear error messages wasted hours

**Spoiler**: Sometimes the hardest bugs aren't in the code AI generated - they're in the **environment configuration** that AI can't see.

---

**Commit References**:
- `7c2fa06` - Glama registry backend service
- `c51cb10` - Registry UI components
- `9cc59f0` - Prepare for MIT open source release
- `50c56b4` - README update with project details

**Documents Created**:
- `ROADMAP_REVISION_SUMMARY.md`
- `context/plans/roadmap/OPEN_SOURCE_ROADMAP.md`
- `context/plans/roadmap/6_MONTH_PLAN.md`
- `AI_ORCHESTRATION.md` (comprehensive case study)

**Strategic Lessons**:
- Validate market before building features
- Open source removes adoption friction
- Documentation is as valuable as code
- AI executes vision; humans create it

**Code**:
- [backend/app/services/registry_service.py](https://github.com/zenchantlive/catwalk/blob/main/backend/app/services/registry_service.py)
- [AI_ORCHESTRATION.md](https://github.com/zenchantlive/catwalk/blob/main/AI_ORCHESTRATION.md)

---

*This is Part 4 of 7. The business model changed, but the technical challenges were just beginning.*

**Previous**: [← Part 3: Production Baptism](03-production-baptism-flyio.md)
**Next**: [Part 5: Authentication Hell →](05-authentication-hell-401-marathon.md)
