# Authentication Troubleshooting Guide

**Last Updated**: 2025-12-22

This document covers common authentication issues, root causes, and resolutions learned from production debugging.

---

## Critical Authentication Requirements

### Two Required Secrets for Full Auth Flow

The authentication system requires **TWO separate secrets** to function correctly:

#### 1. AUTH_SECRET (JWT Token Signing)
- **Purpose**: Signs and verifies JWT tokens for API authentication
- **Used by**:
  - Frontend: Creates JWT tokens in `createBackendAccessToken()`
  - Backend: Verifies JWT signatures in `verify_jwt_token()`
- **Must be set in**:
  - Frontend `.env.local`: `AUTH_SECRET=<value>`
  - Backend Fly.io secrets: `fly secrets set AUTH_SECRET=<same-value>`
- **Generate**: `openssl rand -base64 32`
- **Critical**: Values MUST match exactly between frontend and backend

#### 2. AUTH_SYNC_SECRET (User Sync Endpoint Security)
- **Purpose**: Secures the `/api/auth/sync-user` endpoint (server-to-server auth)
- **Used by**:
  - Frontend: `auth.ts` signIn callback sends to backend
  - Backend: `auth.py` validates incoming sync requests
- **Must be set in**:
  - Frontend `.env.local`: `AUTH_SYNC_SECRET=<value>`
  - Backend Fly.io secrets: `fly secrets set AUTH_SYNC_SECRET=<same-value>`
- **Generate**: `openssl rand -base64 32` (different from AUTH_SECRET)
- **Critical**: If missing, users are NEVER synced to database!

---

## Common Issue: 401 Unauthorized on Settings Page

### Symptoms
```
GET /api/settings → 401 Unauthorized
Error: Unauthorized at Object.getSettings
```

- User can sign in successfully
- Dashboard and public pages work
- Only authenticated endpoints return 401

### Root Cause #1: User Not in Database

**Why it happens**:
1. User signs in with GitHub OAuth → Auth.js creates session
2. Frontend `signIn` callback tries to sync user to backend
3. **If AUTH_SYNC_SECRET is missing**: Sync is skipped silently
4. User session exists, but user doesn't exist in backend database
5. When calling `/api/settings`, backend looks up user → NOT FOUND → 401

**How to diagnose**:
```bash
# 1. Connect to database
fly postgres connect --app catwalk-backend-database

# 2. Switch to app database
\c catwalk_live_backend_dev

# 3. Check if user exists
SELECT id, email, name, github_id, created_at
FROM users
WHERE email = 'your-email@example.com';

# If you see (0 rows), the user doesn't exist!
```

**How to fix**:
```bash
# 1. Generate AUTH_SYNC_SECRET (if not set)
SYNC_SECRET=$(openssl rand -base64 32)
echo "Generated: $SYNC_SECRET"

# 2. Set on backend
fly secrets set AUTH_SYNC_SECRET="$SYNC_SECRET" --app catwalk-live-backend-dev

# 3. Add to frontend .env.local
echo 'AUTH_SYNC_SECRET="$SYNC_SECRET"' >> catwalk-live/frontend/.env.local

# 4. Restart frontend dev server
cd catwalk-live/frontend
bun run dev

# 5. Sign out and sign in again in browser
# User will be synced to database automatically
```

### Root Cause #2: AUTH_SECRET Mismatch

**Why it happens**:
- Frontend and backend have different AUTH_SECRET values
- JWT token signed with one secret, verified with another
- Signature verification fails → 401

**How to diagnose**:
```bash
# Check frontend secret
cd catwalk-live/frontend
grep AUTH_SECRET .env.local

# Check backend has the secret set
fly secrets list --app catwalk-live-backend-dev | grep AUTH_SECRET
```

**How to fix**:
```bash
# Use the SAME secret on both sides
SHARED_SECRET="vyCNeFRq3JQGsKNvXeLa1p910TPSHopUousLIkxuOVE"

# Frontend .env.local
AUTH_SECRET=$SHARED_SECRET

# Backend
fly secrets set AUTH_SECRET=$SHARED_SECRET --app catwalk-live-backend-dev
```

### Root Cause #3: Clock Skew Between Servers

**Why it happens**:
- Frontend creates token with `iat` (issued at) timestamp
- Backend's clock is behind frontend's clock
- Backend thinks token is from the future → rejects as "not yet valid"

**Error in logs**:
```
jwt.exceptions.ImmatureSignatureError: The token is not yet valid (iat)
```

**How to fix**:
- Already fixed in `backend/app/core/auth.py` with `leeway=60`
- Allows 60 seconds clock skew tolerance
- If you see this error, redeploy backend with latest code

### Root Cause #4: Issuer/Audience Verification Issues

**Why it happens**:
- Frontend creates tokens with `iss` and `aud` claims
- Backend tries to verify but settings are inconsistent

**Error in logs**:
```
jwt.exceptions.InvalidAudienceError: Invalid audience
```

**How to fix**:
- Already fixed in `backend/app/core/auth.py`
- Explicitly disables verification when `AUTH_JWT_ISSUER`/`AUTH_JWT_AUDIENCE` not set
- If you see this error, redeploy backend with latest code

---

## Complete Auth Setup Checklist

### Initial Setup (New Project)

