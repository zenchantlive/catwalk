# MCP Remote Platform - Development Guide

## Development Philosophy

## Development Philosophy

This project follows **Pragmatic Quality** principles:

1. **Build Good Things**: Focus on delivering robust, high-quality features.
2. **Test What Matters**: Unit test critical logic, complex helpers, and key API endpoints.
3. **Verify Stability**: Ensure new changes don't break existing functionality (regressions).

**Why Pragmatic?**
- Speed: Don't get bogged down testing trivial implementations.
- Focus: Spend energy on complex, risky parts of the codebase.
- Quality: Smart engineers write good code; tests verify it.

## Testing Strategy

### Test Pyramid

```
         ┌─────────────┐
         │  E2E Tests  │  10% - Critical user flows
         │   (Slow)    │
         └─────────────┘
       ┌───────────────────┐
       │ Integration Tests │  30% - API endpoints
       │     (Medium)      │
       └───────────────────┘
    ┌─────────────────────────┐
    │     Unit Tests          │  60% - Services, utils
    │       (Fast)            │
    └─────────────────────────┘
```

### Coverage Goals
- **Unit tests:** >80% coverage
- **Integration tests:** >70% of API endpoints
- **E2E tests:** 100% of critical paths

---

## Backend Testing

### Unit Tests (Services)

**Example: Analysis Service**

```python
# tests/unit/services/test_analysis.py
import pytest
from unittest.mock import Mock, patch
from app.services.analysis import AnalysisService

@pytest.fixture
def mock_claude_client():
    with patch('app.clients.claude.ClaudeClient') as mock:
        yield mock

def test_analyze_repo_success(mock_claude_client):
    # Arrange
    service = AnalysisService()
    mock_claude_client.return_value.analyze.return_value = {
        "package_name": "@user/mcp-server",
        "env_vars": [...]
    }
    
    # Act
    result = await service.analyze_repo("https://github.com/user/repo")
    
    # Assert
    assert result.package_name == "@user/mcp-server"
    assert len(result.env_vars) > 0

def test_analyze_repo_invalid_url():
    # Arrange
    service = AnalysisService()
    
    # Act & Assert
    with pytest.raises(ValidationError):
        await service.analyze_repo("not-a-url")

def test_analyze_repo_claude_api_timeout(mock_claude_client):
    # Arrange
    service = AnalysisService()
    mock_claude_client.side_effect = TimeoutError()
    
    # Act & Assert
    with pytest.raises(AnalysisError):
        await service.analyze_repo("https://github.com/user/repo")
```

**Run unit tests:**
```bash
pytest tests/unit/ -v --cov=app --cov-report=html
```

---

### Integration Tests (API Endpoints)

**Example: Analyze Endpoint**

```python
# tests/integration/api/test_analyze.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_analyze_endpoint_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/analyze", json={
            "github_url": "https://github.com/user/mcp-server"
        })
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert "package_name" in data
    assert "env_vars" in data

@pytest.mark.asyncio
async def test_analyze_endpoint_invalid_url():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/analyze", json={
            "github_url": "not-a-valid-url"
        })
    
    assert response.status_code == 400
    assert "error" in response.json()

@pytest.mark.asyncio
async def test_analyze_endpoint_caching():
    # First request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post("/api/analyze", json={
            "github_url": "https://github.com/user/mcp-server"
        })
        
        # Second request (should hit cache)
        response2 = await client.post("/api/analyze", json={
            "github_url": "https://github.com/user/mcp-server"
        })
    
    assert response2.json()["data"]["cached"] == True
```

**Run integration tests:**
```bash
pytest tests/integration/ -v
```

---

### Test Fixtures

```python
# tests/fixtures.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Provide a clean database session for each test"""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test")
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_analysis():
    """Provide sample analysis data"""
    return {
        "package_name": "@test/mcp-server",
        "display_name": "Test MCP",
        "env_vars": [
            {"name": "API_KEY", "required": True, "secret": True}
        ],
        "run_command": "npx -y @test/mcp-server"
    }
```

