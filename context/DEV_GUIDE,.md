# Catwalk Live - Development Guide

## Local Development

### Frontend (Bun)

```bash
cd frontend
bun install
bun run dev
```

The frontend rewrites `/api/*` to `NEXT_PUBLIC_API_URL` (or defaults to `http://127.0.0.1:8000/api/*`).

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Notes:
- Local subprocess MCP server spawning requires Linux/WSL2 (Windows asyncio limitation).
- Production migrations run via Fly `release_command`; local runs can use `alembic upgrade head`.

## Fly Deployment

### Deploy backend

```bash
cd backend
fly deploy --app catwalk-live-backend-dev
```

### Build + push the MCP host image

From `deploy/`:
- PowerShell: `./build-and-push.ps1`
- Bash: `./build-and-push.sh`

Then set the image on the backend:

```bash
fly secrets set FLY_MCP_IMAGE="registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX" --app catwalk-live-backend-dev
```

## Debugging

### Verify backend → machine connectivity (private network)

From your machine:
```bash
fly ssh console --app catwalk-live-backend-dev
```

From the backend shell:
```bash
curl -sv http://{machine_id}.vm.catwalk-live-mcp-servers.internal:8080/status
curl -sv http://{machine_id}.vm.catwalk-live-mcp-servers.internal:8080/mcp \
  -H 'accept: application/json' \
  -H 'content-type: application/json' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### Common failure modes

- `Connection refused` / `ConnectError`: wrong host/path, machine not started, or using the wrong address. Prefer internal DNS (`{machine_id}.vm.{app}.internal`) over raw IPv6.
- `404 Not Found`: wrong endpoint; `mcp-proxy` Streamable HTTP is at `/mcp`.
- `406 Not Acceptable`: missing `Accept: application/json` when calling `/mcp`.

## Testing

Backend:
```bash
cd backend
pytest
ruff check .
```

Frontend:
```bash
cd frontend
bun run typecheck
bun run lint
bun run test
```

