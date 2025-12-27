---
title: "Part 2: Foundation - The First 48 Hours"
series: "Building Catwalk Live with AI Orchestration"
part: 2
date: 2025-12-11
updated: 2025-12-27
tags: [AI, Claude Code, Next.js, FastAPI, Multi-AI Planning, Architecture]
reading_time: "10 min"
status: published
---

# Part 2: Foundation - The First 48 Hours

**The Story So Far:** Day 1 ended with a working credential management system - all AI-generated. But we had no UI, no analysis engine, and no deployment orchestration. Just encrypted database models.

## The Multi-AI Planning Session

Before writing more code, I tried something unconventional: **cross-validating architecture across three different AI models**.

I took the same detailed prompt and fed it to:
1. **Claude Code** (via Anthropic CLI)
2. **ChatGPT-4** (via web interface)
3. **Google Gemini** (via Google AI Studio)

The prompt (condensed):
```
Design a platform that:
- Accepts GitHub repo URLs for MCP servers
- Uses Claude API to analyze repos and extract config
- Generates dynamic credential forms
- Deploys to Fly.io with isolated containers
- Implements MCP Streamable HTTP transport

Tech stack: Next.js 15, FastAPI, PostgreSQL, Fly.io

Question: What's the optimal architecture?
```

### The Results

**Claude's Response:**
```
3-layer architecture:
- Frontend (Next.js) → Backend API (FastAPI) → MCP Machines (Fly.io)
- Use Claude API with web search plugin for repo analysis
- Fernet encryption for credentials
- PostgreSQL for deployments + credentials + cache
- Streamable HTTP at /api/mcp/{deployment_id}
```

**GPT-4's Response:**
```
Similar structure, but suggested:
- Use asyncpg for PostgreSQL (WRONG - we'll discover this later)
- Redis for caching instead of PostgreSQL
- Separate microservices for analysis vs deployment
```

**Gemini's Response:**
```
Agreed with Claude on most points:
- Monolith is fine for MVP (not microservices)
- Use psycopg3 for PostgreSQL async (CORRECT)
- Consider rate limiting on analysis endpoint
- MCP session management via headers
```

### Consensus Patterns (Good Design Indicators)

All three AIs agreed on:
- ✅ 3-layer architecture (Frontend → Backend → MCP Containers)
- ✅ FastAPI with async (not sync)
- ✅ PostgreSQL for persistence (not in-memory)
- ✅ Fernet encryption (industry standard, simple)
- ✅ Caching analysis results (expensive LLM calls)

### Discrepancies (Complexity Indicators)

Where they disagreed:
- **PostgreSQL driver**: asyncpg (GPT-4) vs psycopg3 (Gemini, Claude)
- **Caching layer**: Redis (GPT-4) vs PostgreSQL JSONB (Claude, Gemini)
- **Architecture**: Microservices (GPT-4) vs Monolith (Claude, Gemini)

**My decision process:**

1. **PostgreSQL driver**: I chose **psycopg3** (majority + better SSL support for Fly.io)
   - This proved **critical** later when asyncpg failed with Fly.io's `sslmode` parameters

2. **Caching**: Chose **PostgreSQL JSONB** (simpler, fewer dependencies)
   - MVP doesn't need Redis complexity
   - Can migrate later if needed

3. **Architecture**: Chose **monolith** (faster iteration)
   - Microservices add deployment complexity
   - Can split later if scaling demands it

**Lesson learned**: Different AI training data = different blind spots. **Cross-validation catches issues early.**

## Phase 4: Aurora UI Implementation

With architecture decided, I tasked Claude Code with building the frontend:

```bash
commit f5a957a
Date: 2025-12-11

feat(phase-4): Implement Aurora UI (Landing, Dashboard, Forms)
```

This single commit added:
- Landing page with hero section and feature grid
- Dashboard for viewing deployments
- Dynamic credential form builder
- GitHub URL input with validation
- **~1,200 lines of TypeScript + React**

Generated in under an hour.

### The Dynamic Form Magic

The most impressive part: **dynamic form generation from analysis results**.

