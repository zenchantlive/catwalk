---
title: "Part 5: Authentication Hell - The 401 Marathon"
series: "Building Catwalk Live with AI Orchestration"
part: 5
date: 2025-12-20
updated: 2025-12-27
tags: [Authentication, JWT, Debugging, NextAuth, FastAPI, Secret Management]
reading_time: "11 min"
status: published
---

# Part 5: Authentication Hell - The 401 Marathon

**The Story So Far:** The pivot to open source required building a Settings page where users paste their own API keys. Simple, right?

**Narrator voice**: *It was not simple.*

## The Innocent Beginning

December 20, 2025. I tasked Claude Code with building Phase 0:

```
Build a Settings page for user API key management:
- User enters:
  - Fly.io API Token
  - OpenRouter API Key
  - Encryption Key (optional, auto-generated if empty)
- Store in PostgreSQL
- Encrypt sensitive values (Fernet)
- Backend API: CRUD for settings
- Frontend: Vercel-style .env paste UI
```

Claude Code generated:

```bash
commit 068dc28
Date: 2025-12-20

feat: Implement user settings for API key management with encryption,
centralized application configuration, and new authentication modules.
```

**What it created**:
- `backend/app/api/settings.py` - CRUD endpoints
- `backend/app/models/user_settings.py` - Settings model
- `frontend/app/settings/page.tsx` - Settings UI
- `backend/app/services/user_api_keys.py` - Encryption service

I deployed to Fly.io. Frontend loaded beautifully. I clicked "Settings."

```
HTTP 401 Unauthorized
```

## The First Debug: No JWT Token

I checked the browser console:

```javascript
Failed to fetch https://catwalk-backend.fly.dev/api/settings
Response: 401 Unauthorized
{
  "detail": "Not authenticated"
}
```

The Settings endpoint requires authentication:

```python
# backend/app/api/settings.py
from fastapi import Depends
from app.core.auth import get_current_user

@router.get("/api/settings")
async def get_settings(user: User = Depends(get_current_user)):
    # This dependency requires a valid JWT token
    pass
```

But the frontend wasn't sending any token.

I checked the API client:

```typescript
// frontend/lib/api.ts
export async function getSettings() {
  const response = await fetch(`${API_URL}/api/settings`)
  // No Authorization header!
  return response.json()
}
```

**AI mistake #1**: Generated authenticated endpoints but **didn't generate the token creation logic**.

I prompted: *"Add JWT token generation to the frontend auth flow"*

Claude Code added:

```typescript
// frontend/lib/auth.ts
import { getServerSession } from 'next-auth'

export async function createBackendAccessToken() {
  const session = await getServerSession()

  if (!session?.user) return null

  // Sign JWT token with AUTH_SECRET
  const token = await new SignJWT({ sub: session.user.email })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('24h')
    .sign(new TextEncoder().encode(process.env.AUTH_SECRET))

  return token
}
```

Updated API client:

```typescript
export async function getSettings() {
  const token = await createBackendAccessToken()

  const response = await fetch(`${API_URL}/api/settings`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  return response.json()
}
```

Redeployed.

Still: **401 Unauthorized**

## The Secret Mismatch Mystery

I added logging to the backend:

```python
# backend/app/core/auth.py
async def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET,  # ← What secret is this?
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidSignatureError:
        logger.error("JWT signature verification failed")
        raise HTTPException(status_code=401)
```

Backend logs showed:
```
JWT signature verification failed
```

**The signature didn't match.** That meant:
- Frontend signed the token with one secret
- Backend verified with a different secret

I checked my `.env` files:

**Frontend** (`.env.local`):
```bash
NEXTAUTH_SECRET=abc123...
```

**Backend** (Fly.io secrets):
```bash
fly secrets list --app catwalk-backend
```

```
AUTH_SECRET=xyz789...
```

**They were different.**

But wait - where was the frontend getting `AUTH_SECRET`?

