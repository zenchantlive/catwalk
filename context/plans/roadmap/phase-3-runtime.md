# Phase 3: Multi-Runtime Support (Python + npm)
**Duration**: 2-3 weeks
**Priority**: P0 (Blocking)
**Goal**: Support Python MCP servers (covers 80% of Glama registry)

## Overview

Currently, the platform only supports npm packages via hardcoded `npx -y $MCP_PACKAGE` in Dockerfile.

This excludes:
- Python MCP servers (mcp-server-git, mcp-server-postgres, mcp-server-sqlite, etc.)
- Custom run commands
- GitHub-only repos

This phase adds unified runtime support through:
- Enhanced Dockerfile (Node.js + Python in single image)
- Runtime detection from package analysis
- Entrypoint script for dynamic command selection

## Success Criteria

- ✅ 85% of Python MCP servers deploy successfully
- ✅ Runtime auto-detected from package format
- ✅ Both npm and Python packages work in production
- ✅ Dockerfile builds successfully on Fly.io

## Implementation Checklist

### 1. Enhanced Dockerfile

- [ ] **Rewrite `deploy/Dockerfile`**
  - [ ] Start with `FROM python:3.12-slim`
  - [ ] Install Node.js 20:
    ```dockerfile
    RUN apt-get update && \
        apt-get install -y curl && \
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
        apt-get install -y nodejs && \
        rm -rf /var/lib/apt/lists/*
    ```
  - [ ] Install mcp-proxy: `RUN pip install "mcp-proxy>=0.10.0"`
  - [ ] Copy entrypoint script: `COPY entrypoint.sh /app/`
  - [ ] Make executable: `RUN chmod +x /app/entrypoint.sh`
  - [ ] Set CMD: `CMD ["/app/entrypoint.sh"]`

- [ ] **Test Dockerfile locally**
  ```bash
  cd deploy
  docker build -t catwalk-mcp-test .
  docker run -e MCP_RUNTIME=npm -e MCP_PACKAGE=@modelcontextprotocol/server-memory catwalk-mcp-test
  # Should start successfully
  ```

### 2. Entrypoint Script

- [ ] **Create `deploy/entrypoint.sh`**
  - [ ] Add shebang: `#!/bin/sh`
  - [ ] Add `set -e` for error handling
  - [ ] Validate `MCP_RUNTIME` is set
  - [ ] Validate `MCP_PACKAGE` is set (unless runtime=custom)
  - [ ] Implement runtime selection:
    ```bash
    case "$MCP_RUNTIME" in
      npm)
        echo "Starting npm package: $MCP_PACKAGE"
        exec mcp-proxy --host=:: --port=8080 --pass-environment -- npx -y "$MCP_PACKAGE"
        ;;
      python)
        echo "Starting Python module: $MCP_PACKAGE"
        pip install --no-cache-dir "$MCP_PACKAGE" || true
        exec mcp-proxy --host=:: --port=8080 --pass-environment -- python -m "$MCP_PACKAGE"
        ;;
      custom)
        echo "Starting custom command: $MCP_COMMAND"
        exec mcp-proxy --host=:: --port=8080 --pass-environment -- sh -c "$MCP_COMMAND"
        ;;
      *)
        echo "Error: Invalid MCP_RUNTIME=$MCP_RUNTIME"
        exit 1
        ;;
    esac
    ```

- [ ] **Test entrypoint script**
  ```bash
  # Test npm runtime
  docker run -e MCP_RUNTIME=npm -e MCP_PACKAGE=@modelcontextprotocol/server-memory catwalk-mcp-test

  # Test Python runtime
  docker run -e MCP_RUNTIME=python -e MCP_PACKAGE=mcp-server-git catwalk-mcp-test

  # Test invalid runtime
  docker run -e MCP_RUNTIME=invalid catwalk-mcp-test
  # Should exit with error
  ```

### 3. Runtime Detection in Analysis

- [ ] **Update `backend/app/prompts/analysis_prompt.py`**
  - [ ] Add "runtime" field to expected output:
    ```python
    "runtime": "string (npm, python, or custom)",
    ```
  - [ ] Update instructions to check package.json or setup.py
  - [ ] Emphasize runtime detection importance

- [ ] **Test analysis with Python repos**
  ```bash
  curl -X POST /api/analyze -d '{"repo_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/git"}'
  # Should return runtime: "python"
  ```

### 4. FlyDeploymentService Runtime Support

- [ ] **Update `backend/app/services/fly_deployment_service.py`** (line 64-68)
  - [ ] Extract runtime from mcp_config:
    ```python
    runtime = mcp_config.get("runtime", "npm")  # Default npm for backwards compat
    ```
  - [ ] Add runtime to environment variables:
    ```python
    env["MCP_RUNTIME"] = runtime
    env["MCP_PACKAGE"] = package
    ```
  - [ ] For custom runtime, add MCP_COMMAND:
    ```python
    if runtime == "custom":
        env["MCP_COMMAND"] = mcp_config.get("run_command", "")
    ```