Here's the flow:
1. User pastes GitHub URL: `https://github.com/alexarevalo9/ticktick-mcp-server`
2. Backend analyzes repo, extracts config:
   ```json
   {
     "package": "@alexarevalo.ai/mcp-server-ticktick",
     "env_vars": [
       {
         "name": "TICKTICK_CLIENT_ID",
         "description": "Your TickTick OAuth Client ID",
         "required": true,
         "secret": false
       },
       {
         "name": "TICKTICK_CLIENT_SECRET",
         "description": "Your TickTick OAuth Client Secret",
         "required": true,
         "secret": true
       },
       {
         "name": "TICKTICK_ACCESS_TOKEN",
         "description": "OAuth access token from TickTick",
         "required": true,
         "secret": true
       }
     ]
   }
   ```
3. Frontend **auto-generates a form** with:
   - Text inputs for CLIENT_ID
   - Password inputs for secrets (CLIENT_SECRET, ACCESS_TOKEN)
   - "Required" labels where needed
   - Help text from descriptions

Claude Code generated the `FormBuilder.tsx` component that does this transformation automatically. No hardcoding. No manual form creation.

**This was the first "wow" moment** - AI building AI-powered forms that adapt to any MCP server's requirements.

### The Type Safety Obsession

I enforced strict TypeScript rules:
- No `any` types allowed
- All props must have explicit interfaces
- Zod schemas for runtime validation

Example from the generated code:

```typescript
// backend/app/models/deployment.py returns this schema
interface AnalysisResult {
  package: string
  name: string
  description: string
  env_vars: EnvVar[]
  tools: Tool[]
  resources: Resource[]
  prompts: Prompt[]
}

interface EnvVar {
  name: string
  description: string
  required: boolean
  secret: boolean
  default?: string
}

// FormBuilder component uses this to generate inputs
const FormBuilder: React.FC<{ analysis: AnalysisResult }> = ({ analysis }) => {
  // AI-generated logic to map env_vars → form fields
  return (
    <form>
      {analysis.env_vars.map(envVar => (
        <Input
          key={envVar.name}
          type={envVar.secret ? 'password' : 'text'}
          required={envVar.required}
          placeholder={envVar.description}
        />
      ))}
    </form>
  )
}
```

**Zero type errors. Zero runtime surprises.**

Claude Code generated this because I was explicit in my prompt:
```
Use TypeScript 5+ with strict mode
All components must have typed props
Use Zod for schema validation
Never use 'any' - create types or use 'unknown' with guards
```

## Creating the Context Structure

By the end of Day 2, I noticed AI sessions were becoming **inconsistent**. Claude Code would:
- Forget architectural decisions from earlier sessions
- Suggest patterns we'd already rejected
- Ask questions I'd already answered

The problem: **AI memory is session-bound**. When you start a new session, it's a blank slate.

I needed **persistent external memory** - a knowledge base that survived across sessions.

### The `context/` Directory

I created a structured documentation system:

```bash
context/
├── ARCHITECTURE.md       # System design, data flow, tech stack
├── CURRENT_STATUS.md     # What works, what doesn't, next steps
├── Project_Overview.md   # The problem, solution, user journey
├── TECH_STACK.md         # Every dependency and why we chose it
├── API_SPEC.md           # Endpoint documentation
└── plans/
    ├── phase-3-credential-management.md
    ├── phase-4-frontend-ui.md
    └── phase-5-deployment-orchestration.md
```

**Each file served a purpose:**

**`ARCHITECTURE.md`** - The "how it works" bible:
```markdown
## Data Flow: Complete Journey

### Flow 1: Analyze Repository
User enters GitHub URL
  ↓
Frontend validates URL format
  ↓
POST /api/analyze {repo_url}
  ↓
Backend checks cache (AnalysisCache table)
  ↓ (cache miss)
Claude API called with web search plugin
  ↓
Claude extracts: package, env_vars, tools, resources
  ↓
Backend validates response schema
Backend caches result (24h TTL)
  ↓
Returns JSON config to frontend
```

**`CURRENT_STATUS.md`** - The living "where we are" document:
```markdown
## ✅ Completed Features

### Phase 3: Credential Management
- ✅ Fernet encryption service
- ✅ PostgreSQL models (Deployment, Credential)
- ✅ Dynamic form schema generation

### Phase 4: Frontend UI
- ✅ Landing page
- ✅ Dashboard components
- ✅ Dynamic credential forms

## 🚧 What's NOT Working Yet

- ❌ No GitHub repo analysis yet (Phase 4 WIP)
- ❌ No Fly.io deployment (Phase 5)
- ❌ No MCP Streamable HTTP transport (Phase 6)
```

