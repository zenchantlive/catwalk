---
title: "Part 9: Reflections - AI-Orchestrated Development"
series: "Catwalk Live Development Journey"
part: 9
date: 2025-12-27
updated: 2025-12-27
tags: [AI, reflections, methodology, lessons-learned, future]
reading_time: "18 min"
commits_covered: "215deaa...890c67a"
---

## The Journey in Numbers

December 11-23, 2025. **12 days. 86 commits. 0 lines of code written manually.**

**What was built**:
- Full-stack deployment platform
- Next.js 15 frontend (React 19, TailwindCSS 4)
- FastAPI backend (Python 3.12, async SQLAlchemy)
- PostgreSQL database (Fly.io)
- MCP Streamable HTTP implementation (2025-06-18 spec)
- Fly Machines API integration
- JWT authentication (NextAuth.js + custom backend)
- Package validation (npm + PyPI registries)
- Credential encryption (Fernet)
- Comprehensive test suite (51 tests, 89% coverage)
- Production deployment (Vercel + Fly.io)

**The result**: A working platform that deploys MCP servers as easily as deploying to Vercel.

**The method**: Strategic AI orchestration with rigorous human validation.

**The question**: Does this methodology actually work?

## The Central Thesis

**AI can build production systems - but only with the right structure.**

This isn't about "AI writes all the code." It's about **orchestrating multiple AI agents with clear specifications, quality gates, and human oversight**.

Here's what I learned actually works:

### What Worked: The Winning Patterns

#### 1. Prompt Refinement is 80% of Success

**Bad approach**: "Build me a deployment platform for MCP servers"

**Good approach**:
```
Build a platform that:
- Accepts GitHub URLs for MCP servers
- Uses Claude API (via OpenRouter) with web search to analyze repos
- Extracts: package name (npm/PyPI), env vars, tools/resources/prompts
- Generates dynamic credential forms based on extracted requirements
- Encrypts credentials with Fernet symmetric encryption (256-bit key)
- Stores deployments in PostgreSQL with async SQLAlchemy
- Validates package names against npm/PyPI registries (prevent command injection)
- Deploys to Fly.io Machines API with isolated Firecracker VMs
- Implements MCP Streamable HTTP transport (2025-06-18 spec)
- Exposes stable HTTPS endpoints for Claude Desktop

Tech constraints:
- Frontend: Next.js 15 (App Router), React 19, TypeScript 5+ (no 'any' types)
- Backend: FastAPI, Python 3.12, psycopg3 (NOT asyncpg), Pydantic 2.0
- All async (asyncio, async SQLAlchemy)
- Type-safe throughout
- Must pass ruff check with zero warnings

Success criteria:
- End-to-end MCP tool calling works
- Credentials never logged or exposed
- Package validation prevents command injection
- 90%+ test coverage
```

**The difference**: The detailed prompt produced production-quality code. The vague prompt produced a proof-of-concept that would need complete rewrites.

**Time investment**: 30 minutes refining prompts vs 10+ hours debugging vague AI output.

#### 2. Multi-AI Validation Prevents Blind Spots

Different AI models have different strengths. Cross-validation catches issues.

**Example: PostgreSQL driver choice**

| AI Model | Recommendation | Rationale |
|----------|----------------|-----------|
| GPT-4 | asyncpg | "Modern async driver, well-maintained" |
| Claude | psycopg3 | "Better SSL parameter support" |
| Gemini | psycopg3 | "More compatible with connection strings" |

**Consensus**: psycopg3 (2 out of 3)

**Result**: Correct choice. asyncpg failed with Fly.io's `sslmode` parameter.

**Pattern**: Where AI models agree → probably good design. Where they disagree → investigate carefully.

#### 3. Context Files Enable Multi-Session Consistency

AI has limited context windows. Without external memory, architectural decisions get forgotten across sessions.

**The solution**: Structured markdown files as "source of truth":

```
context/
├── CURRENT_STATUS.md     # Where we are, what's next
├── ARCHITECTURE.md       # System design decisions
├── TECH_STACK.md        # Technology choices + rationale
├── API_SPEC.md          # Endpoint documentation
└── CLAUDE.md            # Known pitfalls, lessons learned
```

