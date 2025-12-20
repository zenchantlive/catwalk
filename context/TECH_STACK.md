# Catwalk Live - Tech Stack

## Product Summary

Catwalk Live deploys GitHub-hosted MCP servers as remotely accessible **MCP Streamable HTTP** endpoints.

High-level flow:
`Claude → catwalk backend (/api/mcp/{deployment_id}) → Fly MCP machine (mcp-proxy /mcp) → stdio MCP server`

## Frontend

- **Framework**: Next.js 15 (App Router), React 19
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **Package manager**: Bun (`bun install`, `bun run dev`)
- **Testing**: Vitest (unit/component), Playwright (E2E)

## Backend

- **Framework**: FastAPI (Python 3.12)
- **DB**: PostgreSQL (Fly.io) + SQLAlchemy 2.0 async
- **Driver**: psycopg 3 (`psycopg[binary]`) with `postgresql+psycopg://` URLs
- **Migrations**: Alembic (Fly runs migrations via `release_command`)
- **Claude analysis**: OpenRouter via `openai` SDK (`AsyncOpenAI(base_url="https://openrouter.ai/api/v1")`)
- **HTTP**: `httpx` for Fly Machines API + MCP machine forwarding
- **Credential storage**: Fernet (`cryptography`) encryption at rest

## Infrastructure (Fly.io)

Apps:
- Backend: `<your-backend-app>`
- Postgres: `<your-database-app>`
- MCP machines app: `<your-mcp-app>`

MCP machine image:
- Built from `deploy/Dockerfile`
- Runs `mcp-proxy>=0.10.0` (Streamable HTTP at `/mcp`, health at `/status`)
- Runs the MCP server package via `npx -y $MCP_PACKAGE` (Node.js 20 inside the image)

Networking:
- Backend reaches machines via Fly internal DNS (6PN):
  - `http://{machine_id}.vm.{FLY_MCP_APP_NAME}.internal:8080/mcp`

## Configuration

Backend secrets (Fly):
- `DATABASE_URL` (Fly provides `postgres://...`; backend normalizes to `postgresql+psycopg://...`)
- `ENCRYPTION_KEY` (Fernet key)
- `OPENROUTER_API_KEY`
- `PUBLIC_URL` (e.g. `https://<your-backend-app>.fly.dev`)
- `FLY_API_TOKEN`
- `FLY_MCP_APP_NAME` (e.g. `<your-mcp-app>`)
- `FLY_MCP_IMAGE` (image ref pushed by `deploy/build-and-push.*`)

Frontend env:
- `NEXT_PUBLIC_API_URL` (should point at the backend base URL; Next rewrites `/api/*` to it)

## Repo Structure (monorepo)

```
catwalk-live/
  backend/      # FastAPI + Alembic + Fly config
  frontend/     # Next.js 15 app (Bun)
  deploy/       # Shared MCP host image + build scripts
  context/      # Docs (this folder)
  infrastructure/
  scripts/
```

