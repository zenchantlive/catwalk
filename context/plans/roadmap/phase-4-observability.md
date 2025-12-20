# Phase 4: Observability - Container Logs & Diagnostics
**Duration**: 3-4 weeks
**Priority**: P1 (High)
**Goal**: Surface container logs so users can debug deployment failures

## Overview

Currently, when deployments fail, users have no visibility into:
- Package installation progress
- npm/pip errors
- Server startup failures
- Runtime errors

This phase adds:
- PostgreSQL log storage (last 1000 lines per deployment)
- Fly.io log collection service
- Historical log viewing API
- Real-time WebSocket log streaming
- Frontend log viewer component

## Success Criteria

- ✅ 100% of deployments have accessible logs
- ✅ Users can view last 1000 lines of container output
- ✅ Real-time log streaming during deployment
- ✅ Logs help diagnose 90% of failures

## Implementation Checklist

### 1. Database Schema for Logs

- [ ] **Create Alembic migration for `deployment_logs` table**
  ```bash
  cd backend
  alembic revision -m "add deployment logs table"
  ```

- [ ] **Edit migration file** (`backend/alembic/versions/xxx_add_deployment_logs.py`)
  - [ ] Add create_table:
    ```python
    op.create_table(
        'deployment_logs',
        sa.Column('id', UUID, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('deployment_id', UUID, sa.ForeignKey('deployments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('stream', sa.String(10), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.CheckConstraint("stream IN ('stdout', 'stderr')", name='check_stream_type')
    )
    ```
  - [ ] Add index:
    ```python
    op.create_index('idx_deployment_logs_timestamp', 'deployment_logs', ['deployment_id', 'timestamp'])
    ```

- [ ] **Apply migration**
  ```bash
  alembic upgrade head
  # Verify table exists
  fly postgres connect --app catwalk-live-db-dev
  \d deployment_logs
  ```

### 2. DeploymentLog Model

- [ ] **Create `backend/app/models/deployment_log.py`**
  - [ ] Define DeploymentLog model:
    ```python
    class DeploymentLog(Base):
        __tablename__ = "deployment_logs"

        id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
        deployment_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("deployments.id", ondelete="CASCADE"))
        timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
        stream: Mapped[str] = mapped_column(String(10))
        message: Mapped[str] = mapped_column(Text)

        deployment: Mapped["Deployment"] = relationship(back_populates="logs")
    ```

- [ ] **Update `backend/app/models/deployment.py`**
  - [ ] Add relationship: `logs: Mapped[List["DeploymentLog"]] = relationship(back_populates="deployment")`

- [ ] **Update `backend/app/models/__init__.py`**
  - [ ] Import DeploymentLog: `from .deployment_log import DeploymentLog`

### 3. Log Collection Service

- [ ] **Create `backend/app/services/log_collector.py`**
  - [ ] Implement `LogCollector` class
  - [ ] Add `tail_machine_logs(deployment_id, machine_id, db)` async method:
    - [ ] Build Fly Machines API logs URL:
      ```python
      url = f"https://api.machines.dev/v1/apps/{app_name}/machines/{machine_id}/logs"
      ```
    - [ ] Stream logs with httpx:
      ```python
      async with client.stream("GET", url, headers=auth_headers) as stream:
          async for line in stream.aiter_lines():
              # Parse Fly log format
              log_entry = parse_fly_log(line)
              # Store in database
              await store_log(db, deployment_id, log_entry)
      ```
  - [ ] Add `parse_fly_log(line)` helper:
    - [ ] Parse format: `timestamp stream message`
    - [ ] Return `{"timestamp": dt, "stream": str, "message": str}`
  - [ ] Add `store_log(db, deployment_id, log_entry)` helper:
    - [ ] Insert into deployment_logs table
    - [ ] Implement retention (keep last 1000 lines):
      ```python
      await db.execute(
          delete(DeploymentLog)
          .where(DeploymentLog.deployment_id == deployment_id)
          .where(
              DeploymentLog.id.not_in(
                  select(DeploymentLog.id)
                  .where(DeploymentLog.deployment_id == deployment_id)
                  .order_by(DeploymentLog.timestamp.desc())
                  .limit(1000)
              )
          )
      )
      ```

- [ ] **Test log collection locally** (mock Fly API response)

### 4. Log API Endpoints

- [ ] **Update `backend/app/api/deployments.py`**
  - [ ] Add `GET /deployments/{deployment_id}/logs` endpoint:
    ```python
    @router.get("/{deployment_id}/logs")
    async def get_deployment_logs(
        deployment_id: str,
        limit: int = Query(100, le=1000),
        stream: Optional[str] = Query(None, regex="^(stdout|stderr)$"),
        db: AsyncSession = Depends(get_db)
    ):
        query = (
            select(DeploymentLog)
            .where(DeploymentLog.deployment_id == deployment_id)
            .order_by(DeploymentLog.timestamp.desc())
            .limit(limit)
        )
        if stream:
            query = query.where(DeploymentLog.stream == stream)

        result = await db.execute(query)
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "stream": log.stream,
                    "message": log.message
                }
                for log in reversed(logs)  # Oldest first
            ]
        }
    ```

