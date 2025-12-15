# Phase 5: Deployment Orchestration (Week 9-10)

## Goals
- Programmatically create and manage Fly.io Machines.
- Inject credentials and configuration.
- Expose Streamable HTTP endpoints via `mcp-proxy` (`/mcp`).

## Tasks
- [ ] **Fly.io Integration**
    - [ ] Create `FlyClient` service wrapper.
    - [ ] Implement machine creation logic (using `Dockerfile.base`).
    - [ ] Implement machine destruction/restart logic.
- [ ] **Container Lifecycle**
    - [ ] Health check monitoring.
    - [ ] State synchronization (DB <-> Fly.io).
- [ ] **MCP Bridge (mcp-proxy)**
    - [ ] Verify `mcp-proxy` works in the deployed container.
    - [ ] Ensure proper port exposure (8080).

## Technical Details
- **API**: Fly.io Machines API (REST).
- **Image**: `infrastructure/docker/Dockerfile.base` (Node.js + Python support).
- **Orchestration**: `DeploymentService` in backend.
