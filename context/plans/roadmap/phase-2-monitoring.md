# Phase 2: Health Monitoring & Status Tracking
**Duration**: 2-3 weeks
**Priority**: P0 (Blocking)
**Goal**: Know when deployments are actually working vs. just "running"

## Overview

Currently, deployments are marked "running" immediately after Fly machine creation, even if:
- npm install fails
- Package doesn't exist
- Server crashes on startup
- Environment variables are wrong

This phase adds:
- Background health monitoring (polls `/status` every 30s)
- Accurate deployment status (pending → installing → starting → running → unhealthy)
- Progress tracking during deployment
- Frontend status indicators and auto-refresh

## Success Criteria

- ✅ Unhealthy deployments detected within 60 seconds
- ✅ Deployment status accurately reflects machine state
- ✅ Users see progress during deployment ("Installing packages...")
- ✅ Health checks distinguish "stopped" (serverless) vs "unhealthy" (broken)

## Implementation Checklist

### 1. Deployment Status Enum

- [ ] **Update `backend/app/models/deployment.py`** (line 28)
  - [ ] Import `Enum` from Python's enum module
  - [ ] Create `DeploymentStatus` enum:
    ```python
    class DeploymentStatus(str, Enum):
        PENDING = "pending"
        INSTALLING = "installing"
        STARTING = "starting"
        RUNNING = "running"
        UNHEALTHY = "unhealthy"
        STOPPED = "stopped"
        FAILED = "failed"
    ```
  - [ ] Update `status` column to use enum
  - [ ] Add `progress_message` column (nullable string)

- [ ] **Create Alembic migration**
  ```bash
  cd backend
  alembic revision --autogenerate -m "add deployment status enum"
  ```
  - [ ] Review generated migration
  - [ ] Test locally: `alembic upgrade head`
  - [ ] Verify enum values in database

### 2. Health Monitor Service

- [ ] **Create `backend/app/services/health_monitor.py`**
  - [ ] Implement `HealthMonitor` class
  - [ ] Add `__init__` method (initialize state)
  - [ ] Add `start(db_session_factory)` async method:
    - [ ] Set `self.running = True`
    - [ ] Enter infinite loop: `while self.running:`
    - [ ] Query deployments with `machine_id IS NOT NULL`
    - [ ] Filter by status: `["running", "unhealthy"]`
    - [ ] Check each deployment in parallel with `asyncio.gather()`
    - [ ] Sleep 30 seconds between checks
  - [ ] Add `_check_deployment_health(db, deployment)` async method:
    - [ ] Build machine URL: `http://{machine_id}.vm.{app}.internal:8080/status`
    - [ ] Try GET request with 5-second timeout
    - [ ] If 200 OK → update status to "running"
    - [ ] If non-200 → update status to "unhealthy"
    - [ ] If ConnectError → query Fly Machines API
      - [ ] If machine state is "stopped" → status "stopped"
      - [ ] If machine exists but unreachable → status "unhealthy"
    - [ ] Commit changes to database

- [ ] **Write tests for health monitor**
  - [ ] Test healthy deployment → status remains "running"
  - [ ] Test unhealthy deployment (500 response) → status becomes "unhealthy"
  - [ ] Test stopped machine → status becomes "stopped"
  - [ ] Test unreachable machine → status becomes "unhealthy"

### 3. App Startup Integration

