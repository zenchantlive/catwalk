# Phase 1: Validation & Error Handling
**Duration**: 2 weeks
**Priority**: P0 (Blocking)
**Goal**: Prevent 80% of deployment failures before they happen

## Overview

Currently, deployments fail silently when:
- Package names don't exist in npm/PyPI
- Required credentials are missing
- Users see generic "Failed to create deployment" errors

This phase adds validation BEFORE creating Fly machines, with clear error messages guiding users to fix issues.

## Success Criteria

- ✅ 95% of valid npm packages deploy successfully
- ✅ Invalid packages rejected with clear error message
- ✅ Missing required credentials detected before deployment
- ✅ Users see actionable error messages (not generic "failed")

## Implementation Checklist

### 1. Package Validation Service

- [ ] **Create `backend/app/services/package_validator.py`**
  - [ ] Implement `validate_npm_package(package: str)` method
    - [ ] Handle scoped packages (`@user/package` → `@user%2Fpackage`)
    - [ ] Call `https://registry.npmjs.org/{package}`
    - [ ] Extract version from `dist-tags.latest`
    - [ ] Return `{"valid": bool, "error": str, "version": str}`
  - [ ] Implement `validate_python_package(package: str)` method
    - [ ] Call `https://pypi.org/pypi/{package}/json`
    - [ ] Extract version from `info.version`
    - [ ] Return same format as npm validation
  - [ ] Add timeout handling (5 seconds max)
  - [ ] Add exception handling for network errors

- [ ] **Write tests for package validation**
  - [ ] Test valid npm package (e.g., `@alexarevalo.ai/mcp-server-ticktick`)
  - [ ] Test invalid npm package (should return `valid: false`)
  - [ ] Test valid Python package (e.g., `mcp-server-git`)
  - [ ] Test invalid Python package
  - [ ] Test network timeout scenario
  - [ ] Test malformed package names

### 2. Credential Validation Service

- [ ] **Create `backend/app/services/credential_validator.py`**
  - [ ] Implement `validate_credentials()` method
  - [ ] Accept `provided_credentials` and `required_env_vars` params
  - [ ] Check each required env var is present and non-empty
  - [ ] Return `{"valid": bool, "errors": List[str]}`
  - [ ] Handle `env_` prefix stripping (e.g., `env_API_KEY` vs `API_KEY`)

- [ ] **Write tests for credential validation**
  - [ ] Test all required credentials provided → valid
  - [ ] Test missing required credential → invalid with error message
  - [ ] Test optional credential missing → valid
  - [ ] Test empty string credential → invalid
  - [ ] Test multiple missing credentials → list all in errors

### 3. Integration into Deployment Flow

- [ ] **Update `backend/app/api/deployments.py`** (around line 47-120)
  - [ ] Import validators
  - [ ] After extracting `package` from `mcp_config`:
    - [ ] Detect runtime (npm if starts with `@` or has `/`, else check for `.`)
    - [ ] Call appropriate validator (`validate_npm_package` or `validate_python_package`)
    - [ ] If validation fails, set `deployment.status = "failed"`
    - [ ] Store error in `deployment.error_message`
    - [ ] Raise `HTTPException(400, detail=validation["error"])`
    - [ ] If valid, store `runtime` and `version` in `mcp_config`
  - [ ] Before encrypting credentials:
    - [ ] Extract `required_env_vars` from `mcp_config.env_vars`
    - [ ] Call `credential_validator.validate_credentials()`
    - [ ] If validation fails, rollback transaction
    - [ ] Raise `HTTPException(400, detail={"errors": validation["errors"]})`

### 4. Enhanced Error Messages

- [ ] **Update error response format in `deployments.py`**
  - [ ] Create structured error response:
    ```python
    {
      "error": "error_code",
      "message": "Human-readable message",
      "deployment_id": "uuid",
      "package": "package_name",
      "help": "Actionable guidance"
    }
    ```
  - [ ] Implement `_get_error_help(error)` helper function
    - [ ] Match error patterns (connect, timeout, not found, permission)
    - [ ] Return contextual help text