---

## Frontend Testing

### Component Tests (React Testing Library)

**Example: GitHubUrlInput Component**

```typescript
// __tests__/components/GitHubUrlInput.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { GitHubUrlInput } from '@/components/GitHubUrlInput'

describe('GitHubUrlInput', () => {
  it('renders input field', () => {
    render(<GitHubUrlInput onSubmit={jest.fn()} />)
    expect(screen.getByPlaceholderText(/github url/i)).toBeInTheDocument()
  })

  it('validates URL format', async () => {
    render(<GitHubUrlInput onSubmit={jest.fn()} />)
    
    const input = screen.getByPlaceholderText(/github url/i)
    fireEvent.change(input, { target: { value: 'not-a-url' } })
    
    const submit = screen.getByRole('button', { name: /analyze/i })
    fireEvent.click(submit)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid github url/i)).toBeInTheDocument()
    })
  })

  it('submits valid URL', async () => {
    const onSubmit = jest.fn()
    render(<GitHubUrlInput onSubmit={onSubmit} />)
    
    const input = screen.getByPlaceholderText(/github url/i)
    fireEvent.change(input, { 
      target: { value: 'https://github.com/user/repo' } 
    })
    
    const submit = screen.getByRole('button', { name: /analyze/i })
    fireEvent.click(submit)
    
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith('https://github.com/user/repo')
    })
  })
})
```

**Run component tests:**
```bash
bun run test
```

---

### E2E Tests (Playwright)

**Example: Full Deployment Flow**

```typescript
// __tests__/e2e/deploy-flow.spec.ts
import { test, expect } from '@playwright/test'

test('complete deployment flow', async ({ page }) => {
  // Step 1: Enter GitHub URL
  await page.goto('http://localhost:3000')
  await page.fill('input[placeholder*="GitHub"]', 
    'https://github.com/modelcontextprotocol/servers/tree/main/src/everything')
  await page.click('button:has-text("Analyze")')

  // Step 2: Wait for analysis
  await expect(page.locator('text=Analysis complete')).toBeVisible({ timeout: 15000 })
  
  // Step 3: Verify detected configuration
  await expect(page.locator('text=Everything MCP')).toBeVisible()
  
  // Step 4: Enter credentials (mock for E2E)
  await page.fill('input[name="API_KEY"]', 'test-key-123')
  await page.click('button:has-text("Deploy")')
  
  // Step 5: Wait for deployment
  await expect(page.locator('text=Deploying')).toBeVisible()
  await expect(page.locator('text=Running')).toBeVisible({ timeout: 90000 })
  
  // Step 6: Verify URL displayed
  const urlElement = await page.locator('text=/https:\\/\\/.*\\/api\\/mcp\\/.*/')
  await expect(urlElement).toBeVisible()
  
  // Step 7: Copy URL
  await page.click('button:has-text("Copy URL")')
  await expect(page.locator('text=Copied')).toBeVisible()
})
```

**Run E2E tests:**
```bash
npx playwright test
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/test-and-deploy.yml
name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          cd backend
          pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: 'latest'
      - name: Install dependencies
        run: |
          cd frontend
          bun install --frozen-lockfile
      - name: Run tests
        run: |
          cd frontend
          bun run test -- --coverage

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E tests
        run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/

  deploy-backend:
    if: github.ref == 'refs/heads/main'
    needs: [backend-tests, frontend-tests, e2e-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --config infrastructure/fly/fly.backend.toml
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

  deploy-frontend:
    if: github.ref == 'refs/heads/main'
    needs: [backend-tests, frontend-tests, e2e-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: vercel/actions@v2
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
```

---

## Deployment Process

### Backend Deployment to Fly.io

```bash
# One-time setup
fly apps create mcp-remote-backend
fly secrets set MASTER_ENCRYPTION_KEY=$(openssl rand -base64 32)
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set FLY_API_TOKEN=fo1_...

# Deploy
cd backend
fly deploy --config ../infrastructure/fly/fly.backend.toml

# Check status
fly status
fly logs

# Scale (if needed)
fly scale count 2  # 2 instances
```

