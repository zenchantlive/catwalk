---
title: "Part 3: The AI Analysis Engine"
series: "Catwalk Live Development Journey"
part: 3
date: 2025-12-12
updated: 2025-12-27
tags: [AI, Claude, prompt-engineering, OpenRouter, caching]
reading_time: "12 min"
commits_covered: "af021a1...02f9346"
---

## The Core Problem

We have a platform. We have a database. We have encryption. But there's a fundamental question we haven't answered:

> **How do you teach an AI to analyze an arbitrary MCP server repository and extract everything needed for deployment?**

This isn't a simple parsing task. MCP servers come in all shapes:
- Different package managers (npm, PyPI)
- Different languages (TypeScript, Python)
- Different documentation styles
- Different credential requirements

The AI needs to:
1. Find the repository (given only a GitHub URL)
2. Read the README and package.json/pyproject.toml
3. Understand what the server does
4. Extract the exact package name
5. Identify ALL required environment variables
6. List available tools, resources, and prompts
7. Return structured JSON we can trust

**And it needs to do this reliably, every time.**

## The First Attempt: Naive Prompting

My first prompt to Claude was embarrassingly simple:

```
Analyze this GitHub repository and tell me what MCP server it contains:
{repo_url}
```

Result: A conversational response about what the repo does. Useless.

**Lesson 1**: AI needs **explicit structure** in prompts. "Tell me about X" gets you prose. "Return JSON with these exact fields" gets you structured data.

## The Second Attempt: Structured Output

Better prompt:

```
Analyze this MCP server repository and return ONLY valid JSON:

{
  "package": "exact package name",
  "env_vars": [
    {"name": "VAR_NAME", "description": "...", "required": true}
  ],
  "tools": ["tool1", "tool2"],
  "resources": ["resource1"],
  "prompts": ["prompt1"]
}

Repository: {repo_url}
```

Result: JSON! But incomplete. Claude couldn't access the repository.

**Lesson 2**: LLMs don't browse the web by default. You need to **enable web access explicitly**.

## The Solution: OpenRouter + Web Search Plugin

Enter **OpenRouter** - an API gateway that adds capabilities to LLMs, including web search.

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
)

response = await client.chat.completions.create(
    model="anthropic/claude-haiku-4.5",
    messages=[{
        "role": "user",
        "content": analysis_prompt
    }],
    extra_body={
        "plugins": [{
            "id": "web",
            "max_results": 2  # CRITICAL: Limit results
        }]
    }
)
```

**Why `max_results: 2`**: This was learned the hard way (see "The 200k Token Overflow" below).

**Why Claude Haiku 4.5**: Fast, cheap, good enough for structured extraction. No need for Opus.

## The Prompt: V3 (Production Version)

After multiple iterations, here's the prompt that actually works:

```python
ANALYSIS_SYSTEM_PROMPT = """
You are an expert at analyzing MCP (Model Context Protocol) server repositories.

Your task: Given a GitHub repository URL, extract deployment configuration.

INSTRUCTIONS:
1. Use web search to find the repository
2. Focus on: README.md, package.json, pyproject.toml
3. DO NOT read every file - prioritize entry points
4. Extract ONLY what's listed below
5. Return ONLY valid JSON (no markdown, no explanation)

OUTPUT SCHEMA:
{
  "package": "exact npm package name (e.g., '@user/mcp-server') OR exact PyPI package name",
  "name": "human-friendly name (e.g., 'TickTick MCP Server')",
  "description": "one-sentence description",
  "env_vars": [
    {
      "name": "UPPERCASE_VAR_NAME",
      "description": "clear explanation",
      "required": true/false,
      "secret": true/false,
      "default": "value or null"
    }
  ],
  "tools": ["tool1", "tool2"],
  "resources": ["resource1"],
  "prompts": ["prompt1"],
  "notes": "any special requirements or warnings"
}

CRITICAL RULES:
- package name must be EXACT (used for 'npx {package}' or 'pip install {package}')
- env_vars must include ALL required credentials
- Use web search efficiently (limit to 2-3 queries)
- If unsure, note it in "notes" field

Repository: {repo_url}
"""
```

**Key elements**:

1. **Clear role**: "You are an expert at analyzing MCP repositories"
2. **Explicit task**: "Extract deployment configuration"
3. **Structured output**: Exact JSON schema with types
4. **Constraints**: "DO NOT read every file" (prevents token overflow)
5. **Escape hatch**: `notes` field for uncertainty

**Why "ONLY valid JSON"**: Claude loves to wrap JSON in markdown code blocks. This instruction reduces that.

## The 200k Token Overflow

December 21, 2025. Users report: "Analysis is hanging forever."

I check the logs:

```
RequestValidationError: Input too large (250,000 tokens)
```

**What happened**: OpenRouter's web search plugin, without `max_results` limit, was fetching ENTIRE GitHub documentation pages. One analysis consumed 250k tokens.

**The fix**:

```python
"plugins": [{
    "id": "web",
    "max_results": 2  # Only fetch first 2 search results
}]
```

Combined with prompt instruction: "Focus on README and package.json only"

**Result**: Token usage dropped from 250k to ~5k. Response time from "timeout" to 3 seconds.

**Lesson 3**: Always **limit** what you ask AI to process. More input ≠ better output.

## Parsing the Response: Trust But Verify

Claude returns text. We need to extract JSON:

```python
async def analyze_repo(self, repo_url: str) -> AnalysisResult:
    response = await self.client.chat.completions.create(...)

    content = response.choices[0].message.content

    # Try JSON extraction (Claude sometimes wraps in markdown)
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    else:
        # Maybe it's raw JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

    # Parse and validate
    data = json.loads(content)
    return AnalysisResult(**data)  # Pydantic validation