1. **Generate secrets**:
   ```bash
   AUTH_SECRET=$(openssl rand -base64 32)
   AUTH_SYNC_SECRET=$(openssl rand -base64 32)
   echo "AUTH_SECRET: $AUTH_SECRET"
   echo "AUTH_SYNC_SECRET: $AUTH_SYNC_SECRET"
   ```

2. **Configure frontend** (`catwalk-live/frontend/.env.local`):
   ```bash
   AUTH_SECRET="<value-from-step-1>"
   AUTH_SYNC_SECRET="<value-from-step-1>"
   AUTH_GITHUB_ID="<from-github-oauth-app>"
   AUTH_GITHUB_SECRET="<from-github-oauth-app>"
   NEXTAUTH_URL="http://localhost:3000"
   NEXT_PUBLIC_BACKEND_URL="https://catwalk-live-backend-dev.fly.dev"
   ```

3. **Configure backend** (Fly.io secrets):
   ```bash
   fly secrets set AUTH_SECRET="<same-as-frontend>" --app catwalk-live-backend-dev
   fly secrets set AUTH_SYNC_SECRET="<same-as-frontend>" --app catwalk-live-backend-dev
   ```

4. **Deploy backend**:
   ```bash
   cd catwalk-live/backend
   fly deploy --app catwalk-live-backend-dev
   ```

5. **Test the flow**:
   ```bash
   # Start frontend
   cd catwalk-live/frontend
   bun run dev

   # Open browser to http://localhost:3000
   # Sign in with GitHub
   # Check database - user should exist now!
   ```

### Verification After Setup

```bash
# 1. Check secrets are set on backend
fly secrets list --app catwalk-live-backend-dev

# Should see:
# AUTH_SECRET          (digest)
# AUTH_SYNC_SECRET     (digest)

# 2. Check user was synced
fly postgres connect --app catwalk-backend-database
\c catwalk_live_backend_dev
SELECT email FROM users ORDER BY created_at DESC LIMIT 1;

# 3. Test authenticated endpoint
# Sign in, then check settings page - should load without errors
```

---

## Debugging JWT Issues

### Enable Debug Logging

Backend already has comprehensive JWT debug logging in `app/core/auth.py`:

```python
logger.info(
    "JWT verification config: issuer=%s, audience=%s, required_claims=%s, verify_options=%s",
    settings.AUTH_JWT_ISSUER,
    settings.AUTH_JWT_AUDIENCE,
    required_claims,
    verify_options
)
```

**View logs**:
```bash
fly logs --app catwalk-live-backend-dev
```

**Look for**:
- `JWT verification config:` - Shows what settings are active
- `JWT verification successful for user:` - Token verified successfully
- `JWT validation failed:` - Shows exact error (clock skew, audience, signature, etc.)

### Manual Token Inspection

Decode a JWT without verification to see its contents:

```python
# In Python
import jwt
import json

token = "eyJhbGc..."  # Your JWT token
decoded = jwt.decode(token, options={"verify_signature": False})
print(json.dumps(decoded, indent=2))
```

Look for:
- `sub` - User ID (should match database)
- `email` - User email (should match database)
- `iss` - Issuer (if present)
- `aud` - Audience (if present)
- `iat` - Issued at timestamp
- `exp` - Expiration timestamp

---

## Auth Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ User Signs In with GitHub OAuth                             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Auth.js creates session (JWT in cookie)                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ signIn callback in auth.ts                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ if (!AUTH_SYNC_SECRET) {                                │ │
│ │   console.warn("Skipping user sync")  ⚠️ PROBLEM!      │ │
│ │   return true                                           │ │
│ │ }                                                       │ │
│ │                                                         │ │
│ │ POST /api/auth/sync-user                               │ │
│ │ Headers: X-Auth-Secret: AUTH_SYNC_SECRET               │ │
│ │ Body: { email, name, avatar_url, github_id }           │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend /api/auth/sync-user                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Validates X-Auth-Secret matches AUTH_SYNC_SECRET        │ │
│ │ Creates or updates user in database                     │ │
│ │ Returns user data                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ User exists in database ✅                                  │
│ All authenticated endpoints now work!                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Files

**Frontend**:
- `auth.ts` - Auth.js configuration with signIn callback
- `lib/backend-access-token.ts` - Creates JWT tokens for backend API calls
- `app/api/settings/route.ts` - Example authenticated API route

**Backend**:
- `app/core/auth.py` - JWT verification with clock skew tolerance
- `app/api/auth.py` - User sync endpoint (`/auth/sync-user`)
- `app/models/user.py` - User database model

---

## Prevention Checklist

Before deploying a new environment:

- [ ] Generate AUTH_SECRET and set on frontend + backend
- [ ] Generate AUTH_SYNC_SECRET and set on frontend + backend
- [ ] Verify secrets match: `fly secrets list --app <backend-app>`
- [ ] Deploy backend with latest auth fixes
- [ ] Test sign-in flow end-to-end
- [ ] Verify user appears in database after sign-in
- [ ] Test authenticated endpoint (e.g., `/api/settings`)

---

## Quick Fix Summary

**Problem**: 401 Unauthorized after sign-in
**Diagnosis**: Check if user exists in database
**Fix**: Set AUTH_SYNC_SECRET, restart frontend, sign out/in
**Verification**: Check database for user row

**Time to fix**: ~5 minutes once diagnosed correctly
