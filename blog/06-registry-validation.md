---
title: "Part 6: Building the Registry & Validation Layer"
series: "Catwalk Live Development Journey"
part: 6
date: 2025-12-16
updated: 2025-12-27
tags: [security, validation, npm, pypi, registry]
reading_time: "13 min"
commits_covered: "e41576b...ec955e6"
---

## The Security Wake-Up Call

December 16, 2025. I'm proud. The platform works. Users can deploy MCP servers. Claude connects. Tools execute.

Then **CodeRabbit** (automated PR review agent) posts a comment:

> **HIGH SEVERITY**: Command injection vulnerability in deployment service.
>
> File: `backend/app/services/fly_deployment_service.py`
> Line: 47
>
> The `mcp_package` value from user input is passed directly to shell execution without validation. An attacker could inject shell commands.
>
> Example exploit:
> ```python
> mcp_package = "; rm -rf / #"
> # Executes: npx -y ; rm -rf / #
> ```
>
> **Recommendation**: Validate package names against npm/PyPI registries before deployment.

**Oh no.**

I tested it. CodeRabbit was right:

```python
# Current code (VULNERABLE):
env = {"MCP_PACKAGE": mcp_package}  # mcp_package = user input
# Machine runs: npx -y $MCP_PACKAGE

# If mcp_package = "; cat /etc/passwd #"
# Executes: npx -y ; cat /etc/passwd #
```

**The realization**: AI-generated code had a **critical security vulnerability**. And I almost shipped it to production.

**Lesson 1**: Never trust AI-generated code with security implications. Always validate.

## The Validation Strategy

To prevent command injection, we need to **validate package names before deployment**:

1. **Syntax validation**: Does it look like a valid package name?
2. **Registry validation**: Does it exist in npm or PyPI?
3. **Credential validation**: Does the user provide all required env vars?

If any validation fails, reject the deployment **before** creating a machine.

### Package Name Syntax

```python
# backend/app/services/package_validator.py
import re

class PackageValidator:
    """Validate package names before deployment"""

    # npm: @scope/package-name or package-name
    NPM_PATTERN = r'^(@[\w-]+\/)?[\w-]+(\.[\w-]+)*$'

    # PyPI: package-name (alphanumeric, hyphens, underscores)
    PYPI_PATTERN = r'^[\w-]+(\.[\w-]+)*$'

    @classmethod
    def validate_syntax(cls, package: str, runtime: str) -> bool:
        """
        Validate package name syntax.

        Args:
            package: Package name to validate
            runtime: 'npm' or 'python'

        Returns:
            True if syntax is valid

        Raises:
            ValueError if invalid
        """
        if runtime == "npm":
            if not re.match(cls.NPM_PATTERN, package):
                raise ValueError(
                    f"Invalid npm package name: {package}. "
                    "Expected format: 'package' or '@scope/package'"
                )
        elif runtime == "python":
            if not re.match(cls.PYPI_PATTERN, package):
                raise ValueError(
                    f"Invalid PyPI package name: {package}. "
                    "Expected format: 'package-name'"
                )
        else:
            raise ValueError(f"Unknown runtime: {runtime}")

        return True
```

**Why regex**: Whitelisting valid characters prevents shell metacharacters (`;`, `|`, `&`, etc.).

### Registry Validation

Syntax validation isn't enough. What if an attacker uses a valid-looking name that doesn't exist?

```
package: "@attacker/malicious-script"
```

This would fail during `npx` install, but **after** we've created a machine and stored credentials. Bad.

**Solution**: Check if the package exists in npm/PyPI **before** deployment.

```python
import httpx
from typing import Optional

class RegistryService:
    """Validate packages against npm and PyPI registries"""

    NPM_REGISTRY = "https://registry.npmjs.org"
    PYPI_REGISTRY = "https://pypi.org/pypi"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def validate_npm_package(self, package: str) -> bool:
        """
        Check if package exists in npm registry.

        Args:
            package: Package name (e.g., '@scope/package' or 'package')

        Returns:
            True if package exists

        Raises:
            ValidationError if package not found
        """
        url = f"{self.NPM_REGISTRY}/{package}"

        try:
            response = await self.client.get(url)

            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                raise ValidationError(
                    f"Package '{package}' not found in npm registry"
                )
            else:
                raise ValidationError(
                    f"npm registry error: {response.status_code}"
                )
        except httpx.TimeoutException:
            raise ValidationError("npm registry timeout")

    async def validate_pypi_package(self, package: str) -> bool:
        """Check if package exists in PyPI registry"""
        url = f"{self.PYPI_REGISTRY}/{package}/json"

        try:
            response = await self.client.get(url)

            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                raise ValidationError(
                    f"Package '{package}' not found in PyPI"
                )
            else:
                raise ValidationError(
                    f"PyPI error: {response.status_code}"
                )
        except httpx.TimeoutException:
            raise ValidationError("PyPI timeout")
```

