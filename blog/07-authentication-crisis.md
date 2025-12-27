---
title: "Part 7: The Authentication Nightmare"
series: "Catwalk Live Development Journey"
part: 7
date: 2025-12-20
updated: 2025-12-27
tags: [authentication, jwt, nextauth, debugging, crisis]
reading_time: "15 min"
commits_covered: "068dc28...a8dfde6"
---

## The Dark Before the Dawn

December 20, 2025. The platform works beautifully:
- ✅ Analysis engine extracts MCP config
- ✅ Validation prevents security holes
- ✅ Deployments create Fly machines
- ✅ Streamable HTTP proxies to MCP servers
- ✅ Claude successfully calls tools

There's just one tiny problem: **Anyone can deploy anything**.

No user accounts. No authentication. No authorization. Just... open endpoints.

Time to fix that. How hard could authentication be?

## Attempt 1: NextAuth.js Setup

AI (Claude Code) suggested NextAuth.js (now "Auth.js"):

```typescript
// frontend/auth.ts
import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    })
  ],
  callbacks: {
    async signIn({ user, account }) {
      // Sync user to backend database
      // TODO: Implement this
      return true
    }
  }
})
```

Deployed. Sign-in modal works. Google OAuth succeeds. User sees their email in the navbar.

**Perfect! Ship it.**

## The 401 Error Wall

December 20, 3 PM. First real test: create a deployment.

```
POST /api/deployments
Authorization: Bearer <jwt>

Response: 401 Unauthorized
```

**What?** The user is signed in. The JWT is in the header. Why 401?

Checked backend logs:

```
2025-12-20T15:23:45Z [error] JWT verification failed: Invalid signature
```

**The problem**: Frontend generates JWT. Backend verifies JWT. They're using **different secrets**.

**Frontend** (`.env.local`):
```
AUTH_SECRET=abc123...
```

**Backend** (Fly.io secrets):
```
AUTH_SECRET=xyz789...
```

**The fix**: Make sure secrets **match exactly**.

```bash
# Generate secret once
AUTH_SECRET=$(openssl rand -base64 32)

# Set on backend
fly secrets set AUTH_SECRET="$AUTH_SECRET" --app catwalk-backend

# Set on frontend (.env.local)
echo "AUTH_SECRET=\"$AUTH_SECRET\"" >> frontend/.env.local
```

Redeployed. Tried again:

```
POST /api/deployments
Authorization: Bearer <jwt>

Response: 401 Unauthorized
```

**Still broken.** Different error:

```
2025-12-20T16:05:12Z [error] User not found in database: user@example.com
```

## The Silent User Sync Failure

**What happened**: User signed in via Google OAuth. Frontend has user info. But backend **has no record of this user**.

**Why**: The `signIn` callback that should sync users to the backend... wasn't implemented.

**AI's generated code**:

```typescript
async signIn({ user, account }) {
  // TODO: Sync user to backend database
  return true
}
```

Literally a TODO. **And I shipped it.**

**Lesson 1**: Never skip TODOs. Always verify AI-generated code is complete.

**The fix**: Implement user sync.

```typescript
// frontend/auth.ts
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google(...)],
  callbacks: {
    async signIn({ user, account }) {
      // Sync user to backend
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/auth/sync-user`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Auth-Secret": process.env.AUTH_SYNC_SECRET!
            },
            body: JSON.stringify({
              email: user.email,
              name: user.name,
              provider: account.provider,
              provider_id: account.providerAccountId
            })
          }
        );

        if (!response.ok) {
          console.error("User sync failed:", await response.text());
          return false;  // Block sign-in if sync fails
        }

        return true;
      } catch (error) {
        console.error("User sync error:", error);
        return false;
      }
    }
  }
})
```

**Backend endpoint**:

```python
# backend/app/api/auth.py
from fastapi import APIRouter, HTTPException, Header

router = APIRouter()

@router.post("/auth/sync-user")
async def sync_user(
    email: str,
    name: str,
    provider: str,
    provider_id: str,
    x_auth_secret: str = Header(None, alias="X-Auth-Secret")
):
    """
    Sync user from frontend to backend database.

    Called by NextAuth.js after successful OAuth sign-in.

    Security: Protected by AUTH_SYNC_SECRET header.
    """

    # Verify sync secret
    if x_auth_secret != settings.AUTH_SYNC_SECRET:
        raise HTTPException(403, "Invalid auth sync secret")

    # Create or update user
    async with get_session() as db:
        user = await db.execute(
            select(User).where(User.email == email)
        )
        user = user.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                email=email,
                name=name,
                provider=provider,
                provider_id=provider_id
            )
            db.add(user)
        else:
            # Update existing user
            user.name = name

        await db.commit()
        return {"id": str(user.id), "email": user.email}