I checked `frontend/lib/auth.ts` again:

```typescript
.sign(new TextEncoder().encode(process.env.AUTH_SECRET))
```

`process.env.AUTH_SECRET` was **undefined** because I had set `NEXTAUTH_SECRET`, not `AUTH_SECRET`.

NextAuth.js uses `NEXTAUTH_SECRET` by default. But my JWT signing code was looking for `AUTH_SECRET`.

**AI mistake #2**: Generated code referenced `AUTH_SECRET` but didn't validate it existed or match documentation.

## The Fix Attempt #1: Align Secrets

I updated `.env.local`:

```bash
# Frontend .env.local
AUTH_SECRET=xyz789...  # Match backend
NEXTAUTH_SECRET=xyz789...  # Keep for NextAuth
```

Updated Fly.io backend:

```bash
fly secrets set AUTH_SECRET=xyz789... --app catwalk-backend
```

Redeployed both.

Still: **401 Unauthorized**

**What!?**

## The Debugging Rabbit Hole

I added more logging:

**Frontend**:
```typescript
const token = await createBackendAccessToken()
console.log('Token generated:', token)
console.log('Secret used:', process.env.AUTH_SECRET?.slice(0, 10))
```

**Backend**:
```python
@router.get("/api/settings")
async def get_settings(authorization: str = Header(None)):
    logger.info(f"Received token: {authorization[:50]}...")
    logger.info(f"Secret: {settings.AUTH_SECRET[:10]}...")
```

Frontend output:
```
Token generated: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Secret used: xyz789abcd
```

Backend logs:
```
Received token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Secret: xyz789abcd
```

**Secrets matched.** Token was being sent. Backend received it.

But still: **JWT signature verification failed**

## The JWT Debugging Tool

I created a debug script to decode the token manually:

```javascript
// debug-jwt.mjs
import jwt from 'jsonwebtoken'

const token = process.argv[2]
const secret = process.argv[3]

try {
  const decoded = jwt.verify(token, secret)
  console.log('✅ Token valid:', decoded)
} catch (error) {
  console.log('❌ Token invalid:', error.message)
}
```

Tested locally:

```bash
node debug-jwt.mjs "eyJhbGci..." "xyz789..."
```

```
❌ Token invalid: invalid signature
```

**The token was genuinely invalid.** But why?

I tried signing and verifying in the same script:

```javascript
const secret = 'xyz789abcd'

const token = jwt.sign({ sub: 'test@example.com' }, secret)
console.log('Token:', token)

const decoded = jwt.verify(token, secret)
console.log('Decoded:', decoded)
```

```
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Decoded: { sub: 'test@example.com', iat: 1703098765 }
```

**It worked.** Same secret for signing and verification = valid token.

**Then why was the frontend → backend flow failing?**

## The Breakthrough: User Not Synced

I added a database query to the backend:

```python
@router.get("/api/settings")
async def get_settings(user: User = Depends(get_current_user)):
    logger.info(f"Authenticated user: {user.email}")
    # Fetch settings...
```

But `get_current_user` was failing before reaching this line.

I checked the dependency:

```python
# backend/app/core/auth.py
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_jwt_token(token)  # This worked now
    email = payload.get("sub")

    # Look up user in database
    user = await db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
```

**The user didn't exist in the database.**

The JWT token was **valid**, but the user it referenced (`test@example.com`) had never been synced to the PostgreSQL database.

**AI mistake #3**: Generated authentication flow but **didn't implement the user sync** between NextAuth (frontend session) and PostgreSQL (backend users).

## The Missing Piece: User Sync Endpoint

I needed an endpoint that NextAuth calls after sign-in to create/update users in PostgreSQL.

I prompted Claude Code:

```
Add a user sync endpoint:
- POST /api/auth/sync-user
- Called by NextAuth signIn callback
- Creates or updates user in PostgreSQL
- Secured with AUTH_SYNC_SECRET (different from AUTH_SECRET)
```