**Example from CLAUDE.md**:
```markdown
## PostgreSQL Driver Issues

CRITICAL: Use psycopg3, NOT asyncpg.

Fly.io provides URLs like: postgres://user:pass@host?sslmode=disable
asyncpg does NOT support 'sslmode' parameter → crashes.

Solution: Use psycopg[binary]>=3.1.0 + URL transformer in config.py:
...
```

**Impact**: Without these files, AI tried asyncpg again in session 3. With the file, it immediately used psycopg3.

**The insight**: Context engineering is as important as prompt engineering.

#### 4. Automated Quality Gates Catch What Humans Miss

GitHub agent pipeline:
1. **CodeRabbit**: Security vulnerabilities (found command injection risk)
2. **Qodo**: Edge cases and error handling
3. **Gemini Code Assist**: Code quality and best practices
4. **Greptile**: Integration consistency

**Example: CodeRabbit caught command injection**

AI-generated code:
```python
env = {"MCP_PACKAGE": mcp_package}  # User input, unsanitized!
```

Exploit:
```python
mcp_package = "; rm -rf /"
# Executes: npx -y ; rm -rf /
```

**CodeRabbit flagged this** → I added package validation against registries.

**Human alone**: Might have missed this.
**AI alone**: Generated the vulnerability.
**AI + automated review**: Caught and fixed it.

### What Didn't Work: The Failure Modes

#### 1. AI Doesn't Think About Security

AI-generated code often has security holes:

- ❌ Command injection (user input → shell execution)
- ❌ Secrets in logs (`logger.info(deployment.dict())` logged credentials)
- ❌ CORS misconfiguration (`allow_origins=["*"]`)
- ❌ Missing access control on MCP endpoints

**Why**: AI is trained to make code **work**, not to make code **secure**.

**Solution**: Always run security-focused reviews. Use tools like CodeRabbit. Never trust AI with security-critical code.

#### 2. AI Struggles with Infrastructure Quirks

AI knows general patterns but fails at platform-specific details:

**Example: Fly.io private networking**

AI suggested:
```python
machine_url = f"http://{machine_id}.fly.dev/mcp"
```

**Problem**: `.fly.dev` is public DNS. MCP machines don't have public IPs.

**Correct**:
```python
machine_url = f"http://{machine_id}.vm.mcp-host.internal:8080/mcp"
```

**Why AI failed**: Fly.io's `.internal` DNS is specific to Fly's private network. Not common knowledge in training data.

**Solution**: Deep knowledge of infrastructure platforms still requires human expertise.

#### 3. AI Generates Incomplete Implementations

**Example: Authentication**

AI generated:
```typescript
async signIn({ user, account }) {
  // TODO: Sync user to backend database
  return true
}
```

**I shipped this.** Users could sign in, but backend had no record of them → 401 errors everywhere.

**Why**: AI knows authentication **patterns** but doesn't know **your specific architecture**.

**Solution**: Always verify TODOs are resolved. Never ship commented-out functionality.

#### 4. AI Can't Debug Across Systems

**The 401 authentication nightmare** (Part 7):
- Frontend generates JWT with `AUTH_SECRET`
- Backend verifies JWT with different `AUTH_SECRET`
- Error: "Invalid signature"

**AI's suggestion**: "Check if secrets match"

**Helpful, but not actionable.** AI can't:
- Check Fly.io secrets
- Compare `.env.local` with remote secrets
- Trace requests through multiple systems

**Human debugging required**:
1. Manually verify secrets match
2. Test each component separately
3. Create troubleshooting documentation
4. Fix the root cause (secret sync)

**The insight**: AI debugs single-system issues well. Multi-system integration failures need human investigation.

## The Skill Shift

Building Catwalk Live changed how I think about software development.

### Old Model: Writing Code

**Traditional developer**:
1. Understand requirements
2. Design architecture
3. **Write code line by line**
4. Debug and test
5. Deploy

**Bottleneck**: Step 3 (writing code). Slow, error-prone, tedious.

### New Model: Orchestrating AI

**AI-assisted developer**:
1. Understand requirements
2. Design architecture
3. **Craft detailed prompts**
4. **Validate AI-generated code**
5. **Orchestrate multiple AI agents**
6. Debug (with AI assistance)
7. Deploy

**Bottleneck shift**: From writing code → validating systems.