- [ ] **Test Fly machine creation**
  ```bash
  # Check that MCP_RUNTIME is set in machine env
  fly machine list --app <your-mcp-app>
  fly machine show {machine_id}
  # Verify env vars include MCP_RUNTIME
  ```

### 5. Frontend Runtime Indicator

- [ ] **Create `frontend/components/RuntimeBadge.tsx`**
  - [ ] Accept `runtime` prop
  - [ ] Define colors and icons:
    ```typescript
    const styles = {
      npm: { bg: "bg-red-500", icon: "📦" },
      python: { bg: "bg-blue-500", icon: "🐍" },
      custom: { bg: "bg-purple-500", icon: "⚙️" }
    };
    ```
  - [ ] Render badge with icon and runtime name

- [ ] **Update `frontend/components/DeploymentCard.tsx`**
  - [ ] Import `RuntimeBadge`
  - [ ] Extract runtime from `deployment.schedule_config.mcp_config.runtime`
  - [ ] Render `<RuntimeBadge runtime={runtime} />` next to status

### 6. Python Package Validation

- [ ] **Verify `PackageValidator.validate_python_package` exists** (from Phase 1)
  - [ ] Should check `https://pypi.org/pypi/{package}/json`
  - [ ] Should return same format as npm validation

- [ ] **Update deployment validation** (in `deployments.py`)
  - [ ] For Python packages, call `validate_python_package()`
  - [ ] Detect runtime from package format:
    ```python
    if package.startswith("@") or "/" in package:
        runtime = "npm"
    elif "." in package or "_" in package:
        runtime = "python"
    else:
        runtime = "npm"  # Default
    ```

### 7. Docker Image Build & Deployment

- [ ] **Build and push new Docker image**
  ```bash
  cd deploy
  docker build -t registry.fly.io/<your-mcp-app>:unified .
  docker push registry.fly.io/<your-mcp-app>:unified
  ```

- [ ] **Update Fly.io secret**
  ```bash
  fly secrets set FLY_MCP_IMAGE=registry.fly.io/<your-mcp-app>:unified \
    --app <your-backend-app>
  ```

- [ ] **Verify existing deployments still work**
  - [ ] Test TickTick (npm) deployment
  - [ ] Ensure backward compatibility

### 8. .gitattributes for Line Endings

- [ ] **Create/update `.gitattributes`** (in repository root)
  ```
  *.sh text eol=lf
  ```
  - [ ] Ensures entrypoint.sh always has LF line endings
  - [ ] Prevents CRLF issues on Windows

- [ ] **Verify line endings**
  ```bash
  file deploy/entrypoint.sh
  # Should show: "shell script, ASCII text executable"
  # NOT: "shell script, ASCII text executable, with CRLF line terminators"
  ```

### 9. Testing & Validation

- [ ] **End-to-end testing - npm packages**
  - [ ] Deploy TickTick (@alexarevalo.ai/mcp-server-ticktick)
  - [ ] Deploy filesystem (@modelcontextprotocol/server-filesystem)
  - [ ] Verify both work correctly

- [ ] **End-to-end testing - Python packages**
  - [ ] Deploy git server (mcp-server-git)
  - [ ] Deploy sqlite server (mcp-server-sqlite)
  - [ ] Verify both install and start correctly

- [ ] **Check container logs**
  ```bash
  # For Python deployment
  fly logs --app catwalk-live-mcp-{deployment-id} | grep "Starting Python"
  # Should see: "Starting Python module: mcp-server-git"

  # For npm deployment
  fly logs --app catwalk-live-mcp-{deployment-id} | grep "Starting npm"
  # Should see: "Starting npm package: @alexarevalo.ai/mcp-server-ticktick"
  ```

- [ ] **Run test suite**
  ```bash
  cd backend
  pytest -v
  ruff check .

  cd ../frontend
  bun run typecheck
  bun run lint
  ```

### 10. Documentation Updates

- [ ] **Update `context/CURRENT_STATUS.md`**
  - [ ] Add "Python MCP servers" to "What Works"
  - [ ] Update Phase 3 completion status
  - [ ] Document runtime support

- [ ] **Update `context/TECH_STACK.md`** (if exists)
  - [ ] Add runtime support details
  - [ ] Document Docker image composition

## Files to Create

- `deploy/entrypoint.sh` (NEW)
- `.gitattributes` (NEW or UPDATE)
- `frontend/components/RuntimeBadge.tsx` (NEW)

## Files to Modify

- `deploy/Dockerfile` (complete rewrite)
- `backend/app/prompts/analysis_prompt.py` (add runtime field)
- `backend/app/services/fly_deployment_service.py` (add runtime env vars)
- `frontend/components/DeploymentCard.tsx` (add runtime badge)

## Example Code

### Dockerfile

```dockerfile
# deploy/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Node.js 20 for npm packages
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install mcp-proxy
RUN pip install --no-cache-dir "mcp-proxy>=0.10.0"

# Copy and set up entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
```

### Entrypoint Script