Claude Code generated:

```python
# backend/app/api/auth.py
@router.post("/api/auth/sync-user")
async def sync_user(
    user_data: dict,
    x_auth_secret: str = Header(None)
):
    # Verify request is from our frontend
    if x_auth_secret != settings.AUTH_SYNC_SECRET:
        raise HTTPException(status_code=403, detail="Invalid sync secret")

    # Create or update user
    user = await db.query(User).filter(User.email == user_data["email"]).first()

    if not user:
        user = User(email=user_data["email"], name=user_data.get("name"))
        db.add(user)
    else:
        user.name = user_data.get("name")
        user.updated_at = datetime.utcnow()

    await db.commit()
    return {"status": "synced"}
```

**Frontend** (`frontend/auth.ts`):

```typescript
import { AuthOptions } from 'next-auth'

export const authOptions: AuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET
    })
  ],

  callbacks: {
    async signIn({ user }) {
      // Sync user to backend
      await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/auth/sync-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Secret': process.env.AUTH_SYNC_SECRET
        },
        body: JSON.stringify({
          email: user.email,
          name: user.name
        })
      })

      return true
    }
  }
}
```

**Two secrets now**:
1. **AUTH_SECRET**: Signs/verifies JWT tokens (must match frontend ↔ backend)
2. **AUTH_SYNC_SECRET**: Secures the sync endpoint (prevents unauthorized user creation)

I set both in `.env.local` and Fly.io:

```bash
# Frontend
AUTH_SECRET=xyz789...
AUTH_SYNC_SECRET=abc123...

# Backend
fly secrets set AUTH_SECRET=xyz789... --app catwalk-backend
fly secrets set AUTH_SYNC_SECRET=abc123... --app catwalk-backend
```

Redeployed.

Signed in with Google.

**Finally**: Settings page loaded ✅

## The Hidden Gotcha: Environment Variable Timing

Everything worked... on the first deploy after setting secrets.

But when I redeployed the backend (for unrelated changes), **401 errors returned**.

Logs showed:
```
AUTH_SYNC_SECRET: None
```

**The secret disappeared.**

**The problem**: Fly.io secrets are only available **after setting them manually**. They don't persist in Fly.io configuration files.

If you:
1. Set secret: `fly secrets set AUTH_SECRET=...`
2. Deploy code
3. Destroy app
4. Recreate app
5. Deploy code

**The secret is gone.** You must re-set it.

**The fix**: I created a deployment script:

```bash
#!/bin/bash
# deploy-backend.sh

# Check secrets exist
AUTH_SECRET=$(fly secrets list --app catwalk-backend | grep AUTH_SECRET)

if [ -z "$AUTH_SECRET" ]; then
  echo "❌ AUTH_SECRET not set! Run:"
  echo "fly secrets set AUTH_SECRET=<value> --app catwalk-backend"
  exit 1
fi

# Deploy
fly deploy --app catwalk-backend
```

**Lesson**: AI-generated infrastructure code assumes secrets exist. **You must validate environment setup before deployment.**

## Creating AUTH_TROUBLESHOOTING.md

After 2 days of debugging, I had learned:
- JWT secret mismatches cause invalid signatures
- User sync is critical for authentication to work
- Multiple secrets serve different purposes
- Environment variable timing matters

I documented everything:

```bash
commit a8dfde6
Date: 2025-12-21

feat(auth): Fix 401 errors and add comprehensive authentication
troubleshooting
```

**Created**: `context/AUTH_TROUBLESHOOTING.md`

```markdown
# Authentication Troubleshooting Guide

## Quick Diagnosis

**Symptom**: 401 Unauthorized on /api/settings

**Check**:
1. Is AUTH_SECRET set on both frontend and backend?
2. Do the values match EXACTLY?
3. Has the user been synced to the database?
4. Is AUTH_SYNC_SECRET set?

## Common Issues

### Issue 1: JWT Signature Invalid

**Cause**: AUTH_SECRET mismatch between frontend and backend

**Fix**:
```bash
# Generate matching secret
SECRET=$(openssl rand -base64 32)

