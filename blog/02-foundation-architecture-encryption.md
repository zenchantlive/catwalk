---
title: "Part 2: Foundation - Architecture & Encryption"
series: "Catwalk Live Development Journey"
part: 2
date: 2025-12-11
updated: 2025-12-27
tags: [architecture, encryption, database, security, forms]
reading_time: "10 min"
commits_covered: "b92443c...f5a957a"
---

## Where We Are

Day 1, afternoon. The repository exists. The vision is clear. Now comes the hard part: **designing the foundational architecture that everything else builds on**.

Get this wrong, and you'll refactor painfully later. Get it right, and features flow naturally.

## The Challenge

Catwalk Live needs to handle a deceptively complex flow:

1. **Accept** GitHub URLs from users
2. **Analyze** repositories with AI to extract MCP configuration
3. **Generate** dynamic credential forms based on what the analysis found
4. **Encrypt** sensitive credentials before storage
5. **Store** deployments and credentials in a database
6. **Deploy** isolated containers with injected environment variables
7. **Expose** stable MCP endpoints that Claude can connect to

Each step has security implications. Each step can fail. The architecture needs to be **resilient, secure, and maintainable**.

## Core Architecture: Three Services

I designed the backend around three core services:

### 1. Analysis Service
**Responsibility**: Take a GitHub URL, extract MCP server configuration

```python
class AnalysisService:
    async def analyze_repo(self, repo_url: str) -> AnalysisResult:
        """
        Use Claude API (via OpenRouter) to:
        - Fetch repository README and package.json
        - Extract package name (npm or PyPI)
        - Identify required environment variables
        - List available tools, resources, prompts
        """
        pass
```

**Why separate**: Analysis is stateless, cacheable, and independent of deployments. It should work even if the database is down.

### 2. Credential Service
**Responsibility**: Encrypt and decrypt credentials securely

```python
from cryptography.fernet import Fernet

class CredentialService:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())

    def encrypt_credentials(self, creds: dict) -> bytes:
        """Encrypt credentials for storage"""
        json_str = json.dumps(creds)
        return self.cipher.encrypt(json_str.encode())

    def decrypt_credentials(self, encrypted: bytes) -> dict:
        """Decrypt credentials (only during deployment)"""
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())
```

**Why Fernet**: Symmetric encryption, well-audited, includes authentication (prevents tampering), simple API.

**Critical security pattern**:
- Credentials encrypted **before** hitting the database
- Decrypted **only** in memory during deployment
- Never logged, never returned in API responses
- Master key stored in Fly.io secrets (not in code)

### 3. Deployment Service
**Responsibility**: Orchestrate the entire deployment lifecycle

```python
class DeploymentService:
    async def create_deployment(
        self,
        name: str,
        repo_url: str,
        credentials: dict
    ) -> Deployment:
        """
        1. Retrieve cached analysis
        2. Validate credentials against analysis schema
        3. Encrypt credentials
        4. Store deployment in database
        5. Trigger container deployment (Fly.io)
        6. Return deployment info
        """
        pass
```

**Why orchestrate**: Deployment involves multiple steps across multiple systems. If any step fails, we need clear error messages and rollback capability.

## Database Schema: Simple But Powerful

AI agents suggested complex schemas. I kept it simple:

### Deployments Table

```sql
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'deploying', 'running',
        'stopped', 'failed'
    )),
    machine_id TEXT UNIQUE,  -- Fly.io machine ID
    schedule_config JSONB NOT NULL,  -- {mcp_config: {package, tools, env_vars}}
    connection_url TEXT,  -- e.g., "https://backend.fly.dev/api/mcp/{id}"
    access_token TEXT,  -- For MCP endpoint authentication
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX idx_deployments_user_id ON deployments(user_id);
CREATE INDEX idx_deployments_status ON deployments(status);
```

**Design decisions**:

1. **`schedule_config` as JSONB**: Flexible schema - different MCP servers need different configs. PostgreSQL's JSONB lets us query this later if needed.

2. **`status` with CHECK constraint**: Explicit states prevent invalid transitions. Can't accidentally set status to "bananas".

3. **`machine_id` UNIQUE**: Each deployment gets one machine. Constraint prevents duplicate deployments.

4. **`connection_url` denormalized**: Could compute from ID, but storing it makes API responses faster.

5. **`access_token` for auth**: Each deployment gets a unique token. Prevents unauthorized MCP access.

### Credentials Table