- [ ] **Add error types**
  - [ ] `credential_validation_failed` - Missing/invalid credentials
  - [ ] `package_not_found` - Package doesn't exist
  - [ ] `package_validation_failed` - Network/registry error
  - [ ] `deployment_failed` - Generic error

### 5. Frontend Error Display

- [ ] **Update `frontend/app/configure/page.tsx`** (line 73-76)
  - [ ] Replace console.error with proper error state
  - [ ] Create `ErrorMessage` component
  - [ ] Display validation errors as list (if `errorDetail.errors` exists)
  - [ ] Display help text (if `errorDetail.help` exists)
  - [ ] Style with error colors (red badge, etc.)

- [ ] **Create `frontend/components/ErrorMessage.tsx`** (optional)
  - [ ] Accept `error` prop with structured error
  - [ ] Render different layouts based on error type
  - [ ] Show actionable guidance prominently

### 6. Testing & Validation

- [ ] **End-to-end testing**
  - [ ] Deploy TickTick (valid npm, valid credentials) → Should succeed
  - [ ] Deploy with invalid package name → Should fail with "not found" error
  - [ ] Deploy with missing TICKTICK_TOKEN → Should fail listing missing credential
  - [ ] Deploy Python server (e.g., mcp-server-git) → Should succeed
  - [ ] Check frontend displays errors correctly

- [ ] **Run test suite**
  ```bash
  cd backend
  pytest tests/test_package_validator.py -v
  pytest tests/test_credential_validator.py -v
  pytest tests/test_deployments.py -v
  ruff check .

  cd ../frontend
  bun run typecheck
  bun run lint
  ```

### 7. Documentation Updates

- [ ] **Update `context/CURRENT_STATUS.md`**
  - [ ] Move "package validation" from "What's NOT Working" to "What Works"
  - [ ] Add Phase 1 completion status
  - [ ] Document new error codes

- [ ] **Update `context/API_SPEC.md`** (if exists)
  - [ ] Document new error response format
  - [ ] Add validation error examples

## Files to Create

- `backend/app/services/package_validator.py` (NEW)
- `backend/app/services/credential_validator.py` (NEW)
- `backend/tests/test_package_validator.py` (NEW)
- `backend/tests/test_credential_validator.py` (NEW)
- `frontend/components/ErrorMessage.tsx` (NEW - optional)

## Files to Modify

- `backend/app/api/deployments.py` (lines 47-120)
- `frontend/app/configure/page.tsx` (lines 73-76)
- `context/CURRENT_STATUS.md`

## Example Code

### Package Validator

```python
# backend/app/services/package_validator.py
import httpx
from typing import Dict, Any

class PackageValidator:
    async def validate_npm_package(self, package: str) -> Dict[str, Any]:
        """Check if npm package exists."""
        encoded = package.replace("/", "%2F")
        url = f"https://registry.npmjs.org/{encoded}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "valid": True,
                        "error": None,
                        "version": data.get("dist-tags", {}).get("latest")
                    }
                elif response.status_code == 404:
                    return {
                        "valid": False,
                        "error": f"Package '{package}' not found in npm registry",
                        "version": None
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"npm registry error: {response.status_code}",
                        "version": None
                    }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate package: {str(e)}",
                "version": None
            }
```

### Deployment Integration

```python
# In backend/app/api/deployments.py (after line 48)
package = mcp_config.get("package")

if package:
    # Validate package exists
    validator = PackageValidator()

    # Detect runtime
    if package.startswith("@") or "/" in package:
        validation = await validator.validate_npm_package(package)
        runtime = "npm"
    elif "." in package or "_" in package:
        validation = await validator.validate_python_package(package)
        runtime = "python"
    else:
        deployment.status = "failed"
        deployment.error_message = f"Cannot determine runtime for package: {package}"
        await db.commit()
        raise HTTPException(400, detail=deployment.error_message)

    if not validation["valid"]:
        deployment.status = "failed"
        deployment.error_message = validation["error"]
        await db.commit()
        raise HTTPException(400, detail={
            "error": "package_not_found",
            "message": validation["error"],
            "package": package,
            "help": "Verify the package name is correct and published to npm/PyPI"
        })

    # Store validated info
    deployment.schedule_config["mcp_config"]["runtime"] = runtime
    deployment.schedule_config["mcp_config"]["version"] = validation["version"]
    await db.commit()
```