```

Deployed. Signed in. Checked logs:

```
2025-12-20T17:30:22Z [info] User synced: user@example.com
```

**Success!** User now exists in database.

Tried creating a deployment:

```
POST /api/deployments
Authorization: Bearer <jwt>

Response: 401 Unauthorized
```

**STILL BROKEN.**

## The Great Secret Confusion

December 20, 6 PM. I'm debugging for 3 hours. The error:

```
2025-12-20T18:45:33Z [error] JWT verification failed: Invalid signature
```

But the `AUTH_SECRET` matches! I've checked 10 times!

**Then I noticed**: Two different secrets in the environment variables.

**Frontend `.env.local`**:
```
AUTH_SECRET=abc123...
AUTH_SYNC_SECRET=def456...
```

**Backend Fly.io**:
```
AUTH_SECRET=xyz789...
AUTH_SYNC_SECRET=def456...
```

**The problem**: `AUTH_SECRET` still didn't match. I had set `AUTH_SYNC_SECRET` correctly but never updated `AUTH_SECRET` on the backend.

**The confusion**: Two secrets with similar names:
1. **`AUTH_SECRET`**: Signs/verifies JWT tokens for API authentication
2. **`AUTH_SYNC_SECRET`**: Secures the `/auth/sync-user` endpoint

**Why two secrets?**:
- `AUTH_SECRET` must be shared between frontend and backend (JWT verification)
- `AUTH_SYNC_SECRET` is server-to-server only (prevents external calls to sync endpoint)

**The fix** (for real this time):

```bash
# Generate BOTH secrets
AUTH_SECRET=$(openssl rand -base64 32)
AUTH_SYNC_SECRET=$(openssl rand -base64 32)

# Set on backend
fly secrets set \
  AUTH_SECRET="$AUTH_SECRET" \
  AUTH_SYNC_SECRET="$AUTH_SYNC_SECRET" \
  --app catwalk-backend

# Set on frontend
cat >> frontend/.env.local <<EOF
AUTH_SECRET="$AUTH_SECRET"
AUTH_SYNC_SECRET="$AUTH_SYNC_SECRET"
EOF
```

Redeployed both frontend and backend. Signed in. Tried creating a deployment:

```
POST /api/deployments
Authorization: Bearer <jwt>

Response: 201 Created
{
  "id": "...",
  "name": "My TickTick",
  "status": "deploying"
}
```

**IT WORKS!** After 4 hours of debugging.

## The Authentication Flow (Final)

Here's the complete flow that finally worked:

### Step 1: User Signs In

```
User clicks "Sign in with Google"
  ↓
NextAuth.js redirects to Google OAuth
  ↓
User authorizes application
  ↓
Google redirects back to /api/auth/callback/google
  ↓
NextAuth.js signIn callback fires
```

### Step 2: User Sync

```typescript
// frontend/auth.ts signIn callback
async signIn({ user, account }) {
  // POST to backend /api/auth/sync-user
  // Headers: X-Auth-Secret (server-to-server auth)
  // Body: { email, name, provider, provider_id }

  // Backend creates/updates user in database
  // Returns user ID

  return true;  // Allow sign-in
}
```

### Step 3: JWT Token Generation

```typescript
// frontend/auth.ts jwt callback
async jwt({ token, user }) {
  // Add user ID to JWT payload
  if (user) {
    token.userId = user.id;
  }
  return token;
}
```

### Step 4: API Request with JWT

```typescript
// frontend/lib/api.ts
export async function createDeployment(data: DeploymentCreate) {
  const session = await auth();  // Get NextAuth session

  // Generate JWT for backend
  const jwt = await createBackendAccessToken(session);

  const response = await fetch(
    `${BACKEND_URL}/api/deployments`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${jwt}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    }
  );

  return response.json();
}
```

### Step 5: Backend JWT Verification

```python
# backend/app/middleware/auth.py
from jose import jwt, JWTError

