# Local Development Setup

Complete guide to running Catwalk Live locally.

## Prerequisites

- **Node.js** 20+ ([Download](https://nodejs.org/))
- **Bun** 1.0+ ([Install](https://bun.sh/))
- **Python** 3.12+ ([Download](https://www.python.org/downloads/))
- **PostgreSQL** 15+ ([Download](https://www.postgresql.org/download/)) OR use SQLite for dev
- **Git** ([Download](https://git-scm.com/downloads))

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/zenchantlive/catwalk.git
cd catwalk/catwalk-live
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your API keys:
# - OPENROUTER_API_KEY (get from https://openrouter.ai/keys)
# - ENCRYPTION_KEY (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# - DATABASE_URL (optional, defaults to SQLite)

# Run database migrations (from project root)
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload
```

Backend will be available at: **http://localhost:8000**

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
bun install

# Create environment file
cp .env.local.example .env.local

# Edit .env.local and set:
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/:path*

# Start frontend dev server
bun run dev
```

Frontend will be available at: **http://localhost:3000**

## Database Options

### Option A: SQLite (Default, Easiest)

No setup needed! The backend defaults to SQLite for local development.

### Option B: PostgreSQL (Production-like)

1. **Install PostgreSQL** 15+
2. **Create database**:
   ```bash
   createdb mcp_remote
   ```
3. **Set DATABASE_URL in `.env`**:
   ```
   DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/mcp_remote
   ```
4. **Run migrations (from project root)**:
   ```bash
   alembic upgrade head
   ```

## Generating API Keys

### OpenRouter API Key (Required)

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Navigate to [Keys](https://openrouter.ai/keys)
3. Create a new key
4. Add to `backend/.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

### Encryption Key (Required)

Generate a Fernet encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `backend/.env`:
```
ENCRYPTION_KEY=<generated-key>
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest                 # Run all tests
pytest tests/unit/     # Run unit tests only
pytest -v              # Verbose output
pytest --cov           # With coverage report
```

### Frontend Tests

```bash
cd frontend
bun run test           # Run all tests
bun run test --ui      # Open Vitest UI
bun run test --coverage # With coverage report
```

## Code Quality Checks

### Backend (Python)

```bash
cd backend
ruff check .           # Lint
ruff format .          # Format
pytest                 # Test
```

### Frontend (TypeScript)

```bash
cd frontend
bun run typecheck      # Type checking
bun run lint           # ESLint
bun run test           # Vitest
```

## Troubleshooting

### "Module not found" errors (Backend)

Make sure virtual environment is activated:
```bash
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

Then reinstall dependencies:
```bash
pip install -r requirements.txt
```

### "Connection refused" (Frontend → Backend)

1. Check backend is running: `http://localhost:8000/api/health`
2. Verify `NEXT_PUBLIC_API_URL` in frontend `.env.local`
3. Check for port conflicts (kill processes on 8000/3000)

### Database migration errors

Reset database:
```bash
# Delete existing migrations
rm -rf alembic/versions/*.py

# Recreate from scratch (from project root)
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### Windows-specific issues

**Subprocess spawning doesn't work on Windows** (Python asyncio limitation).

**Solution**: Run backend in WSL2 for MCP server subprocess testing.

## Next Steps

- Read `AGENTS.md` for AI agent specifications
- Read `context/ARCHITECTURE.md` for system design
- Read `CLAUDE.md` for deployment lessons learned
- Check `context/CURRENT_STATUS.md` for current project status

## Getting Help

- Open an issue on GitHub
- Read existing issues for common problems
- Check the `/context` directory for detailed documentation

Happy coding! 🚀