```

**Defense in depth**:
1. Regex extraction (handles markdown-wrapped JSON)
2. Fallback to raw JSON search
3. Pydantic validation (ensures schema compliance)
4. Exception handling (log failures, return user-friendly errors)

**Why regex**: AI is unpredictable. Sometimes it returns `{"package": "..."}`. Sometimes it returns ` ```json\n{"package": "..."}\n``` `. Regex handles both.

## Caching Strategy: Save Money, Save Time

Claude API costs money. Analyzing the same repo twice is wasteful.

**Solution**: PostgreSQL-backed cache with 24-hour TTL.

```python
async def analyze_repo_cached(self, repo_url: str) -> AnalysisResult:
    # Normalize URL (github.com/user/repo vs github.com/user/repo/)
    normalized_url = repo_url.rstrip('/')

    # Check cache
    cached = await self.cache_service.get(normalized_url)
    if cached and not self.force_refresh:
        return cached

    # Cache miss - run analysis
    result = await self.analyze_repo(normalized_url)

    # Store in cache
    await self.cache_service.set(
        url=normalized_url,
        data=result,
        ttl=timedelta(hours=24)
    )

    return result
```

**Cache invalidation**:

```python
# Manual cache clearing (admin only)
@router.delete("/api/analyze/cache")
async def clear_cache(repo_url: str):
    await cache_service.delete(repo_url)
    return {"message": "Cache cleared"}

# Force refresh (any user)
@router.post("/api/analyze")
async def analyze(repo_url: str, force: bool = False):
    result = await service.analyze_repo_cached(repo_url, force=force)
    return result
```

**Why 24 hours**: MCP servers don't change that often. 24 hours balances freshness vs cost.

**Why PostgreSQL**: We already have it. Redis would be overkill for this scale.

## Error Handling: When AI Fails

AI fails. A lot. Here's how we handle it:

```python
try:
    result = await self.analyze_repo(repo_url)
except json.JSONDecodeError:
    # AI returned non-JSON
    raise AnalysisError(
        message="AI analysis returned invalid format",
        details={"response": content},
        user_message="Analysis failed. Try again or contact support."
    )
except ValidationError as e:
    # Pydantic validation failed (missing required fields)
    raise AnalysisError(
        message="Analysis missing required fields",
        details={"errors": e.errors()},
        user_message="Incomplete analysis. The repository might not be an MCP server."
    )
except Exception as e:
    # Unexpected error
    logger.exception("Analysis failed", extra={"repo_url": repo_url})
    raise AnalysisError(
        message="Analysis failed unexpectedly",
        user_message="Something went wrong. Please try again."
    )
