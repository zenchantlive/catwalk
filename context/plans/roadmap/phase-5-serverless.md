# Phase 5: Serverless & Cost Optimization
**Duration**: 3-4 weeks
**Priority**: P1 (High)
**Goal**: 70% cost reduction through scale-to-zero machines

## Overview

MCP servers are typically used intermittently (user asks Claude → tool call → idle). Currently, all Fly machines run 24/7 (~$1.94/month each). This phase implements Fly.io's scale-to-zero feature to:
- Auto-stop machines when idle
- Auto-wake on incoming requests
- Reduce costs by 70-90% for idle deployments

## Success Criteria

- ✅ 70-90% cost reduction for idle deployments
- ✅ Cold start time < 10 seconds (P95)
- ✅ Health monitor distinguishes "stopped" vs "unhealthy"
- ✅ Users understand serverless behavior (not perceived as "broken")

## Implementation Checklist

### 1. Serverless Fly Machine Configuration

- [ ] **Update `backend/app/services/fly_deployment_service.py`** (line 70-86)
  - [ ] Add services configuration to machine config:
    ```python
    config = {
        "config": {
            "image": self.image,
            "guest": {...},
            "env": env,
            "restart": {"policy": "always"},
            # NEW: Serverless configuration
            "services": [{
                "protocol": "tcp",
                "internal_port": 8080,
                "auto_stop_machines": "stop",      # Scale to zero
                "auto_start_machines": True,       # Wake on request
                "min_machines_running": 0,         # Allow zero
                "concurrency": {
                    "type": "requests",
                    "hard_limit": 10               # Max concurrent requests
                }
            }]
        }
    }
    ```

- [ ] **Test serverless configuration**
  - [ ] Deploy test server
  - [ ] Wait 5 minutes (default idle timeout)
  - [ ] Check machine state: `fly machine list --app {app_name}`
  - [ ] Expected: Machine state = "stopped"

### 2. Cold Start Optimization

- [ ] **Pre-cache common packages in Dockerfile**
  - [ ] Update `deploy/Dockerfile`:
    ```dockerfile
    # After mcp-proxy install, pre-install popular packages
    RUN npm install -g \
        @modelcontextprotocol/server-filesystem \
        @modelcontextprotocol/server-github \
        @modelcontextprotocol/server-memory \
        @alexarevalo.ai/mcp-server-ticktick

    RUN pip install --no-cache-dir \
        mcp-server-git \
        mcp-server-time \
        mcp-server-sqlite
    ```
  - [ ] Rebuild and push image

- [ ] **Add warm-up request after machine creation**
  - [ ] In `deployments.py` after machine creation:
    ```python
    if machine_id:
        # Send warm-up request to pre-populate cache
        await send_warmup_request(machine_id)

        # Then wait for health
        health_ok = await wait_for_health(machine_id, timeout=60)
    ```
  - [ ] Implement `send_warmup_request()`:
    ```python
    async def send_warmup_request(machine_id: str):
        machine_url = f"http://{machine_id}.vm.{app}.internal:8080/mcp"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    machine_url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                    headers={"Accept": "application/json"}
                )
        except Exception as e:
            logger.warning(f"Warmup request failed: {e}")
    ```

### 3. Health Monitor Serverless Adaptation

- [ ] **Update `backend/app/services/health_monitor.py`**
  - [ ] Modify `_check_deployment_health()` to handle stopped machines:
    ```python
    except httpx.ConnectError:
        # Query Fly API to check machine state
        machine_info = await fly_service.get_machine(deployment.machine_id)

        if machine_info and machine_info.get("state") == "stopped":
            # Normal serverless behavior
            if deployment.status != DeploymentStatus.STOPPED:
                deployment.status = DeploymentStatus.STOPPED
                await db.commit()
        else:
            # Actually unhealthy
            if deployment.status != DeploymentStatus.UNHEALTHY:
                deployment.status = DeploymentStatus.UNHEALTHY
                deployment.error_message = "Machine unreachable"
                await db.commit()
    ```

- [ ] **Test health monitor with stopped machine**
  - [ ] Deploy server, wait for "running"
  - [ ] Wait 5+ minutes for auto-stop
  - [ ] Check status becomes "stopped" (not "unhealthy")