**`AGENTS.md`** - The AI system prompt:
```markdown
You are a Senior Full-Stack Engineer for Catwalk Live.

## Current Project Status (READ THIS FIRST)
**Phase**: 4 In Progress - Frontend UI + Repo Analysis

**Critical Context Files**:
1. context/CURRENT_STATUS.md - What works, what doesn't
2. context/ARCHITECTURE.md - System design
3. context/TECH_STACK.md - Every dependency

## Interaction Protocol
1. Read context files before starting any task
2. Implement thoughtful, type-safe solutions
3. Write tests for critical logic
4. Run quality checks (typecheck, lint, test)
5. Update CURRENT_STATUS.md when completing tasks

## Boundaries

### ✅ Always
- Use TypeScript strict mode (no 'any' types)
- Write descriptive variable names
- Add error handling for edge cases
- Pass `ruff check` (Python) or `bun run typecheck` (TypeScript)

### 🚫 Never
- Commit secrets or API keys
- Skip type hints in Python
- Use 'any' in TypeScript
- Modify database schemas without migrations
```

### The Immediate Impact

Next session, I started Claude Code with:
```
Read context/CURRENT_STATUS.md and context/ARCHITECTURE.md
before proceeding. Implement Phase 4: GitHub repo analysis
using Claude API with web search.
```

Claude Code:
1. ✅ Read both files
2. ✅ Understood we were on Phase 4 (not starting from scratch)
3. ✅ Generated code consistent with existing architecture
4. ✅ Used the exact tech stack documented (OpenRouter API, not direct Claude)

**This changed everything.** No more "AI amnesia." No more re-explaining architectural decisions.

**The context files became the "codebase constitution"** that AI had to respect.

## The Analysis Engine Emerges

With context structure in place, I tasked Claude Code:

```
Implement repository analysis service:
- Use OpenRouter API (anthropic/claude-haiku-4.5)
- Enable web search plugin with max_results=2
- Extract: package name, env vars, tools, resources, prompts
- Cache results in AnalysisCache table (24h TTL)
- Return structured JSON matching AnalysisResult schema
```

The AI generated `backend/app/services/analysis.py`:

```python
from openai import AsyncOpenAI  # OpenRouter is OpenAI-compatible
import json
import re

class AnalysisService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    async def analyze_repo(self, repo_url: str) -> dict:
        # Use Claude Haiku 4.5 with web search
        response = await self.client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=[{
                "role": "user",
                "content": ANALYSIS_PROMPT.format(repo_url=repo_url)
            }],
            extra_body={
                "plugins": [{"id": "web", "max_results": 2}]
            }
        )

        # Extract JSON from response
        content = response.choices[0].message.content
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)

        if json_match:
            return json.loads(json_match.group(1))
        else:
            # Try to parse entire response as JSON
            return json.loads(content)
```

**Critical detail**: The AI used **regex to extract JSON** from markdown code blocks.

Why? Because Claude API often wraps JSON in triple backticks:
````
```json
{
  "package": "@example/mcp-server",
  ...
}
```
````

This regex pattern made the analysis service **robust to formatting variations**.

**I didn't tell AI to do this.** It inferred the problem from the prompt: *"Extract structured JSON from LLM response"*

## What Worked vs What Didn't

### ✅ What Worked

**Multi-AI cross-validation**:
- Caught the asyncpg vs psycopg3 debate early
- Majority consensus led to correct decision
- Prevented a painful database driver migration later

**Context files as external memory**:
- Eliminated "AI amnesia" across sessions
- Kept architecture consistent
- Made onboarding new AI sessions trivial

**Structured prompts with explicit constraints**:
- Type safety enforcement in prompts → zero `any` types
- Linter requirements in prompts → all code passed `ruff check`
- Explicit tech stack → no dependency surprises

**Dynamic form generation**:
- Single `FormBuilder` component handles any MCP server
- No hardcoding per-service
- Scales to infinite MCP servers

### ❌ What Didn't Work

**AI tried to build too much at once**:
```bash
commit af021a1
Date: 2025-12-12

work on front end and backend for attempt to complete flow,
next sttepis working on fly.ioo integration
```

