# MCP Remote Platform - Tech Stack & File Structure

## Technology Choices

### Frontend Stack

**Framework: Next.js 16 (LTS)**
- React 19+ with Server Components
- TypeScript for type safety
- Built-in routing, SSR, and optimization

**Why Next.js?**
- Best-in-class React framework for production
- App Router is future-proof (Pages Router is legacy)
- Excellent TypeScript support
- Easy deployment to Vercel
- Server Components reduce client JS bundle

**Styling: Tailwind CSS 4+**
- Utility-first CSS framework
- Rapid prototyping
- Consistent design system
- Minimal custom CSS needed

**State Management: React Hooks**
- useState for component state
- useEffect for side effects
- No Redux/Zustand needed (simple app)
- Context API if shared state needed (future)

**API Client: Native Fetch**
- TypeScript wrapper for type safety
- No Axios needed (fetch is sufficient)
- Automatic JSON parsing

**Testing:**
- Vitest (unit/component tests)
- React Testing Library (component behavior)
- Playwright (E2E tests)

### Backend Stack

**Framework: FastAPI (Python 3.12+)**
- Async-native web framework
- Automatic OpenAPI docs
- Pydantic validation built-in
- Excellent performance

**Why FastAPI?**
- Type hints throughout (Python's TypeScript)
- Auto-generated API documentation
- Async support for I/O-bound operations
- Easy testing with TestClient

**Database: PostgreSQL 15+**
- ORM: SQLAlchemy 2.0+ (async mode)
- Driver: asyncpg (fastest Python Postgres driver)
- Migrations: Alembic

**Why PostgreSQL?**
- ACID compliance (important for credentials)
- JSONB support for flexible schemas
- Excellent performance
- Battle-tested reliability

**External APIs:**
- anthropic (Claude API client)
- httpx (async HTTP client for Fly.io API)
- cryptography (Fernet encryption)

**Testing:**
- pytest (test framework)
- pytest-asyncio (async test support)
- httpx TestClient (API testing)

### Infrastructure Stack

**Container Runtime: Fly.io Machines**
- Firecracker VMs (not Docker containers)
- Global edge network
- Simple Machines API
- Scale-to-zero capable (Phase 9)

**Why Fly.io?**
- Fast cold starts (<1 second)
- Built-in HTTPS and routing
- Excellent developer experience
- Cost-effective for our use case
- No complex orchestration (K8s) needed

**MCP Bridge: mcp-proxy**
- Open source stdio→Streamable HTTP bridge (also supports legacy SSE)
- We don't build this, just use it
- Installed in base Docker image

**Container Registry:**
- Fly.io registry (built-in)
- Alternative: Docker Hub (if needed)

**Secrets Management:**
- Fly.io secrets (for master encryption key)
- Application-level encryption (Fernet)

### Development Tools

**Version Control:**
- Git
- GitHub (mono-repo with frontend + backend)

**CI/CD:**
- GitHub Actions
- Automated tests on every PR
- Auto-deploy to Fly.io on merge to main

**Code Quality:**
- Frontend: ESLint + Prettier
- Backend: Ruff (fast Python linter)
- Pre-commit hooks (lint on commit)

**Documentation:**
- OpenAPI (auto-generated from FastAPI)
- README per component
- Architecture diagrams (Mermaid in markdown)

## Detailed File Structure

```
mcp-remote-platform/
│
├── frontend/                          # Next.js application
│   ├── app/                          # Next.js 14 app directory
│   │   ├── layout.tsx               # Root layout
│   │   ├── page.tsx                 # Landing (GitHub URL input)
│   │   ├── analyze/[id]/page.tsx    # Analysis results
│   │   ├── deploy/[id]/page.tsx     # Deploy confirmation
│   │   ├── dashboard/page.tsx       # Deployment list
│   │   └── globals.css              # Tailwind imports
│   │
│   ├── components/
│   │   ├── ui/                      # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── GitHubUrlInput.tsx       # URL validation + submit
│   │   ├── AnalysisResults.tsx      # Display config
│   │   ├── CredentialForm.tsx       # Dynamic form
│   │   ├── DeploymentCard.tsx       # Single deployment
│   │   ├── DeploymentList.tsx       # All deployments
│   │   └── ClaudeInstructions.tsx   # Setup instructions
│   │
│   ├── lib/
│   │   ├── api-client.ts            # Backend API wrapper
│   │   ├── types.ts                 # TypeScript interfaces
│   │   └── utils.ts                 # Helper functions
│   │
│   ├── __tests__/
│   │   ├── components/              # Component tests
│   │   └── e2e/                     # Playwright tests
│   │
│   ├── public/
│   │   └── images/                  # Screenshots, logos
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── main.py                  # FastAPI app + CORS setup
│   │   ├── config.py                # Pydantic Settings
│   │   │
│   │   ├── api/                     # API routes
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py          # POST /analyze
│   │   │   ├── deployments.py      # Deployment CRUD
│   │   │   └── health.py           # GET /health
│   │   │
│   │   ├── services/                # Business logic
│   │   │   ├── analysis.py         # Claude API integration
│   │   │   ├── credentials.py      # Encryption
│   │   │   ├── deployments.py      # Fly.io orchestration
│   │   │   └── cache.py            # Analysis caching
│   │   │
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── deployment.py
│   │   │   ├── credential.py
│   │   │   └── analysis_cache.py
│   │   │
│   │   ├── schemas/                 # Pydantic schemas
│   │   │   ├── analyze.py          # Request/response
│   │   │   ├── deployment.py       # DTOs
│   │   │   └── credential.py       # Credential schemas
│   │   │
│   │   ├── clients/                 # External APIs
│   │   │   ├── claude.py           # Anthropic client
│   │   │   └── fly.py              # Fly.io Machines API
│   │   │
│   │   ├── database/
│   │   │   ├── session.py          # Async session
│   │   │   └── base.py             # SQLAlchemy base
│   │   │
│   │   └── utils/
│   │       ├── encryption.py       # Fernet helpers
│   │       ├── validation.py       # Input validation
│   │       └── logging.py          # Structured logging
│   │
│   ├── tests/
│   │   ├── unit/                    # Service tests
│   │   ├── integration/             # API tests
│   │   └── fixtures/                # Test data
│   │
│   ├── alembic/                      # DB migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile.base          # MCP base image
│   │   │   # FROM python:3.11-slim
│   │   │   # Install Node.js 20
│   │   │   # Install mcp-proxy
│   │   │   # EXPOSE 8080
│   │   │
│   │   └── Dockerfile.backend       # Backend API
│   │
│   ├── fly/
│   │   ├── fly.backend.toml         # Backend config
│   │   └── fly.base.toml            # MCP container template
│   │
│   └── scripts/
│       ├── deploy-backend.sh
│       └── build-base-image.sh
│
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md               # This file
│   ├── API_SPECIFICATION.md
│   └── DEVELOPMENT_GUIDE.md
│
├── .github/
│   └── workflows/
│       ├── backend-tests.yml
│       ├── frontend-tests.yml
│       └── deploy.yml
│
├── .env.example
├── docker-compose.yml
└── README.md
```

## Key Design Decisions

### 1. Monorepo vs Multi-repo

**Decision: Monorepo**

**Rationale:**
- Simpler for single developer (you)
- Shared types between frontend/backend
- Single CI/CD pipeline
- Easier to keep in sync

**Alternative Considered:** Separate repos
- Rejected: Adds coordination overhead

### 2. Next.js App Router vs Pages Router

**Decision: App Router**

**Rationale:**
- Future-proof (Pages Router is legacy)
- Better TypeScript support
- Server Components reduce client JS
- Improved data fetching patterns

**Alternative Considered:** Pages Router
- Rejected: Why start with deprecated tech?

### 3. SQLAlchemy Async vs Sync

**Decision: Async**

**Rationale:**
- FastAPI is async-native
- Non-blocking I/O for Fly.io API calls
- Better performance under load
- Modern best practice

**Alternative Considered:** Sync SQLAlchemy
- Rejected: Blocks event loop, worse performance

### 4. Fernet vs AWS KMS for Encryption

**Decision: Fernet (symmetric encryption)**

**Rationale:**
- No external dependencies (runs anywhere)
- Fast encryption/decryption
- Audited implementation (cryptography lib)
- Good enough security for MVP
- Can migrate to KMS later if needed

**Alternative Considered:** AWS KMS
- Rejected: Adds cost and complexity for MVP

### 5. PostgreSQL vs MongoDB

**Decision: PostgreSQL**

**Rationale:**
- Structured data (clear schema)
- ACID transactions (important for credentials)
- JSONB if we need flexibility
- Better for relational queries

**Alternative Considered:** MongoDB
- Rejected: No compelling reason for document model

### 6. Polling vs WebSocket for Status Updates

**Decision: Polling (for MVP)**

**Rationale:**
- Simpler implementation
- No WebSocket infrastructure needed
- Adequate UX (2-second updates during deploy)
- Can add WebSocket later if needed

**[ASSUMPTION: Poll every 2 seconds during deployment, every 30 seconds when running]**

**Alternative Considered:** WebSocket
- Rejected: Over-engineered for MVP

## Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mcpremote

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Fly.io
FLY_API_TOKEN=fo1_...
FLY_APP_NAME=mcp-deployments

# Encryption
MASTER_ENCRYPTION_KEY=<32-byte base64 key>

# Environment
ENVIRONMENT=development  # or production
LOG_LEVEL=INFO
```

### Frontend (.env.local)
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Environment
NEXT_PUBLIC_ENVIRONMENT=development
```

### Fly.io Secrets
```bash
fly secrets set MASTER_ENCRYPTION_KEY=<key>
fly secrets set ANTHROPIC_API_KEY=<key>
fly secrets set FLY_API_TOKEN=<token>
```

## Dependencies

### Frontend (package.json)
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "typescript": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "autoprefixer": "^10.0.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^14.0.0",
    "postcss": "^8.0.0",
    "prettier": "^3.0.0",
    "tailwindcss": "^3.0.0",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

### Backend (requirements.txt)
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
alembic==1.13.1
asyncpg==0.29.0
pydantic==2.5.3
pydantic-settings==2.1.0
anthropic==0.18.0
httpx==0.26.0
cryptography==42.0.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
```

### Backend (requirements-dev.txt)
```txt
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
ruff==0.1.13
```

## Local Development Setup

### Prerequisites
```bash
# Install Python 3.11+
python --version  # Should be 3.11+

# Install Node.js 20+
node --version  # Should be 20+

# Install PostgreSQL 15+
postgres --version  # Should be 15+

# Install Fly CLI
fly version
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env  # Edit with your values
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local  # Edit with your values
npm run dev  # Runs on port 3000
```

### Full Stack with Docker Compose
```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mcpremote
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
  
  backend:
    build: 
      context: ./backend
      dockerfile: ../infrastructure/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@db/mcpremote
    depends_on:
      - db
  
  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend
```

```bash
docker-compose up
# Access at http://localhost:3000
```

## Base Docker Image for MCP Containers

```dockerfile
# infrastructure/docker/Dockerfile.base
FROM python:3.11-slim

# Install Node.js 20
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install mcp-proxy
RUN pip install --no-cache-dir "mcp-proxy>=0.10.0"

# Expose port for HTTP
EXPOSE 8080

# Default command (overridden by Fly.io config)
CMD ["mcp-proxy", "--host", "0.0.0.0", "--port", "8080", "--", "npx", "-y", "@modelcontextprotocol/server-everything"]
```

**Build and push:**
```bash
cd infrastructure/docker
docker build -t mcp-base:latest -f Dockerfile.base .
fly deploy --config ../fly/fly.base.toml
```