**Key skills now**:
- ✅ **Architectural thinking**: What should be built, why, and how?
- ✅ **Prompt engineering**: How to specify requirements precisely?
- ✅ **System validation**: Is this code safe? Does it handle edge cases?
- ✅ **Integration debugging**: Why are these systems not talking to each other?
- ✅ **Quality control**: Does this meet production standards?

**Skills becoming less critical**:
- ⬇️ Syntax memorization (AI knows all frameworks)
- ⬇️ Boilerplate generation (AI excels at this)
- ⬇️ CRUD implementation (AI generates correctly)
- ⬇️ API client code (AI reads OpenAPI specs)

### The Role Evolution

**I'm not a traditional coder anymore.** I'm a:

- **System Architect**: Designing how components fit together
- **Quality Engineer**: Validating AI output meets production standards
- **Prompt Engineer**: Specifying requirements with precision
- **Integration Specialist**: Debugging cross-system failures
- **AI Orchestrator**: Coordinating multiple AI agents to build systems

**Analogy**: From construction worker (building brick by brick) → construction manager (coordinating teams to build the structure).

## Lessons for Future AI-Assisted Projects

Based on 12 days and 86 commits, here's what I'd do again (and what I'd change):

### Do Again ✅

1. **Start with context files** (`AGENTS.md`, `ARCHITECTURE.md`, `CURRENT_STATUS.md`)
   - Write these BEFORE any code
   - Update them religiously
   - Treat as single source of truth

2. **Multi-AI validation**
   - Cross-check architecture decisions across GPT-4, Claude, Gemini
   - Where consensus → proceed confidently
   - Where disagreement → investigate deeply

3. **Automated review agents**
   - Add CodeRabbit, Qodo to every PR
   - Feed their comments back to implementing AI
   - Create iterative improvement loop

4. **Detailed prompts with constraints**
   - Specify tech stack versions
   - List security requirements explicitly
   - Define success criteria
   - Include example code patterns

5. **Incremental validation**
   - Deploy early and often
   - Test each component as it's built
   - Don't wait until "everything is ready"

### Do Differently ❌

1. **Write tests FIRST**
   - I waited until day 10 to write tests
   - This was a mistake
   - Test-driven development works with AI too

2. **Smaller, more frequent commits**
   - Some commits changed 20+ files
   - Made debugging harder
   - One feature per commit is better

3. **Security review at every stage**
   - I only ran security review at the end
   - Found critical issues late
   - Should have reviewed after each feature

4. **Database design upfront**
   - Changed schema 3 times
   - Migrations became messy
   - Spend more time designing schema before coding

5. **Document infrastructure decisions immediately**
   - Spent hours re-learning Fly.io private networking
   - Should have documented the first time
   - "Future me" would thank "past me"

## The Honest Assessment

**Can AI build production systems without human coding?**

**Answer: Yes, but...**

### What AI Can Do (Proven)

✅ Generate boilerplate (FastAPI routes, React components)
✅ Implement known patterns (CRUD, authentication, validation)
✅ Write database models and migrations
✅ Create API clients from OpenAPI specs
✅ Generate comprehensive test suites
✅ Follow specific architectural constraints
✅ Refactor code to improve readability

### What AI Cannot Do (Yet)

❌ Architectural decision-making (monolith vs microservices?)
❌ Security threat modeling (what could attackers exploit?)
❌ Infrastructure platform expertise (Fly.io quirks, AWS specifics)
❌ Business requirement interpretation (what does the user actually need?)
❌ Edge case discovery (what scenarios did we not think of?)
❌ Cross-system debugging (why is auth failing between frontend and backend?)
❌ Production trade-off evaluation (performance vs cost vs complexity?)

### What Humans Must Still Do

🧠 **System Architecture**: Design how components interact
🧠 **Security Validation**: Ensure code doesn't enable attacks
🧠 **Infrastructure Knowledge**: Understand platform-specific behavior
🧠 **Integration Debugging**: Solve multi-system failures
🧠 **Quality Assurance**: Validate code meets production standards
🧠 **Product Decisions**: Prioritize features, manage scope

**The insight**: AI is a powerful **amplifier** of developer productivity, not a **replacement** for developer judgment.

## The Future: Where This Goes

This project proved AI-orchestrated development can build production systems. But we're still early.

### Near Future (1-2 years)

**Expectation**: AI coding assistants become standard in every developer workflow.

**Changes**:
- IDEs integrate AI deeply (already happening: Cursor, Continue)
- AI agents handle full features (not just code snippets)
- Multi-agent systems become common (planning AI + implementation AI + review AI)
- Context management becomes critical skill

**Developer role shift**: Less "writing code" → more "validating systems"

### Medium Future (3-5 years)

**Expectation**: AI can build entire MVPs from specifications.

**Requirements**:
- Better architectural reasoning (AI makes design decisions)
- Improved security awareness (AI proactively hardens code)
- Infrastructure knowledge (AI understands platform specifics)
- Self-testing capability (AI writes comprehensive tests automatically)

**Developer role shift**: Focus on **what to build** (product) rather than **how to build it** (implementation).

### Long Future (5-10 years)

**Speculation**: AI builds complex systems with minimal human intervention.

**Open questions**:
- Can AI learn infrastructure quirks from documentation?
- Can AI reason about security threats like humans?
- Can AI debug emergent failures in distributed systems?
- Can AI make architectural trade-offs (cost vs performance vs complexity)?

**My intuition**: AI will get very good at **implementation** but humans will remain critical for **judgment calls**.

## The Meta-Lesson

This project was as much about **AI-orchestrated development methodology** as it was about building a deployment platform.

**The real deliverable**: A reproducible process for building production systems with AI.

**The methodology**:
1. Refine prompts to extreme specificity
2. Cross-validate architecture with multiple AI models
3. Create structured context files for consistency
4. Implement with AI (Claude Code, Cursor)
5. Review with automated AI agents (CodeRabbit, Qodo)
6. Debug integration issues (human expertise required)
7. Iterate based on feedback
8. Ship to production

**Why this matters**: Software development is entering a new era. Developers who learn to **orchestrate AI effectively** will have a massive productivity advantage.

**This blog series is the playbook.**

## Where Catwalk Live Goes Next

**Current state**: Production-ready platform with known gaps.

**What works**:
- End-to-end MCP deployment
- Streamable HTTP proxying
- Credential encryption
- Package validation
- User authentication
- Production infrastructure

**What's next (Phase 8+)**:
- Health monitoring loop (proactive failure detection)
- Deployment logs and metrics
- Cost tracking per deployment
- Vercel Functions as Fly.io alternative (edge deployment)
- Scale-to-zero for cost optimization
- Public MCP registry (discover and deploy)

**Long-term vision**: Make MCP server deployment as simple as `git push`.

## Final Thoughts

December 27, 2025. Looking back at 12 days:

**What surprised me**:
- How well multi-AI validation worked
- How bad AI is at security
- How critical context files became
- How much human judgment still matters

**What I'm proud of**:
- Shipping a working production system
- Documenting the methodology completely
- Proving AI orchestration can build real products
- Creating a reproducible process

**What I learned**:
- AI is a tool, not magic
- Prompt engineering is a critical skill
- Quality gates prevent bad AI code from shipping
- Humans make architectural and security decisions
- The skill is shifting from "coding" to "validating systems"

**The conclusion**: AI-orchestrated development **works** - but only when humans provide structure, validation, and judgment.

**This is the future of software development.** And it's already here.

---

## Resources

**This Project**:
- [GitHub Repository](https://github.com/zenchantlive/catwalk)
- [AI_ORCHESTRATION.md](../AI_ORCHESTRATION.md) - Complete methodology
- [AGENTS.md](../AGENTS.md) - AI agent specifications
- [context/](../context/) - Full knowledge base

**AI Tools Used**:
- Claude Code (Anthropic) - Primary implementation
- Cursor - Refactoring
- Google Gemini - Planning and validation
- ChatGPT (GPT-4) - Cross-validation
- CodeRabbit - Security review
- Qodo - Edge case detection

**Connect**:
- Email: jordanlive121@gmail.com
- Twitter: [@zenchantlive](https://twitter.com/zenchantlive)
- LinkedIn: [Jordan Hindo](https://linkedin.com/in/jordan-hindo)

---

**Thank you for reading this series.** I hope it inspires you to experiment with AI-orchestrated development.

**The future is being built by developers who learned to orchestrate AI. Will you be one of them?**

---

**Series Complete**: [Return to Overview](README.md)

**Previous Post**: [Part 8: Security Hardening & Production Ready](08-security-hardening-production.md)

**Share your experience**: If you build something using this methodology, I'd love to hear about it!