### 4. Frontend Cold Start Indicator

- [ ] **Update `frontend/components/StatusBadge.tsx`**
  - [ ] Add tooltip for "stopped" status:
    ```typescript
    {status === "stopped" && (
        <span className="text-xs text-gray-400 ml-2">
            (will wake on next request)
        </span>
    )}
    ```

- [ ] **Add cold start progress indicator** (optional)
  - [ ] Show "Waking server..." during first request after idle
  - [ ] Estimated time: "5-10 seconds"

### 5. Cost Analytics Dashboard

- [ ] **Create `frontend/components/CostDashboard.tsx`**
  - [ ] Calculate estimated monthly cost:
    ```typescript
    const calculateCost = () => {
        let total = 0;
        for (const d of deployments) {
            if (d.status === "running") {
                total += 1.94;  // Always-on cost
            } else if (d.status === "stopped") {
                total += 0.05;  // Minimal idle cost
            }
        }
        return total.toFixed(2);
    };
    ```
  - [ ] Display:
    - Total estimated monthly cost
    - Number of active vs idle deployments
    - Savings compared to always-on

- [ ] **Add to dashboard page**
  - [ ] Render `<CostDashboard deployments={deployments} />` at top

### 6. Testing & Validation

- [ ] **Test serverless lifecycle**
  1. Deploy server → Status "running"
  2. Wait 5 minutes → Status "stopped"
  3. Send tool call from Claude → Machine wakes
  4. Measure cold start time
  5. Expected: < 10 seconds to first response

- [ ] **Test concurrent requests during cold start**
  - [ ] Send 5 requests simultaneously to stopped machine
  - [ ] Verify all succeed (no errors)
  - [ ] Check only 1 machine started

- [ ] **Cost validation**
  - [ ] Check Fly.io invoice after 1 week
  - [ ] Expected: ~$0.05/deployment instead of ~$1.94

### 7. Documentation

- [ ] **Update `context/CURRENT_STATUS.md`**
  - [ ] Add "Serverless scale-to-zero" to "What Works"
  - [ ] Document cost savings

- [ ] **Create user guide** (in frontend or docs)
  - [ ] Explain serverless behavior
  - [ ] Set expectations for cold start latency

## Files to Create

- `frontend/components/CostDashboard.tsx` (NEW)

## Files to Modify

- `backend/app/services/fly_deployment_service.py` (add services config)
- `backend/app/api/deployments.py` (add warm-up request)
- `backend/app/services/health_monitor.py` (handle stopped state)
- `deploy/Dockerfile` (pre-cache packages)
- `frontend/components/StatusBadge.tsx` (add stopped tooltip)

## Cold Start Optimization Results

Expected performance (based on Fly.io docs):

| Scenario | Cold Start Time |
|----------|-----------------|
| Pre-cached package (TickTick) | 3-5 seconds |
| Non-cached npm package | 8-12 seconds |
| Python package (pip install) | 10-15 seconds |

Target: P95 < 10 seconds (achieved with pre-caching)

## Risk Mitigation

### Risk: Users perceive cold starts as "broken"
**Mitigation**: Clear UI messaging ("Waking server..."), set expectations
**Education**: Add info tooltip explaining serverless behavior

### Risk: Cold start timeout in Claude
**Mitigation**: Claude's default timeout is 60s, well above our 10s target
**Fallback**: Always-on mode toggle for users who need instant response

### Risk: Package not pre-cached → slow cold start
**Mitigation**: Pre-cache top 20 packages (cover 80% of deployments)
**Future**: Allow users to opt into always-on mode

## Deployment Steps

1. Create feature branch
2. Update FlyDeploymentService with serverless config
3. Update Dockerfile with pre-cached packages
4. Rebuild and push Docker image
5. Deploy backend
6. Test serverless lifecycle
7. Monitor costs for 1 week
8. Create git tag `phase-5-complete`

## Next Phase

Proceed to **Phase 6: Advanced Features** (version pinning, OAuth, GitHub-only repos).

See `phase-6-advanced.md` for details.