```bash
#!/bin/sh
set -e

# Validate required environment variables
if [ -z "$MCP_RUNTIME" ]; then
    echo "Error: MCP_RUNTIME environment variable is required"
    exit 1
fi

if [ -z "$MCP_PACKAGE" ] && [ "$MCP_RUNTIME" != "custom" ]; then
    echo "Error: MCP_PACKAGE environment variable is required"
    exit 1
fi

# Runtime selection
case "$MCP_RUNTIME" in
  npm)
    echo "Starting npm package: $MCP_PACKAGE"
    exec mcp-proxy --host=:: --port=8080 --pass-environment -- npx -y "$MCP_PACKAGE"
    ;;
  python)
    echo "Starting Python module: $MCP_PACKAGE"
    # Install package if not already present
    pip install --no-cache-dir "$MCP_PACKAGE" || true
    exec mcp-proxy --host=:: --port=8080 --pass-environment -- python -m "$MCP_PACKAGE"
    ;;
  custom)
    if [ -z "$MCP_COMMAND" ]; then
        echo "Error: MCP_COMMAND required for custom runtime"
        exit 1
    fi
    echo "Starting custom command: $MCP_COMMAND"
    exec mcp-proxy --host=:: --port=8080 --pass-environment -- sh -c "$MCP_COMMAND"
    ;;
  *)
    echo "Error: Invalid MCP_RUNTIME=$MCP_RUNTIME (must be npm, python, or custom)"
    exit 1
    ;;
esac
```

## Testing Scenarios

### Test 1: npm package (TickTick)
```bash
# Deploy via frontend or API
{
  "name": "TickTick npm",
  "schedule_config": {
    "mcp_config": {
      "package": "@alexarevalo.ai/mcp-server-ticktick",
      "runtime": "npm"
    }
  },
  "credentials": {"env_TICKTICK_TOKEN": "..."}
}

# Expected container logs:
# "Starting npm package: @alexarevalo.ai/mcp-server-ticktick"
# "mcp-proxy listening on [::]:8080"
```

### Test 2: Python package (git server)
```bash
{
  "name": "Git Python",
  "schedule_config": {
    "mcp_config": {
      "package": "mcp-server-git",
      "runtime": "python"
    }
  },
  "credentials": {}
}

# Expected container logs:
# "Starting Python module: mcp-server-git"
# "Collecting mcp-server-git..."
# "mcp-proxy listening on [::]:8080"
```

### Test 3: Invalid runtime
```bash
{
  "schedule_config": {
    "mcp_config": {
      "package": "test",
      "runtime": "java"  # Invalid
    }
  }
}

# Expected container logs:
# "Error: Invalid MCP_RUNTIME=java"
# Container should exit with code 1
```

## Risk Mitigation

### Risk: Larger Docker image size
**Impact**: ~500MB (Node + Python) vs ~200MB (npm only)
**Mitigation**: Future optimization with multi-stage builds
**Acceptable**: For MVP, simplicity > size

### Risk: CRLF line endings break entrypoint.sh
**Mitigation**: Add .gitattributes rule for `*.sh text eol=lf`
**Validation**: Test on Windows machine before deployment

### Risk: pip install fails during container startup
**Mitigation**: `pip install ... || true` allows container to start
**Detection**: Health monitor will mark deployment unhealthy if server doesn't start

### Risk: Python version incompatibility
**Mitigation**: Use Python 3.12 (latest stable)
**Future**: Allow users to specify Python version

## Deployment Steps

1. **Create feature branch**
   ```bash
   git checkout -b phase-3-runtime
   ```

2. **Implement changes**
   ```bash
   # Create entrypoint.sh
   # Update Dockerfile
   # Update analysis prompt
   # Update FlyDeploymentService
   # Create .gitattributes
   ```

3. **Build and test Docker image locally**
   ```bash
   cd deploy
   docker build -t catwalk-mcp-test .
   # Test npm runtime
   docker run -e MCP_RUNTIME=npm -e MCP_PACKAGE=@modelcontextprotocol/server-memory catwalk-mcp-test
   # Test Python runtime
   docker run -e MCP_RUNTIME=python -e MCP_PACKAGE=mcp-server-git catwalk-mcp-test
   ```

4. **Push image to Fly.io registry**
   ```bash
   docker tag catwalk-mcp-test registry.fly.io/<your-mcp-app>:unified
   docker push registry.fly.io/<your-mcp-app>:unified
   ```

5. **Update backend secret**
   ```bash
   fly secrets set FLY_MCP_IMAGE=registry.fly.io/<your-mcp-app>:unified --app <your-backend-app>
   ```

6. **Deploy backend**
   ```bash
   cd backend
   fly deploy --app <your-backend-app>
   ```

7. **Test end-to-end**
   - Deploy npm server (TickTick)
   - Deploy Python server (git)
   - Verify both work in Claude

8. **Create git tag**
   ```bash
   git add .
   git commit -m "feat: add multi-runtime support (npm + Python) (Phase 3)"
   git tag phase-3-complete
   git push origin phase-3-runtime
   git push origin phase-3-complete
   ```

## Next Phase

After Phase 3 is complete and validated, proceed to **Phase 4: Observability (Container Logs)**.

See `phase-4-observability.md` for details.