- [ ] **Add WebSocket endpoint for streaming** (optional for Phase 4)
  - [ ] `GET /deployments/{deployment_id}/logs/stream`
  - [ ] WebSocket implementation:
    ```python
    @router.websocket("/{deployment_id}/logs/stream")
    async def stream_deployment_logs(
        websocket: WebSocket,
        deployment_id: str
    ):
        await websocket.accept()
        # Subscribe to log events for this deployment
        # (Requires event broadcasting system)
    ```
  - [ ] Note: May defer WebSocket to future phase if complex

### 5. Integrate Log Collection into Deployment Flow

- [ ] **Update `backend/app/api/deployments.py`** (after machine creation)
  - [ ] Start log collection asynchronously:
    ```python
    if machine_id:
        # Start collecting logs in background
        log_collector = LogCollector()
        asyncio.create_task(
            log_collector.tail_machine_logs(
                deployment_id=str(deployment.id),
                machine_id=machine_id,
                db=db
            )
        )
    ```
  - [ ] Note: Background task runs independently of HTTP request

### 6. Frontend Log Viewer Component

- [ ] **Create `frontend/components/LogViewer.tsx`**
  - [ ] Accept `deploymentId` prop
  - [ ] Fetch logs on mount:
    ```typescript
    useEffect(() => {
        getDeploymentLogs(deploymentId, 100).then(setLogs);
    }, [deploymentId]);
    ```
  - [ ] Render terminal-style log display:
    - [ ] Black background (`bg-gray-900`)
    - [ ] Monospace font (`font-mono`)
    - [ ] Color-coded streams (stdout: gray, stderr: red)
    - [ ] Timestamps in gray
    - [ ] Auto-scroll to bottom
  - [ ] Add refresh button
  - [ ] Add stream filter (all / stdout / stderr)

- [ ] **Update `frontend/app/dashboard/[id]/page.tsx`** (deployment detail page)
  - [ ] Import LogViewer
  - [ ] Render `<LogViewer deploymentId={id} />` in tab or section

- [ ] **Add to `frontend/lib/api.ts`**
  - [ ] Create `getDeploymentLogs(deploymentId, limit)` function:
    ```typescript
    export async function getDeploymentLogs(
        deploymentId: string,
        limit: number = 100
    ): Promise<LogEntry[]> {
        const res = await fetch(
            `/api/deployments/${deploymentId}/logs?limit=${limit}`
        );
        if (!res.ok) throw new Error("Failed to fetch logs");
        const data = await res.json();
        return data.logs;
    }
    ```

### 7. Fly.io Logs API Integration

- [ ] **Update `backend/app/services/fly_deployment_service.py`**
  - [ ] Add `get_machine_logs(machine_id)` method:
    ```python
    async def get_machine_logs(self, machine_id: str):
        """Stream logs from Fly machine."""
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}/logs"
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, headers=headers, timeout=None) as response:
                async for line in response.aiter_lines():
                    yield line
    ```

- [ ] **Test Fly logs API access**
  ```bash
  curl -H "Authorization: Bearer $FLY_API_TOKEN" \
    https://api.machines.dev/v1/apps/catwalk-live-mcp-servers/machines/{machine_id}/logs
  ```

### 8. Testing & Validation

- [ ] **Test log storage**
  - [ ] Deploy test server
  - [ ] Check database for logs:
    ```sql
    SELECT COUNT(*) FROM deployment_logs WHERE deployment_id = '{id}';
    ```
  - [ ] Verify last 1000 lines retained

- [ ] **Test log API**
  ```bash
  curl https://catwalk-live-backend-dev.fly.dev/api/deployments/{id}/logs?limit=50
  # Should return last 50 log entries
  ```

- [ ] **Test frontend log viewer**
  - [ ] Visit deployment detail page
  - [ ] Verify logs displayed
  - [ ] Test stream filter (stdout/stderr/all)
  - [ ] Test refresh button

- [ ] **End-to-end test: Failed deployment**
  - [ ] Deploy server with invalid package
  - [ ] Check logs show npm/pip error
  - [ ] Verify error visible in frontend log viewer

### 9. Documentation Updates

- [ ] **Update `context/CURRENT_STATUS.md`**
  - [ ] Move "Container logs" from "What's NOT Working" to "What Works"
  - [ ] Add Phase 4 completion status

- [ ] **Update `context/API_SPEC.md`**
  - [ ] Document `GET /deployments/{id}/logs` endpoint
  - [ ] Add example responses

## Files to Create