```

**User-facing errors are key**. "ValidationError: 'package' field missing" means nothing to users. "This repository might not be an MCP server" helps them understand.

## Real Examples: What It Extracts

### Example 1: TickTick MCP Server

Input: `https://github.com/hong-hao/mcp-ticktick`

Output:
```json
{
  "package": "@hong-hao/mcp-ticktick",
  "name": "TickTick MCP Server",
  "description": "MCP server for interacting with TickTick task management",
  "env_vars": [
    {
      "name": "TICKTICK_TOKEN",
      "description": "Your TickTick API access token",
      "required": true,
      "secret": true,
      "default": null
    }
  ],
  "tools": ["create_task", "list_tasks", "update_task", "delete_task"],
  "resources": ["ticktick://tasks"],
  "prompts": [],
  "notes": "Requires TickTick account and API token"
}
```

**Perfect extraction**. Frontend generates a form with one password field: "TICKTICK_TOKEN".

### Example 2: Filesystem MCP Server

Input: `https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem`

Output:
```json
{
  "package": "@modelcontextprotocol/server-filesystem",
  "name": "Filesystem MCP Server",
  "description": "MCP server for filesystem operations",
  "env_vars": [
    {
      "name": "ALLOWED_DIRECTORIES",
      "description": "Comma-separated list of allowed directories",
      "required": true,
      "secret": false,
      "default": null
    }
  ],
  "tools": ["read_file", "write_file", "list_directory", "create_directory"],
  "resources": ["file://"],
  "prompts": [],
  "notes": "Security: Only allows access to whitelisted directories"
}
```

**Also perfect**. Even extracted the security note.

### Example 3: Analysis Failure

Input: `https://github.com/user/random-repo` (not an MCP server)

Output: `422 Validation Error: Package name not found`

**Good failure mode**. User gets clear feedback that this isn't deployable.

## The Frontend Integration

When analysis succeeds, the frontend receives:

```typescript
const analysis = await analyzeRepo(repoUrl);

// Display results
<AnalysisResults>
  <PackageInfo package={analysis.package} />
  <ToolsList tools={analysis.tools} />
  <CredentialsForm envVars={analysis.env_vars} />
</AnalysisResults>
```

The `CredentialsForm` is dynamically generated (see Part 2) - no hardcoded forms, adapts to any MCP server.

## Performance in Numbers

After optimization:

- **Average analysis time**: 3.2 seconds
- **Token usage**: 4,000-8,000 tokens (vs 250k before optimization)
- **Cost per analysis**: ~$0.01 (Claude Haiku pricing)
- **Cache hit rate**: 73% (most users analyze popular repos)
- **Failure rate**: 8% (repos that aren't MCP servers)

**Cost savings from caching**: ~$0.007 per cached request. At 100 analyses/day: $0.70/day saved.

## What I Learned

### AI Excels At ✅
- **Structured extraction** from semi-structured docs (READMEs)
- **Pattern recognition** (identifying env var requirements)
- **Schema compliance** (when prompted correctly)

### AI Struggles With ❌
- **Ambiguous documentation** (poorly written READMEs)
- **Unconventional structures** (non-standard package.json)
- **Edge cases** (monorepos, non-npm packages)

### Human Judgment Required 🧠
- **Prompt design** - AI can't write its own prompts (yet)
- **Error handling** - What should happen when AI fails?
- **Cost optimization** - Limiting results, caching strategy
- **Security validation** - Is the extracted package name safe to execute?

## Up Next

The AI analysis engine works. We can extract MCP configuration from GitHub repos. Dynamic forms are generated.

But it all runs on localhost. Time to **deploy to production**.

That's Part 4: First Deployment - Fly.io Adventures.

Spoiler: It doesn't go smoothly.

---

**Key Commits**:
- `af021a1` - Frontend/backend flow implementation
- `02f9346` - Comprehensive API hardening and analysis improvements
- `d0766bf` - Fix analysis token overflow with `max_results: 2`

**Related Files**:
- `backend/app/services/analysis_service.py` - Analysis implementation
- `backend/app/prompts/analysis_prompt.py` - The actual prompt
- `backend/app/services/cache_service.py` - Caching logic

**Next Post**: [Part 4: First Deployment - Fly.io Adventures](04-first-deployment-flyio.md)