### Frontend Deployment to Vercel

```bash
# One-time setup
bun add -g vercel
cd frontend
vercel login
vercel link

# Deploy
vercel --prod

# Environment variables (in Vercel dashboard)
NEXT_PUBLIC_API_URL=https://mcp-remote-backend.fly.dev
```

### Base MCP Image Deployment

```bash
cd infrastructure/docker
docker build -t mcp-base:latest -f Dockerfile.base .
docker tag mcp-base:latest registry.fly.io/mcp-deployments:latest
fly auth docker
docker push registry.fly.io/mcp-deployments:latest
```

---

## Common Development Tasks

### Add a New API Endpoint

```bash
# 1. Implementation
touch backend/tests/integration/api/test_new_endpoint.py
# (Optional) Write test first if logic is complex, otherwise implementing first is fine.

# 2. Implement Feature
touch backend/app/api/new_endpoint.py
# ... write code ...

# 3. Verify
pytest backend/tests/integration/api/test_new_endpoint.py

# 6. Refactor if needed (tests still pass)
```

### Add a New Frontend Component

```bash
# 1. Implement component
touch frontend/components/NewComponent.tsx
# ... write code ...

# 2. Add verification test (if component has logic)
touch frontend/__tests__/components/NewComponent.test.tsx
bun run test NewComponent.test.tsx
```

### Database Migration

```bash
cd backend

# Create migration
alembic revision -m "add new column to deployments"

# Edit migration file in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Debug Deployment Issue

```bash
# Check backend logs
fly logs -a mcp-remote-backend

# SSH into machine
fly ssh console -a mcp-remote-backend

# Check specific deployment
fly logs -a mcp-deployments --instance {machine_id}

# Restart machine
fly machines restart {machine_id}
```

---

## Environment Setup Checklist

### Initial Setup (One-time)

- [ ] Clone repository
- [ ] Install Python 3.11+
- [ ] Install Node.js 20+
- [ ] Install Bun (frontend package manager)
- [ ] Install PostgreSQL 15+
- [ ] Install Fly CLI
- [ ] Create `.env` files from `.env.example`
- [ ] Run database migrations
- [ ] Install dependencies (pip + bun)
- [ ] Run tests to verify setup
- [ ] Start dev servers

### Daily Development

- [ ] Pull latest changes
- [ ] Check for dependency updates
- [ ] Check for dependency updates
- [ ] Create feature branch
- [ ] Implement feature (Write tests for critical logic)
- [ ] Run test suite to verify no regressions
- [ ] Commit with descriptive message
- [ ] Push and create PR
- [ ] Wait for CI to pass
- [ ] Merge to main

---

## Debugging Tips

### Backend Issues

**Problem: Database connection fails**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify connection string
echo $DATABASE_URL
```

**Problem: Claude API times out**
```python
# Add timeout logging
import logging
logger.setLevel(logging.DEBUG)

# Check API key
anthropic.debug = True
```

**Problem: Fly.io API returns 403**
```bash
# Verify token
fly auth whoami

# Check token permissions
curl -H "Authorization: Bearer $FLY_API_TOKEN" \
  https://api.machines.dev/v1/apps
```

### Frontend Issues

**Problem: API calls fail**
```typescript
// Enable request logging
console.log('API URL:', process.env.NEXT_PUBLIC_API_URL)

// Check CORS headers
fetch(url, { mode: 'cors' })
```

**Problem: Tests fail in CI but pass locally**
```bash
# Run tests in same environment as CI
docker-compose run --rm frontend bun run test
```

---

## Performance Monitoring

**Backend:**
- Request duration logged per endpoint
- Database query times tracked
- Claude API response times monitored

**Frontend:**
- Core Web Vitals tracked (Vercel Analytics)
- API call durations measured
- User flows timed

**[ASSUMPTION: For MVP, basic logging is sufficient. Phase 7+ adds Sentry, DataDog, or similar.]**
