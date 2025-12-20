# Contributing to Catwalk Live

This project was built entirely using **AI-orchestrated development**. We welcome contributions from both traditional developers and AI orchestrators!

## Two Ways to Contribute

### Option A: Traditional Development (Write Code Yourself)

1. Fork the repository
2. Set up local environment (see [SETUP.md](SETUP.md))
3. Write code following our style guides
4. Submit a Pull Request

### Option B: AI-Orchestrated Development (Recommended!)

1. Fork the repository
2. Use AI coding assistants (Claude Code, Cursor, ChatGPT, Gemini) to generate code
3. Follow the **AI Orchestration Workflow** (see below)
4. Submit a Pull Request with context about your AI methodology

**We explicitly encourage AI-assisted contributions!** This project is a case study in AI orchestration, and we want to see different approaches.

## AI Orchestration Workflow (How This Project Was Built)

If you're using AI to contribute, here's the proven methodology:

### 1. Read the Context Files First

**CRITICAL**: AI assistants need context. Feed them these files:

- **`AGENTS.md`** - AI agent specifications & system prompts
- **`context/ARCHITECTURE.md`** - System design decisions
- **`context/CURRENT_STATUS.md`** - Current project state
- **`CLAUDE.md`** - Deployment lessons & pitfalls
- **`AI_ORCHESTRATION.md`** - Full AI development methodology

**Pro tip**: Use these as system prompts or paste them into your AI assistant's context window.

### 2. Plan Before Implementing

- Use AI planning tools (Claude's "Plan Mode", ChatGPT with o1, etc.)
- Cross-validate with multiple AI models (Claude, GPT-4, Gemini)
- Document your plan in markdown before writing code

### 3. Implement with Quality Gates

- Generate code with your AI assistant
- Run automated checks:
  - Frontend: `bun run typecheck && bun run lint && bun run test`
  - Backend: `pytest && ruff check .`
- Fix issues iteratively with AI

### 4. Use Automated PR Review Agents

When you submit a PR, these agents will automatically review:

- **CodeRabbit** - Security vulnerabilities (SQL injection, XSS, secrets)
- **Qodo** - Edge cases, error handling, input validation
- **Gemini Code Assist** - Code quality, best practices
- **Greptile** - Integration consistency, breaking changes

**Feed their comments back to your AI assistant** and iterate!

### 5. Document Your AI Workflow (Optional but Appreciated)

In your PR description, share:

- Which AI tools you used (Claude Code, Cursor, ChatGPT, etc.)
- Your prompt engineering strategy
- Challenges you encountered with AI
- What worked well vs what needed manual intervention

**Why?** This helps us learn from different AI orchestration approaches!

## Development Process

## Code Quality Standards (REQUIRED)

### Frontend

```bash
bun run typecheck    # TypeScript type checking (MUST pass)
bun run lint         # ESLint (MUST pass)
bun run test         # Vitest tests (SHOULD pass for affected code)
```

### Backend

```bash
pytest               # All tests (MUST pass)
ruff check .         # Linter (MUST pass, zero warnings)
ruff format .        # Auto-format (run before committing)
```

**ALL quality checks must pass before merging.** No exceptions.

If you're using AI and it generates code that fails checks, **feed the error messages back to the AI and iterate** until all checks pass.

## Expectations for Contributors

### What We Expect From YOU:

1. **✅ Quality over speed** - Take time to understand the codebase
2. **✅ Tests for critical paths** - If you change logic, add/update tests
3. **✅ Clear PR descriptions** - Explain what changed and why
4. **✅ Responsiveness** - Address review comments within 7 days
5. **✅ Respect the architecture** - Don't introduce breaking changes without discussion

### What YOU Can Expect From US:

1. **✅ Code review within 48 hours** (automated agents are instant!)
2. **✅ Constructive feedback** - We'll help you improve, not just criticize
3. **✅ Merge within 7 days** if all checks pass and feedback is addressed
4. **✅ Recognition** - Contributors listed in releases and README
5. **✅ Learning opportunities** - We'll share AI orchestration tips if you're interested

## AI-Specific Guidelines

### If You're Using AI Tools:

**DO:**
- ✅ Validate AI-generated code before submitting
- ✅ Run all quality checks (type check, lint, test)
- ✅ Manually review diffs to understand what changed
- ✅ Share your AI methodology in PR descriptions (optional but cool!)
- ✅ Iterate with AI when automated reviewers flag issues

**DON'T:**
- ❌ Blindly copy-paste AI output without understanding it
- ❌ Submit PRs with failing tests or type errors
- ❌ Ignore automated review comments
- ❌ Use AI to bypass code quality standards

### Recommended AI Tools:

- **Claude Code** - Great for architecture and system-level thinking
- **Cursor** - Excellent for iterative development and refactoring
- **ChatGPT (GPT-4, o1)** - Good for problem-solving and planning
- **GitHub Copilot** - Useful for boilerplate and autocomplete
- **Gemini** - Strong at multi-file refactoring

**Mix and match!** The original project used Claude, Gemini, and Cursor together.

## What We're Looking For

- 🐛 **Bug fixes** - If you find an issue, please fix it and add a test
- ✨ **Feature enhancements** - New capabilities that fit the platform's vision
- 📚 **Documentation improvements** - Better explanations, examples, or guides
- 🧪 **Test coverage** - Adding tests for untested code paths
- 🎨 **UI/UX improvements** - Better user experience or visual design

## What We're NOT Looking For

- ❌ Major architectural rewrites without prior discussion
- ❌ Dependencies that conflict with MIT license
- ❌ Features that deviate from the "Vercel for MCP" vision
- ❌ Code without tests for critical paths

## Questions?

Open an issue for discussion before starting major work. We're friendly!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