**Why external validation**:
- npm and PyPI are authoritative sources
- If package doesn't exist, deployment will definitely fail
- Prevents wasted machine creation and credentials storage

### Credential Validation

Even if the package is valid, deployment will fail if required credentials are missing.

**Example**: TickTick MCP requires `TICKTICK_TOKEN`. If user doesn't provide it:

```
Deployment created ✓
Machine started ✓
MCP server starts... ERROR: TICKTICK_TOKEN not set
```

**User experience**: Terrible. They deployed, think it worked, then discover tools don't work.

**Solution**: Validate credentials against analysis schema **before** deployment.

```python
async def validate_credentials(
    self,
    credentials: Dict[str, str],
    analysis: AnalysisResult
) -> None:
    """
    Validate user-provided credentials against analysis schema.

    Raises:
        ValidationError if required credentials missing
    """
    required_vars = [
        env_var for env_var in analysis.env_vars
        if env_var.required
    ]

    missing = []
    for env_var in required_vars:
        if env_var.name not in credentials:
            missing.append(env_var.name)

    if missing:
        raise ValidationError(
            f"Missing required credentials: {', '.join(missing)}",
            details={"missing": missing}
        )

    # Optional: Validate credential formats
    for name, value in credentials.items():
        env_var = next(
            (ev for ev in analysis.env_vars if ev.name == name),
            None
        )

        if env_var and "URL" in name:
            # Validate URL format
            try:
                httpx.URL(value)
            except Exception:
                raise ValidationError(
                    f"Invalid URL for {name}: {value}"
                )
```

**Result**: Deployments only proceed if:
1. Package name syntax is valid
2. Package exists in registry
3. All required credentials are provided
4. Credential formats are correct

## The Glama Registry Integration

MCP servers are scattered across GitHub. How do users discover them?

**Enter Glama**: A community registry of MCP servers (like npm search, but for MCP).

**Integration**:

```python
# backend/app/services/registry_service.py
class RegistryService:
    """Search and discover MCP servers via Glama"""

    GLAMA_API = "https://glama.ai/api/mcp/servers"

    async def search_servers(self, query: str) -> List[MCPServerInfo]:
        """
        Search Glama registry for MCP servers.

        Args:
            query: Search query (e.g., "ticktick")

        Returns:
            List of MCP servers matching query
        """
        response = await self.client.get(
            self.GLAMA_API,
            params={"q": query, "limit": 20}
        )

        response.raise_for_status()
        data = response.json()

        return [
            MCPServerInfo(
                name=server["name"],
                description=server["description"],
                repo_url=server["repository"],
                package=server["package"],
                stars=server.get("stars", 0),
                verified=server.get("verified", False)
            )
            for server in data.get("servers", [])
        ]
```

**Frontend integration**:

```typescript
// frontend/app/discover/page.tsx
export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const [servers, setServers] = useState([]);

  const handleSearch = async () => {
    const results = await searchMCPServers(query);
    setServers(results);
  };

  return (
    <div>
      <SearchInput value={query} onChange={setQuery} onSubmit={handleSearch} />
      <ServerGrid servers={servers} />
    </div>
  );
}
```

**User flow**:
1. User searches "ticktick"
2. Glama returns MCP servers matching query
3. User clicks "Deploy" on a server
4. Analysis pre-filled from Glama data (faster than analyzing GitHub)
5. Deployment proceeds with validation

**Why this improves UX**: Users don't need to know GitHub URLs. Just search and deploy.

## Runtime Detection

Should users specify "npm" vs "python"? No. **Auto-detect** it.

```python
def detect_runtime(package: str) -> str:
    """
    Auto-detect runtime from package name.

    Rules:
    - Starts with '@': npm (scoped package)
    - Contains '/': npm (@scope/package)
    - Otherwise: Check both registries

    Returns:
        'npm' or 'python'
    """
    # Scoped packages are always npm
    if package.startswith('@') or '/' in package:
        return "npm"

    # Check both registries (concurrent)
    npm_task = validate_npm_package(package)
    pypi_task = validate_pypi_package(package)

    npm_exists, pypi_exists = await asyncio.gather(
        npm_task, pypi_task,
        return_exceptions=True
    )

    if isinstance(npm_exists, Exception) and isinstance(pypi_exists, Exception):
        raise ValidationError(f"Package '{package}' not found in npm or PyPI")

    # Prefer npm if exists in both (rare but possible)
    if not isinstance(npm_exists, Exception):
        return "npm"
    else:
        return "python"
```

**Edge case**: Some packages exist in both npm and PyPI (e.g., `chalk`). Default to npm.

## Deployment Flow with Validation

With validation in place, deployment flow becomes:

