# Phase 6: Advanced Features
**Duration**: 4-6 weeks
**Priority**: P2 (Medium)
**Goal**: Support edge cases and advanced deployment scenarios

## Overview

After the core platform is solid (Phases 1-5), this phase adds advanced features for power users:
- **Version pinning**: Deploy specific package versions (not just latest)
- **OAuth credential flows**: Multi-step auth with callbacks
- **GitHub-only repos**: Support repos not published to npm/PyPI
- **Complex credentials**: JSON files, SSH keys, multi-field credentials

## Success Criteria

- ✅ 30% of deployments use version pinning
- ✅ OAuth flows work for 5+ common services
- ✅ GitHub-only repos deployable via `npx github:user/repo`
- ✅ Users can upload JSON credential files

## Implementation Checklist

### 1. Version Pinning

- [ ] **Update analysis to extract version**
  - [ ] Modify `backend/app/prompts/analysis_prompt.py`
  - [ ] Add `"version": "1.2.3"` to expected output
  - [ ] Default to `null` if version not specified

- [ ] **Add version to deployment schema**
  - [ ] Update `backend/app/schemas/deployment.py`
  - [ ] Add optional `version` field to DeploymentCreate

- [ ] **Validate version exists**
  - [ ] In `package_validator.py`, add `validate_npm_package_version(package, version)`
  - [ ] Check `https://registry.npmjs.org/{package}/{version}`
  - [ ] Return error if version doesn't exist

- [ ] **Use versioned package in deployment**
  - [ ] In `fly_deployment_service.py`:
    ```python
    if version:
        env["MCP_PACKAGE"] = f"{package}@{version}"
    else:
        env["MCP_PACKAGE"] = package  # Latest
    ```

- [ ] **Add version selector to frontend**
  - [ ] In `configure/page.tsx`, add version input (optional)
  - [ ] Show detected version from analysis as default

### 2. OAuth Credential Flows

- [ ] **Create OAuth router**
  - [ ] Create `backend/app/api/oauth.py`
  - [ ] Add `/oauth/{service}/authorize` endpoint (GET)
    - [ ] Redirect to OAuth provider
    - [ ] Store state in cache for CSRF protection
  - [ ] Add `/oauth/{service}/callback` endpoint (GET)
    - [ ] Verify state
    - [ ] Exchange code for token
    - [ ] Return token to frontend

- [ ] **Add OAuth configs**
  - [ ] Create `backend/app/oauth/configs.py`
  - [ ] Define configs for common services:
    - GitHub: client_id, client_secret, scopes
    - Google: similar
    - Others as needed

- [ ] **Frontend OAuth flow**
  - [ ] Add "Connect with GitHub" button in credential form
  - [ ] Open OAuth popup window
  - [ ] Listen for callback with token
  - [ ] Auto-fill credential field with token

### 3. GitHub-only Repository Support

- [ ] **Update analysis prompt**
  - [ ] Accept GitHub URLs as package names
  - [ ] Format: `"package": "github:user/repo"`

- [ ] **Validate GitHub repos**
  - [ ] In `package_validator.py`, add `validate_github_repo(url)`
  - [ ] Check repo exists via GitHub API
  - [ ] Return error if repo not found or not accessible

- [ ] **Support `npx github:user/repo`**
  - [ ] In `entrypoint.sh`, handle `github:` prefix:
    ```bash
    npm)
      if [[ "$MCP_PACKAGE" == github:* ]]; then
        echo "Installing from GitHub: $MCP_PACKAGE"
      fi
      exec mcp-proxy ... -- npx -y "$MCP_PACKAGE"
      ;;
    ```

### 4. Complex Credential Types

- [ ] **Add credential type to env var schema**
  - [ ] In analysis, extract `"type": "text|password|json|file"`
  - [ ] Default to "password" if secret=true, else "text"

- [ ] **Update form builder**
  - [ ] In `frontend/components/dynamic-form/FormBuilder.tsx`
  - [ ] Add field type handlers:
    ```typescript
    switch (field.type) {
      case "json":
        return <textarea placeholder="Paste JSON here" .../>;
      case "file":
        return <input type="file" accept=".pem,.json,.key" .../>;
      default:
        return <input type={field.secret ? "password" : "text"} .../>;
    }
    ```

- [ ] **Handle file uploads**
  - [ ] Convert file to base64 in frontend
  - [ ] Send as string in credential
  - [ ] Decode in backend before passing to container

### 5. Testing

- [ ] **Test version pinning**
  - [ ] Deploy TickTick@1.0.0 (if version exists)
  - [ ] Verify correct version installed in container

- [ ] **Test OAuth flow** (use GitHub as example)
  - [ ] Start OAuth flow
  - [ ] Complete authorization
  - [ ] Verify token received
  - [ ] Deploy with OAuth token

- [ ] **Test GitHub repo**
  - [ ] Deploy `github:modelcontextprotocol/servers`
  - [ ] Verify `npx github:...` works

- [ ] **Test JSON credential**
  - [ ] Upload service account JSON
  - [ ] Verify deployed correctly as env var

## Files to Create

- `backend/app/api/oauth.py` (NEW)
- `backend/app/oauth/configs.py` (NEW)
- `backend/tests/test_oauth.py` (NEW)

## Files to Modify

- `backend/app/prompts/analysis_prompt.py` (add version field)
- `backend/app/services/package_validator.py` (add version validation, GitHub validation)
- `backend/app/services/fly_deployment_service.py` (use versioned package)
- `backend/app/schemas/deployment.py` (add version field)
- `deploy/entrypoint.sh` (handle github: prefix)
- `frontend/components/dynamic-form/FormBuilder.tsx` (add field types)
- `frontend/app/configure/page.tsx` (add version input, OAuth buttons)

## Deployment Steps

1. Create feature branch
2. Implement version pinning
3. Implement OAuth flows (start with GitHub)
4. Implement GitHub-only repos
5. Implement complex credentials
6. Test each feature independently
7. Deploy to production
8. Create git tag `phase-6-complete`

## Next Steps

After Phase 6, the core platform is feature-complete. Proceed to **long-term vision** (marketplace, teams, edge, etc.).

See `future-vision.md` for Phases 7-14+.