This commit message (with typo "sttepis") showed AI was rushing. It tried to:
- Build frontend components
- Implement backend analysis
- Start Fly.io deployment
- **All in one session**

Result: None of it worked properly. Features half-implemented. Integration bugs everywhere.

**Lesson**: I should've enforced **one phase per session**. Keep scope tight.

**Variable naming still generic in places**:
Despite my prompts for descriptive names, AI still generated:
```python
# AI's first pass
data = process_data(input_data)
result = calculate_result(data)
```

I had to manually catch these during code review:
```python
# After feedback
analysis_result = analyze_github_repo(repo_url)
deployment_config = generate_deployment_config(analysis_result)
```

**Lesson**: Even with explicit prompts, **code review is non-negotiable**.

**Missing error handling in happy-path code**:
The analysis service didn't handle:
- Invalid GitHub URLs
- API rate limits
- Malformed JSON responses
- Network timeouts

I had to prompt: *"Add comprehensive error handling for all failure modes"*

Only then did AI add try/except blocks and custom exceptions.

**Lesson**: AI generates happy paths. **You must prompt for error cases explicitly.**

## Key Metrics After 48 Hours

**Lines of Code**: ~2,400
- Backend (Python): ~1,200
- Frontend (TypeScript): ~1,200

**Time Spent**: ~8 hours
- Multi-AI planning: 1 hour
- Creating context structure: 1 hour
- AI code generation: 3 hours
- Code review & validation: 2 hours
- Debugging integration: 1 hour

**Manual Coding**: 0 lines
- 100% AI-generated code
- My role: architect, reviewer, validator

**Quality**:
- ✅ Passes `ruff check` with zero warnings
- ✅ Passes `bun run typecheck` with zero errors
- ✅ Type-safe throughout (no `any` types)
- ✅ Dynamic forms working locally
- ❌ No production deployment yet

## The Moment I Knew This Would Work

End of Day 2, I ran the frontend locally:

```bash
cd frontend
bun run dev
```

The landing page loaded. I pasted a GitHub URL into the analysis form. Clicked "Analyze."

The backend hit Claude API. Web search plugin fetched the repo. Analysis extracted:
```json
{
  "package": "@alexarevalo.ai/mcp-server-ticktick",
  "env_vars": [
    {"name": "TICKTICK_CLIENT_ID", ...},
    {"name": "TICKTICK_CLIENT_SECRET", ...}
  ],
  "tools": ["list-tasks", "create-task", "update-task"],
  "resources": ["ticktick://tasks"],
  "prompts": []
}
```

The frontend **auto-generated a credential form** with three password fields, help text, and validation.

**I hadn't hardcoded any of this.** The form adapted dynamically to the analysis result.

This was the proof: **AI orchestration could build adaptive, production-quality systems.**

Not just CRUD. Not just boilerplate. But **intelligent UX that responds to data.**

## Coming Next

In **Part 3**, reality hits hard:
- First Fly.io production deployment
- The PostgreSQL driver nightmare (asyncpg fails, migrate to psycopg3)
- Docker CRLF line ending hell on Windows
- Missing dependencies causing crash loops
- MCP Streamable HTTP implementation
- The moment Claude Desktop successfully connected to a remote MCP server

Spoiler: **I spent 6 hours debugging PostgreSQL connections.** AI generated the infrastructure code in 20 minutes, but infrastructure debugging required deep manual intervention.

---

**Commit References**:
- `f5a957a` - Aurora UI (Landing, Dashboard, Forms)
- `af021a1` - First integration attempt (too much scope)
- `a06d684` - Refactored error handling in encryption service
- `4d6b32b` - Credential management foundation

**Tools Used**:
- Claude Code (primary implementation)
- ChatGPT-4 (architecture validation)
- Google Gemini (cross-validation)

**Code**:
- [frontend/components/](https://github.com/zenchantlive/catwalk/tree/main/frontend/components)
- [backend/app/services/analysis.py](https://github.com/zenchantlive/catwalk/tree/main/backend/app/services/analysis.py)

---

*This is Part 2 of a 7-part series. The code works locally. Now comes the hard part: production.*

**Previous**: [← Part 1: Genesis](01-genesis-choosing-ai-first.md)
**Next**: [Part 3: Production Baptism →](03-production-baptism-flyio.md)