```python
@router.post("/api/deployments")
async def create_deployment(
    name: str,
    repo_url: str,
    credentials: Dict[str, str]
):
    # 1. Retrieve analysis from cache
    analysis = await analysis_service.get_cached(repo_url)
    if not analysis:
        raise HTTPException(400, "Analyze repository first")

    # 2. Validate package syntax
    package = analysis.package
    runtime = detect_runtime(package)
    package_validator.validate_syntax(package, runtime)

    # 3. Validate package exists in registry
    if runtime == "npm":
        await registry_service.validate_npm_package(package)
    else:
        await registry_service.validate_pypi_package(package)

    # 4. Validate credentials
    await validate_credentials(credentials, analysis)

    # 5. Create deployment record
    deployment = Deployment(
        name=name,
        repo_url=repo_url,
        schedule_config={"mcp_config": analysis.dict()},
        status="pending"
    )
    db.add(deployment)
    await db.commit()

    # 6. Encrypt credentials
    encrypted = credential_service.encrypt(credentials)
    credential_record = Credential(
        deployment_id=deployment.id,
        encrypted_data=encrypted
    )
    db.add(credential_record)
    await db.commit()

    # 7. Deploy to Fly.io (background task)
    background_tasks.add_task(
        fly_service.create_machine,
        deployment.id,
        package,
        credentials
    )

    return deployment
```

**Benefits**:
- Validation happens **before** deployment
- Clear error messages at each step
- No wasted machine creation
- No credentials stored for invalid packages

## Error Messages: User-Facing vs Internal

**Internal error** (before):
```
ValidationError: regex pattern '^(@[\w-]+\/)?[\w-]+(\.[\w-]+)*$' did not match input '; rm -rf /'
```

**User-facing error** (after):
```json
{
  "error": "invalid_package_name",
  "message": "The package name contains invalid characters. Package names can only contain letters, numbers, hyphens, and underscores.",
  "details": {
    "package": "; rm -rf /",
    "allowed_format": "'package-name' or '@scope/package-name'"
  }
}
```

**Why better UX**: Users understand the problem and how to fix it.

## Security Review: CodeRabbit's Feedback

After implementing validation, CodeRabbit reviewed again:

✅ **RESOLVED**: Command injection vulnerability
- Package names validated with regex whitelist
- Registry validation prevents non-existent packages
- Credential validation prevents runtime errors

⚠️ **NEW ISSUE**: Concurrency race condition in registry service

> Multiple concurrent requests to the same package can cause duplicate validation requests. Consider caching validation results.

**The fix**:

```python
from functools import lru_cache

class RegistryService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._cache = {}  # In-memory cache
        self._cache_ttl = 300  # 5 minutes

    async def validate_npm_package(self, package: str) -> bool:
        # Check cache first
        if package in self._cache:
            cached_at, result = self._cache[package]
            if time.time() - cached_at < self._cache_ttl:
                return result

        # Validate
        result = await self._validate_npm_package_uncached(package)

        # Cache result
        self._cache[package] = (time.time(), result)
        return result
```

**Result**: Validation requests reduced by 80% (most users deploy popular packages).

## What I Learned

### Where AI Helped ✅
- Regex patterns for package name validation
- HTTP client setup for registry APIs
- Error message structuring

### Where AI Failed ❌
- **Didn't think about security** - AI generated the vulnerable code
- **Didn't consider concurrency** - Race conditions in validation
- **Over-complicated** - AI suggested database for caching (overkill)

### Human Expertise Required 🧠
- **Threat modeling**: What could go wrong?
- **Security validation**: Is this code safe to execute?
- **UX decisions**: How should validation errors appear?
- **Performance**: Do we need caching? Where?

**The pattern**: AI writes code. Humans think about what the code **enables attackers to do**.

## Up Next

The platform is now secure:
- ✅ Package names validated
- ✅ Registry checks prevent non-existent packages
- ✅ Credentials validated before deployment
- ✅ Clear error messages

But there's another problem: **Users can't actually access the platform**.

There's no authentication. No user accounts. No way to manage API keys.

Time to build **authentication**.

That's Part 7: The Authentication Nightmare.

Spoiler: This one nearly broke me.

---

**Key Commits**:
- `e41576b` - Introduce Glama MCP registry search and dynamic form generation
- `ec955e6` - Add credential and package validation services
- `7c2fa06` - Implement registry service and API

**Related Files**:
- `backend/app/services/package_validator.py` - Package name validation
- `backend/app/services/registry_service.py` - npm/PyPI validation
- `backend/app/api/deployments.py` - Validation integration

**Security Resources**:
- CodeRabbit security review comments
- OWASP Top 10: Injection vulnerabilities

**Next Post**: [Part 7: The Authentication Nightmare](07-authentication-crisis.md)