async def verify_jwt_token(token: str) -> User:
    """
    Verify JWT token and return user.

    Raises:
        HTTPException(401) if token invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET,
            algorithms=["HS256"]
        )

        user_id = payload.get("userId")
        if not user_id:
            raise HTTPException(401, "Invalid token: missing userId")

        # Fetch user from database
        async with get_session() as db:
            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(401, "User not found")

        return user

    except JWTError:
        raise HTTPException(401, "Invalid token")
```

### Step 6: Protected Endpoint

```python
# backend/app/api/deployments.py
from app.middleware.auth import get_current_user

@router.post("/deployments")
async def create_deployment(
    data: DeploymentCreate,
    user: User = Depends(get_current_user)
):
    """
    Create deployment (authenticated endpoint).

    The get_current_user dependency:
    1. Extracts Authorization header
    2. Verifies JWT signature
    3. Fetches user from database
    4. Returns user object (or raises 401)
    """

    deployment = Deployment(
        user_id=user.id,  # Associate with authenticated user
        **data.dict()
    )

    # ... rest of deployment logic
```

## The Debugging Methodology

What worked for debugging authentication:

### 1. Logging at Every Step

```python
# backend/app/middleware/auth.py
import logging
logger = logging.getLogger(__name__)

async def verify_jwt_token(token: str) -> User:
    logger.info(f"Verifying token: {token[:20]}...")  # Don't log full token

    try:
        payload = jwt.decode(...)
        logger.info(f"Token decoded successfully. User ID: {payload.get('userId')}")
        # ... rest
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise
```

**This revealed**: "JWT verification failed: Invalid signature" → secrets mismatch

### 2. Manual JWT Decoding

```bash
# Decode JWT without verification (to see payload)
echo "eyJhbGciOi..." | base64 -d | jq
```

**This revealed**: `userId` field missing → jwt callback not adding it

### 3. Testing Each Component Separately

```bash
# Test user sync directly
curl -X POST https://backend.fly.dev/api/auth/sync-user \
  -H "X-Auth-Secret: $AUTH_SYNC_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test", "provider": "google", "provider_id": "123"}'

# Test JWT verification
curl https://backend.fly.dev/api/deployments \
  -H "Authorization: Bearer $JWT"
```

### 4. Documentation

I created `AUTH_TROUBLESHOOTING.md`:

```markdown
# Authentication Troubleshooting

## 401 Errors Checklist

1. **Verify secrets match**:
   - Frontend `.env.local`: `AUTH_SECRET`
   - Backend Fly.io: `fly secrets list --app catwalk-backend`
   - Must be IDENTICAL

2. **Check user sync**:
   - Sign in
   - Check backend logs: "User synced: <email>"
   - If missing: `AUTH_SYNC_SECRET` mismatch or network error

3. **Verify JWT payload**:
   - Decode JWT: `echo $JWT | base64 -d`
   - Must contain: `{"userId": "..."}`

4. **Check backend logs**:
   - `fly logs --app catwalk-backend`
   - Look for: "JWT verification failed"
```

**This saved me** when the same issue appeared during frontend Vercel deployment.

## What I Learned

### Where AI Helped ✅
- NextAuth.js setup boilerplate
- JWT signing/verification code
- Database user model

### Where AI Failed ❌
- **Incomplete implementation**: TODOs in production code
- **Secret management confusion**: Didn't explain AUTH_SECRET vs AUTH_SYNC_SECRET
- **Error handling**: Generic errors, not actionable
- **Testing**: No auth flow tests generated

### Human Debugging Required 🧠
- **Secret synchronization**: AI can't check environment variables across systems
- **Flow understanding**: Tracking requests through frontend → backend → database
- **Error interpretation**: "Invalid signature" means secrets mismatch
- **Documentation**: Creating troubleshooting guides

**The pattern**: AI writes code. Humans debug when code interacts with external systems (OAuth, secrets, databases).

## Up Next

Authentication works! Users can sign in, create deployments, manage their MCP servers.

But the code quality is... questionable. No tests. Security reviews pending. Edge cases uncovered.

Time for **Security Hardening & Production Polish**.

That's Part 8.

---

**Key Commits**:
- `068dc28` - Implement user settings for API key management
- `2f42cff` - Implement JWT-based authentication
- `efbac5c` - Implement JWT authentication and user management with Auth.js
- `a8dfde6` - Fix 401 errors and add comprehensive authentication troubleshooting

**Related Files**:
- `frontend/auth.ts` - NextAuth.js configuration
- `backend/app/middleware/auth.py` - JWT verification
- `backend/app/api/auth.py` - User sync endpoint
- `context/AUTH_TROUBLESHOOTING.md` - Debugging guide

**Debugging Resources**:
- [NextAuth.js Callbacks](https://next-auth.js.org/configuration/callbacks)
- [JWT Decoder](https://jwt.io/)

**Next Post**: [Part 8: Security Hardening & Production Ready](08-security-hardening-production.md)