## Testing Scenarios

### Test 1: Valid npm package
```bash
curl -X POST https://catwalk-live-backend-dev.fly.dev/api/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TickTick Test",
    "schedule_config": {
      "mcp_config": {
        "package": "@alexarevalo.ai/mcp-server-ticktick",
        "env_vars": [{"name": "TICKTICK_TOKEN", "required": true}]
      }
    },
    "credentials": {
      "env_TICKTICK_TOKEN": "test_token"
    }
  }'

# Expected: 201 Created (deployment proceeds)
```

### Test 2: Invalid package
```bash
curl -X POST https://catwalk-live-backend-dev.fly.dev/api/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid Test",
    "schedule_config": {
      "mcp_config": {
        "package": "this-package-does-not-exist-xyz"
      }
    },
    "credentials": {}
  }'

# Expected: 400 Bad Request
# {
#   "error": "package_not_found",
#   "message": "Package 'this-package-does-not-exist-xyz' not found in npm registry",
#   "package": "this-package-does-not-exist-xyz",
#   "help": "Verify the package name is correct and published to npm/PyPI"
# }
```

### Test 3: Missing required credential
```bash
curl -X POST https://catwalk-live-backend-dev.fly.dev/api/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Missing Creds Test",
    "schedule_config": {
      "mcp_config": {
        "package": "@alexarevalo.ai/mcp-server-ticktick",
        "env_vars": [
          {"name": "TICKTICK_TOKEN", "required": true},
          {"name": "TICKTICK_USER", "required": true}
        ]
      }
    },
    "credentials": {
      "env_TICKTICK_TOKEN": "test_token"
    }
  }'

# Expected: 400 Bad Request
# {
#   "error": "credential_validation_failed",
#   "errors": ["Required credential 'TICKTICK_USER' is missing or empty"]
# }
```

## Risk Mitigation

### Risk: Private npm packages fail validation
**Solution**: Add "Skip validation" checkbox in frontend (advanced users only)
**Implementation**: Pass `skip_validation: true` in request, bypass validator

### Risk: npm/PyPI API rate limits
**Solution**: Cache validation results for 1 hour
**Implementation**: Add `@cache(ttl=3600)` decorator to validator methods

### Risk: False negatives (package exists but isn't MCP server)
**Solution**: Phase 2 health monitoring will catch this
**Note**: Validation only checks package existence, not MCP compatibility

## Deployment Steps

1. **Create feature branch**
   ```bash
   git checkout -b phase-1-validation
   ```

2. **Implement backend changes**
   ```bash
   cd backend
   # Create validators
   # Update deployments.py
   # Write tests
   pytest -v
   ruff check .
   ```

3. **Implement frontend changes**
   ```bash
   cd frontend
   # Update configure/page.tsx
   # Create ErrorMessage component
   bun run typecheck
   bun run lint
   ```

4. **Deploy to Fly.io**
   ```bash
   cd backend
   fly deploy --app catwalk-live-backend-dev
   fly logs --app catwalk-live-backend-dev  # Monitor for errors
   ```

5. **Test end-to-end**
   - Deploy valid server (TickTick)
   - Deploy invalid package
   - Deploy with missing credentials
   - Verify error messages in frontend

6. **Create git tag**
   ```bash
   git add .
   git commit -m "feat: add package and credential validation (Phase 1)"
   git tag phase-1-complete
   git push origin phase-1-validation
   git push origin phase-1-complete
   ```

## Next Phase

After Phase 1 is complete and validated, proceed to **Phase 2: Health Monitoring & Status**.

See `phase-2-monitoring.md` for details.