```sql
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID NOT NULL UNIQUE REFERENCES deployments(id) ON DELETE CASCADE,
    encrypted_data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Why separate table**:
- Credentials are sensitive - separate table, separate access controls
- `ON DELETE CASCADE` - deleting deployment deletes credentials automatically
- `UNIQUE` constraint on `deployment_id` - one credential set per deployment

### Analysis Cache Table

```sql
CREATE TABLE analysis_cache (
    id SERIAL PRIMARY KEY,
    repo_url TEXT NOT NULL UNIQUE,
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_cache_expires ON analysis_cache(expires_at);
```

**Why cache**: Claude API costs money. If 10 users analyze the same repo, run analysis once, cache for 24 hours.

**Expiration strategy**: Simple TTL. Background job could clean expired entries, but PostgreSQL query `WHERE expires_at > NOW()` is fast enough.

## Dynamic Form Generation: The Magic

Here's a cool part: **forms that generate themselves based on AI analysis**.

User analyzes `github.com/user/mcp-ticktick`. Claude extracts:

```json
{
  "package": "@hong-hao/mcp-ticktick",
  "env_vars": [
    {
      "name": "TICKTICK_TOKEN",
      "description": "Your TickTick API token",
      "required": true,
      "secret": true
    }
  ]
}
```

Frontend receives this and **generates a form dynamically**:

```typescript
// frontend/components/dynamic-form/FormBuilder.tsx
export function FormBuilder({ envVars }: { envVars: EnvVar[] }) {
  const schema = generateZodSchema(envVars);
  const form = useForm({ resolver: zodResolver(schema) });

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {envVars.map(envVar => (
        <FormField
          key={envVar.name}
          name={envVar.name}
          label={envVar.description}
          type={envVar.secret ? "password" : "text"}
          required={envVar.required}
        />
      ))}
      <Button type="submit">Deploy</Button>
    </form>
  );
}
```

**Why this works**:
- No hardcoded forms - adapts to any MCP server
- Type-safe (Zod schema generated from analysis)
- Required fields enforced client-side and server-side
- Secrets automatically use password inputs

**The Zod schema generation** (this was AI-generated and it's beautiful):

```typescript
function generateZodSchema(envVars: EnvVar[]): z.ZodObject<any> {
  const shape: Record<string, z.ZodString> = {};

  envVars.forEach(envVar => {
    let field = z.string();

    if (envVar.required) {
      field = field.min(1, `${envVar.name} is required`);
    }

    if (envVar.name.includes('URL')) {
      field = field.url('Must be a valid URL');
    }

    shape[envVar.name] = field;
  });

  return z.object(shape);
}
```

AI-generated validation that actually works. This is where AI shines: boilerplate that follows clear patterns.

## Aurora UI: The Design System

The frontend needed to feel modern, trustworthy, and **fast**. We landed on "Aurora" - a glassmorphic design system inspired by Vercel but with more color.

**Design principles**:

1. **Glassmorphism**: Semi-transparent panels with backdrop blur
2. **Gradient accents**: Purple-to-blue gradients for CTAs
3. **Dark-first**: Dark mode by default (developers love dark mode)
4. **Fast animations**: 150ms transitions, nothing slower
5. **Accessible**: WCAG AA contrast ratios, keyboard navigation

**Key components** (all AI-generated, then refined):

```tsx
// Button with gradient
<Button variant="gradient">
  Deploy to Cloud
</Button>

// Glassmorphic card
<Card className="glass">
  <CardHeader>
    <CardTitle>Deployment Status</CardTitle>
  </CardHeader>
  <CardContent>
    {/* ... */}
  </CardContent>
</Card>

// Status badges
<Badge status="running">Running</Badge>
<Badge status="failed">Failed</Badge>
```

**TailwindCSS 4 configuration**:

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      backdropBlur: {
        xs: '2px',
      },
      colors: {
        glass: 'rgba(255, 255, 255, 0.1)',
        'glass-border': 'rgba(255, 255, 255, 0.2)',
      },
    },
  },
};
```

**Result**: A UI that feels premium without being over-designed. Clean, modern, functional.

## What I Learned: AI's Strengths and Gaps

### Where AI Excelled ✅

1. **Database migrations**: Generated Alembic migrations perfectly from schema changes
2. **Form components**: Dynamic form builder worked first try
3. **Type definitions**: TypeScript types from Pydantic schemas
4. **Boilerplate**: FastAPI route structure, React component scaffolding

### Where AI Struggled ❌

1. **Security edge cases**: Didn't validate package names initially (command injection risk)
2. **Async patterns**: Race conditions in concurrent analysis requests
3. **Database constraints**: Suggested overly complex foreign key relationships
4. **Design decisions**: No opinion on "should this be one table or two?"

**The pattern**: AI is great at **implementation** of decisions you've made. It's weak at **making** those decisions.

## The Foundation in Numbers

At the end of day 1:

- **Commits**: 6 (b92443c → f5a957a)
- **Database tables**: 4 (users, deployments, credentials, analysis_cache)
- **API endpoints**: 8 (analyze, deployments CRUD, forms)
- **Frontend pages**: 3 (landing, dashboard, configure)
- **Lines of code**: ~1,200 (backend + frontend)
- **Tests**: 0 (we'll regret this later)
- **Security vulnerabilities**: At least 2 (we'll find them later)

**Status**: Foundation complete, but untested. Time to build on it.

## Up Next

The architecture is solid. The database is designed. Forms are dynamic. Encryption is working.

But there's a critical missing piece: **the AI analysis engine**. How do you actually get Claude to analyze an arbitrary GitHub repository and extract MCP configuration?

That's Part 3: The AI Analysis Engine.

---

**Key Commits**:
- `b92443c` - Initialize Phase 3 Credential Management
- `4d6b32b` - Credential Management Foundation and Dynamic Forms
- `a06d684` - Centralized form schemas and error handling
- `f5a957a` - Implement Aurora UI

**Related Files**:
- `backend/app/models/` - Database models
- `backend/app/services/credential_service.py` - Encryption service
- `frontend/components/dynamic-form/` - Dynamic forms

**Next Post**: [Part 3: The AI Analysis Engine](03-ai-analysis-engine.md)