# Frontend
echo "AUTH_SECRET=\"$SECRET\"" >> .env.local

# Backend
fly secrets set AUTH_SECRET="$SECRET" --app catwalk-backend
```

### Issue 2: User Not Found

**Cause**: User never synced to PostgreSQL

**Check**:
```sql
SELECT * FROM users WHERE email = 'your@email.com';
```

If empty, sync is broken.

**Fix**: Verify AUTH_SYNC_SECRET is set and signIn callback is firing.

### Issue 3: Secrets Disappeared After Redeploy

**Cause**: Fly.io secrets don't persist in config files

**Fix**: Always check secrets before deploying:
```bash
fly secrets list --app catwalk-backend
```
```

This became **the most referenced document** during onboarding contributors.

## PR #10: The Big Authentication Fix

All the fixes were bundled into Pull Request #10:

```bash
commit 945b055
Date: 2025-12-21

Fix code review issues: auth safety, migration defaults, modal URLs
```

**What it included**:
- ✅ Consolidated auth modules (removed duplicate middleware)
- ✅ Fixed JWT secret handling (AUTH_SECRET everywhere)
- ✅ User sync endpoint (with AUTH_SYNC_SECRET)
- ✅ Database timestamp fixes (func.now() instead of Python datetime)
- ✅ Alembic migration updates (proper foreign key constraints)
- ✅ AUTH_TROUBLESHOOTING.md guide

**Test results after PR #10**:
```bash
pytest
```

```
51 tests passed ✅
0 warnings
```

**Frontend type check**:
```bash
bun run typecheck
```

```
0 errors ✅
```

**Authentication flow**:
1. User signs in with Google ✅
2. NextAuth signIn callback fires ✅
3. Frontend calls `/api/auth/sync-user` with AUTH_SYNC_SECRET ✅
4. Backend creates/updates user in PostgreSQL ✅
5. Frontend creates JWT token signed with AUTH_SECRET ✅
6. Backend verifies JWT with AUTH_SECRET ✅
7. Settings page loads ✅

**Total time debugging auth**: ~16 hours over 2 days

**AI contribution**: Generated base authentication code, but missed:
- User sync logic
- Secret validation
- Environment variable checks
- Timing issues (secrets not persisting)

**Human contribution**: Everything. This was pure manual debugging.

## What AI Can't Debug

### 1. Environment Configuration

AI can generate:
```python
secret = os.getenv("AUTH_SECRET")
```

AI **cannot**:
- Verify the secret is set in your `.env.local`
- Check if Fly.io secrets are configured
- Validate secrets match across environments
- Detect when secrets are undefined vs empty string

**Why?** AI only sees code, not runtime environment.

### 2. Cross-System Integration

AI can generate:
- NextAuth configuration ✅
- FastAPI authentication middleware ✅
- JWT signing and verification ✅

AI **cannot**:
- Validate the *flow* works end-to-end
- Detect missing sync between NextAuth session and PostgreSQL
- Understand timing (when callbacks fire, when secrets are available)

**Why?** Integration bugs span multiple systems AI can't execute.

### 3. Secret Lifecycle

AI can generate:
```bash
fly secrets set AUTH_SECRET=...
```

AI **cannot**:
- Remember you need to run this command
- Detect when secrets are missing
- Warn that secrets don't persist in config files
- Validate secrets are set before deployment

**Why?** Infrastructure state is invisible to AI.

## What You Must Bring

**As an AI orchestrator, debugging environment issues requires:**

1. **Infrastructure knowledge**:
   - How Fly.io secrets work
   - Environment variable precedence (`.env.local` vs runtime)
   - When secrets are loaded (build time vs runtime)

2. **Systematic debugging**:
   - Add logging at every layer
   - Test each component in isolation
   - Validate assumptions (secrets exist, values match, user synced)