- `backend/app/models/deployment_log.py` (NEW)
- `backend/app/services/log_collector.py` (NEW)
- `backend/alembic/versions/xxx_add_deployment_logs.py` (NEW migration)
- `frontend/components/LogViewer.tsx` (NEW)
- `frontend/app/dashboard/[id]/page.tsx` (NEW - deployment detail page)

## Files to Modify

- `backend/app/models/deployment.py` (add logs relationship)
- `backend/app/models/__init__.py` (import DeploymentLog)
- `backend/app/api/deployments.py` (add log endpoints, start collection)
- `backend/app/services/fly_deployment_service.py` (add get_machine_logs)
- `frontend/lib/api.ts` (add getDeploymentLogs function)

## Example Code

### Log Viewer Component

```typescript
// frontend/components/LogViewer.tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { getDeploymentLogs } from "@/lib/api";

interface LogEntry {
    timestamp: string;
    stream: "stdout" | "stderr";
    message: string;
}

export default function LogViewer({ deploymentId }: { deploymentId: string }) {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [filter, setFilter] = useState<"all" | "stdout" | "stderr">("all");
    const logEndRef = useRef<HTMLDivElement>(null);

    const loadLogs = async () => {
        const data = await getDeploymentLogs(deploymentId, 100);
        setLogs(data);
    };

    useEffect(() => {
        loadLogs();
    }, [deploymentId]);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    const filteredLogs = filter === "all"
        ? logs
        : logs.filter(log => log.stream === filter);

    return (
        <div className="space-y-4">
            <div className="flex justify-between">
                <h3 className="text-lg font-semibold">Container Logs</h3>
                <div className="flex gap-2">
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value as any)}
                        className="px-2 py-1 rounded border"
                    >
                        <option value="all">All</option>
                        <option value="stdout">stdout</option>
                        <option value="stderr">stderr</option>
                    </select>
                    <button onClick={loadLogs} className="btn-sm">
                        Refresh
                    </button>
                </div>
            </div>

            <div className="bg-gray-900 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
                {filteredLogs.map((log, i) => (
                    <div
                        key={i}
                        className={log.stream === "stderr" ? "text-red-400" : "text-gray-300"}
                    >
                        <span className="text-gray-500">
                            {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        {" "}
                        <span className="text-yellow-500">[{log.stream}]</span>
                        {" "}
                        {log.message}
                    </div>
                ))}
                <div ref={logEndRef} />
            </div>
        </div>
    );
}
```

## Testing Scenarios

### Test 1: Successful deployment logs
1. Deploy valid server (TickTick)
2. View logs at `/dashboard/{id}`
3. Expected logs:
   ```
   Starting npm package: @alexarevalo.ai/mcp-server-ticktick
   Installing packages...
   mcp-proxy listening on [::]:8080
   ```

### Test 2: Failed deployment logs
1. Deploy with invalid package name
2. View logs
3. Expected logs:
   ```
   Starting npm package: nonexistent-package
   npm ERR! 404 Not Found
   npm ERR! '@nonexistent-package' is not in the npm registry
   ```

### Test 3: Log retention
1. Generate >1000 log lines (deploy chatty server)
2. Query database:
   ```sql
   SELECT COUNT(*) FROM deployment_logs WHERE deployment_id = '{id}';
   ```
3. Expected: Exactly 1000 rows (oldest deleted)

## Risk Mitigation

### Risk: High log volume overwhelms database
**Mitigation**: 1000-line limit per deployment with auto-cleanup
**Future**: Archive old logs to S3

### Risk: Fly logs API rate limits
**Mitigation**: Single stream per deployment, closed when deployment inactive
**Future**: Use Fly logs retention instead of streaming

### Risk: Real-time streaming complexity
**Mitigation**: Start with polling (GET /logs), add WebSocket later
**Acceptable**: 5-10s delay for log updates is fine for debugging

## Deployment Steps

1. **Create feature branch**
   ```bash
   git checkout -b phase-4-observability
   ```

2. **Implement backend changes**
   ```bash
   cd backend
   alembic revision -m "add deployment logs"
   # Edit migration
   alembic upgrade head
   # Create log_collector.py
   # Update deployments.py
   pytest -v
   ```

3. **Implement frontend changes**
   ```bash
   cd frontend
   # Create LogViewer component
   # Create deployment detail page
   bun run typecheck
   ```

4. **Deploy to Fly.io**
   ```bash
   cd backend
   fly deploy --app catwalk-live-backend-dev
   ```

5. **Test end-to-end**
   - Deploy test server
   - View logs in frontend
   - Verify logs update on refresh

6. **Create git tag**
   ```bash
   git add .
   git commit -m "feat: add container logs and diagnostics (Phase 4)"
   git tag phase-4-complete
   git push origin phase-4-observability
   git push origin phase-4-complete
   ```

## Next Phase

After Phase 4 is complete, proceed to **Phase 5: Serverless & Cost Optimization**.

See `phase-5-serverless.md` for details.