- [ ] **Update `backend/app/main.py`**
  - [ ] Import `asynccontextmanager` from contextlib
  - [ ] Import `HealthMonitor` from services
  - [ ] Create `lifespan` context manager:
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        health_monitor = HealthMonitor()
        health_task = asyncio.create_task(
            health_monitor.start(get_db_session_factory())
        )
        yield
        health_monitor.running = False
        await health_task
    ```
  - [ ] Update `FastAPI` instantiation: `app = FastAPI(lifespan=lifespan)`

- [ ] **Test health monitor startup**
  ```bash
  cd backend
  uvicorn app.main:app --reload
  # Check logs for "HealthMonitor started"
  ```

### 4. Deployment Progress Tracking

- [ ] **Update `backend/app/api/deployments.py`** (line 79-90)
  - [ ] After creating deployment record:
    - [ ] Set `deployment.status = DeploymentStatus.INSTALLING`
    - [ ] Set `deployment.progress_message = "Creating Fly machine..."`
    - [ ] Commit to database
  - [ ] After `fly_service.create_machine()` succeeds:
    - [ ] Set `deployment.status = DeploymentStatus.STARTING`
    - [ ] Set `deployment.progress_message = "Installing packages and starting server..."`
    - [ ] Commit to database
  - [ ] Implement `wait_for_health(machine_id, timeout)` helper:
    - [ ] Poll machine `/status` every 2 seconds
    - [ ] Return `True` if 200 OK within timeout
    - [ ] Return `False` if timeout exceeded
  - [ ] After machine creation:
    - [ ] Call `wait_for_health(machine_id, timeout=60)`
    - [ ] If healthy → status "running", clear progress_message
    - [ ] If timeout → status "unhealthy", error_message "failed to start"

### 5. Frontend Status Display

- [ ] **Create `frontend/components/DeploymentProgress.tsx`**
  - [ ] Accept `deployment` prop
  - [ ] Define step mapping:
    ```typescript
    const steps = {
      pending: 0,
      installing: 33,
      starting: 66,
      running: 100
    };
    ```
  - [ ] Render progress bar (0-100% width)
  - [ ] Display `progress_message` if present
  - [ ] Style with Tailwind (bg-blue-500 for progress)

- [ ] **Create `frontend/components/StatusBadge.tsx`**
  - [ ] Accept `status` prop
  - [ ] Define colors:
    ```typescript
    const colors = {
      running: "bg-green-500",
      unhealthy: "bg-red-500",
      pending: "bg-yellow-500",
      installing: "bg-blue-500",
      starting: "bg-blue-500",
      stopped: "bg-gray-500",
      failed: "bg-red-500"
    };
    ```
  - [ ] Render badge with status text and color

- [ ] **Update `frontend/app/dashboard/page.tsx`**
  - [ ] Import `StatusBadge` and `DeploymentProgress`
  - [ ] Add auto-refresh logic:
    ```typescript
    refetchInterval: (data) => {
      const hasActive = data?.some(d =>
        ["pending", "installing", "starting"].includes(d.status)
      );
      return hasActive ? 5000 : 30000;  // 5s if active, 30s otherwise
    }
    ```
  - [ ] Render `StatusBadge` for each deployment
  - [ ] Render `DeploymentProgress` for active deployments

### 6. Fly Machines API Integration

- [ ] **Update `backend/app/services/fly_deployment_service.py`**
  - [ ] Add `get_machine(machine_id)` method:
    ```python
    async def get_machine(self, machine_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()
            return None
    ```
  - [ ] Use in health monitor to check machine state

### 7. Testing & Validation

- [ ] **End-to-end testing**
  - [ ] Deploy TickTick server
  - [ ] Watch status transitions:
    ```bash
    watch -n 2 'curl -s https://<your-backend-app>.fly.dev/api/deployments/{id} | jq ".status, .progress_message"'
    ```
  - [ ] Verify: pending → installing → starting → running
  - [ ] Deploy server that fails to start (invalid package)
  - [ ] Verify: pending → installing → starting → unhealthy
  - [ ] Stop machine manually: `fly machine stop {machine_id}`
  - [ ] Verify: running → stopped (not unhealthy)

- [ ] **Run test suite**
  ```bash
  cd backend
  pytest tests/test_health_monitor.py -v
  pytest tests/test_deployments.py -v
  ruff check .

  cd ../frontend
  bun run typecheck
  bun run lint
  ```

### 8. Documentation Updates

- [ ] **Update `context/CURRENT_STATUS.md`**
  - [ ] Move "Health monitoring" from "What's NOT Working" to "What Works"
  - [ ] Add Phase 2 completion status
  - [ ] Document status enum values

## Files to Create

- `backend/app/services/health_monitor.py` (NEW)
- `backend/tests/test_health_monitor.py` (NEW)
- `backend/alembic/versions/xxx_add_deployment_status_enum.py` (NEW migration)
- `frontend/components/DeploymentProgress.tsx` (NEW)
- `frontend/components/StatusBadge.tsx` (NEW)

## Files to Modify

- `backend/app/models/deployment.py` (add status enum, progress_message column)
- `backend/app/main.py` (add lifespan with health monitor)
- `backend/app/api/deployments.py` (add progress tracking)
- `backend/app/services/fly_deployment_service.py` (add get_machine method)
- `frontend/app/dashboard/page.tsx` (add status display and auto-refresh)

## Example Code

### Health Monitor

```python
# backend/app/services/health_monitor.py
import asyncio
import httpx
from sqlalchemy import select
from app.models.deployment import Deployment, DeploymentStatus

class HealthMonitor:
    def __init__(self):
        self.running = False
        self.check_interval = 30

    async def start(self, db_session_factory):
        self.running = True

        while self.running:
            async with db_session_factory() as db:
                result = await db.execute(
                    select(Deployment).where(
                        Deployment.machine_id.isnot(None),
                        Deployment.status.in_([
                            DeploymentStatus.RUNNING,
                            DeploymentStatus.UNHEALTHY
                        ])
                    )
                )
                deployments = result.scalars().all()

                await asyncio.gather(*[
                    self._check_deployment_health(db, d)
                    for d in deployments
                ])

            await asyncio.sleep(self.check_interval)

    async def _check_deployment_health(self, db, deployment):
        machine_url = f"http://{deployment.machine_id}.vm.{app_name}.internal:8080/status"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(machine_url)

                if response.status_code == 200:
                    if deployment.status != DeploymentStatus.RUNNING:
                        deployment.status = DeploymentStatus.RUNNING
                        deployment.error_message = None
                        await db.commit()
                else:
                    if deployment.status != DeploymentStatus.UNHEALTHY:
                        deployment.status = DeploymentStatus.UNHEALTHY
                        deployment.error_message = f"Health check failed: {response.status_code}"
                        await db.commit()

        except httpx.ConnectError:
            # Check if machine is stopped (serverless) or actually unhealthy
            from app.services.fly_deployment_service import FlyDeploymentService
            fly_service = FlyDeploymentService()
            machine_info = await fly_service.get_machine(deployment.machine_id)

            if machine_info and machine_info.get("state") == "stopped":
                if deployment.status != DeploymentStatus.STOPPED:
                    deployment.status = DeploymentStatus.STOPPED
                    await db.commit()
            else:
                if deployment.status != DeploymentStatus.UNHEALTHY:
                    deployment.status = DeploymentStatus.UNHEALTHY
                    deployment.error_message = "Machine unreachable"
                    await db.commit()
```

### Progress Tracking

```python
# In backend/app/api/deployments.py (after machine creation)
if machine_id:
    deployment.machine_id = machine_id
    deployment.status = DeploymentStatus.STARTING
    deployment.progress_message = "Installing packages and starting server..."
    await db.commit()

    # Wait for health check to pass
    health_ok = await wait_for_health(machine_id, timeout=60)

    if health_ok:
        deployment.status = DeploymentStatus.RUNNING
        deployment.progress_message = None
        await db.commit()
    else:
        deployment.status = DeploymentStatus.UNHEALTHY
        deployment.error_message = "Server failed to start within 60 seconds"
        await db.commit()

async def wait_for_health(machine_id: str, timeout: int) -> bool:
    start_time = asyncio.get_event_loop().time()
    machine_url = f"http://{machine_id}.vm.{app_name}.internal:8080/status"

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(machine_url)
                if response.status_code == 200:
                    return True
        except httpx.ConnectError:
            pass

        await asyncio.sleep(2)

    return False
```

## Testing Scenarios

### Test 1: Healthy deployment
1. Deploy TickTick with valid credentials
2. Watch logs: `fly logs --app <your-backend-app>`
3. Expected status transitions:
   - pending (0s)
   - installing (5s)
   - starting (15s)
   - running (30s)

### Test 2: Unhealthy deployment
1. Deploy with invalid package name
2. Expected status transitions:
   - pending → installing → starting → unhealthy
3. Error message should contain "failed to start"

### Test 3: Serverless stopped machine
1. Deploy valid server, wait for "running"
2. Stop machine: `fly machine stop {machine_id} --app {app_name}`
3. Wait 60 seconds for health monitor to detect
4. Expected: status transitions running → stopped (not unhealthy)

## Risk Mitigation

### Risk: Health monitor crashes and doesn't restart
**Solution**: Implement watchdog process or use Fly.io restart policy
**Mitigation**: Log health monitor heartbeat every 60s for monitoring

### Risk: 30-second polling too slow
**Solution**: Make check_interval configurable via environment variable
**Future**: Add webhook support for instant notifications

### Risk: False positives (stopped vs unhealthy)
**Solution**: Query Fly Machines API to check actual machine state
**Implemented**: In `_check_deployment_health` ConnectError handler

## Deployment Steps

1. **Create feature branch**
   ```bash
   git checkout -b phase-2-monitoring
   ```

2. **Implement backend changes**
   ```bash
   cd backend
   # Create health_monitor.py
   # Update models/deployment.py
   # Generate migration
   alembic upgrade head
   # Test locally
   pytest -v
   ```

3. **Implement frontend changes**
   ```bash
   cd frontend
   # Create StatusBadge and DeploymentProgress components
   # Update dashboard/page.tsx
   bun run typecheck
   ```

4. **Deploy to Fly.io**
   ```bash
   cd backend
   fly deploy --app <your-backend-app>
   # Monitor for health monitor startup
   fly logs --app <your-backend-app> | grep "HealthMonitor"
   ```

5. **Test end-to-end**
   - Deploy test server
   - Watch status transitions in frontend
   - Verify health monitor detects failures

6. **Create git tag**
   ```bash
   git add .
   git commit -m "feat: add health monitoring and status tracking (Phase 2)"
   git tag phase-2-complete
   git push origin phase-2-monitoring
   git push origin phase-2-complete
   ```

## Next Phase

After Phase 2 is complete and validated, proceed to **Phase 3: Multi-Runtime Support**.

See `phase-3-runtime.md` for details.