3. **Documentation discipline**:
   - Write troubleshooting guides as you debug
   - Make implicit knowledge explicit
   - Help future you (and contributors) avoid repeating this

4. **Cross-system thinking**:
   - Trace the full request flow (frontend → backend → database)
   - Identify where data transforms (session → JWT → user lookup)
   - Verify every handoff point

**AI helps you write the code. You debug the world it runs in.**

## Key Metrics: The Authentication Gauntlet

**Time Debugging**: 16 hours (Dec 20-21)
- Secret mismatch troubleshooting: 4 hours
- User sync investigation: 6 hours
- Environment variable issues: 3 hours
- Testing and validation: 2 hours
- Writing AUTH_TROUBLESHOOTING.md: 1 hour

**Commits**:
- `068dc28` - Initial Settings implementation (AI-generated, broken)
- `89478a0` - Fix auth sync secret
- `46d8576` - Harden auth binding
- `945b055` - Final auth safety fixes (PR #10)

**AI Contribution**: ~30% (generated base code)
**Human Contribution**: ~70% (debugging, environment setup, testing)

**Lines of Code**:
- Added: ~800 (auth modules, Settings API, frontend UI)
- Changed: ~300 (secret handling, user sync)
- Deleted: ~200 (duplicate auth middleware, broken code)

**Documentation**:
- `AUTH_TROUBLESHOOTING.md`: 600 words
- Updated `AGENTS.md` with auth protocols: 200 words
- Updated `CURRENT_STATUS.md`: 150 words

## The Lesson

**AI is phenomenal at generating code patterns it's seen before.**

JWT authentication? ✅ Training data has millions of examples.
FastAPI middleware? ✅ Common pattern.
NextAuth configuration? ✅ Well-documented.

**AI is terrible at:**
- Debugging environment-specific failures
- Validating cross-system integration
- Detecting missing configuration
- Understanding secret lifecycle

**Your job as orchestrator**:
- Generate code with AI (fast)
- Test in real environments (slow)
- Debug integration issues (manual)
- Document solutions (essential)

**The ratio**: For every 1 hour AI saves on coding, expect to spend 0.5-1 hour debugging environment and integration issues.

Still a **massive productivity gain** - but not "push button, receive working system."

## Coming Next

In **Part 6**, security enters the spotlight:
- Automated PR review agents (CodeRabbit, Qodo, Gemini Code Assist)
- Command injection risks AI missed
- Package validation (npm/PyPI registry checks)
- Comprehensive test suite expansion
- Access token rotation for security
- PR #13: Security hardening

**Spoiler**: AI wrote code with a **critical security flaw** that would've allowed arbitrary code execution. Only automated security review agents caught it.

---

**Commit References**:
- `068dc28` - Initial Settings implementation
- `a8dfde6` - Auth troubleshooting guide
- `945b055` - Auth safety fixes (PR #10)
- `efbac5c` - JWT auth implementation

**Documents Created**:
- `context/AUTH_TROUBLESHOOTING.md`
- Updated: `AGENTS.md`, `CURRENT_STATUS.md`

**Debugging Tools**:
- `debug-jwt.mjs` - Manual JWT verification
- `test-jwt-match.sh` - Secret validation script

**Code**:
- [backend/app/core/auth.py](https://github.com/zenchantlive/catwalk/blob/main/backend/app/core/auth.py)
- [frontend/lib/auth.ts](https://github.com/zenchantlive/catwalk/blob/main/frontend/lib/auth.ts)
- [context/AUTH_TROUBLESHOOTING.md](https://github.com/zenchantlive/catwalk/blob/main/context/AUTH_TROUBLESHOOTING.md)

---

*This is Part 5 of 7. Authentication works, but AI missed something critical...*

**Previous**: [← Part 4: The Pivot](04-pivot-saas-to-open-source.md)
**Next**: [Part 6: Security Awakening →](06-security-awakening-what-ai-missed.md)
