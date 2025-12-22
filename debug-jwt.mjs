#!/usr/bin/env node
/**
 * JWT Debugging Script
 *
 * This script helps diagnose JWT token creation and verification issues.
 * Run with: node debug-jwt.mjs
 */

import { SignJWT, jwtDecrypt, decodeJwt } from "jose"

const AUTH_SECRET = process.env.AUTH_SECRET
const AUTH_JWT_ISSUER = process.env.AUTH_JWT_ISSUER || "catwalk-live"
const AUTH_JWT_AUDIENCE = process.env.AUTH_JWT_AUDIENCE || "catwalk-live-backend"

console.log("=== JWT Configuration Debug ===\n")

console.log("Frontend Environment:")
console.log("  AUTH_SECRET:", AUTH_SECRET ? `${AUTH_SECRET.substring(0, 10)}...` : "(NOT SET)")
console.log("  AUTH_SECRET length:", AUTH_SECRET?.length || 0)
console.log("  AUTH_JWT_ISSUER:", AUTH_JWT_ISSUER)
console.log("  AUTH_JWT_AUDIENCE:", AUTH_JWT_AUDIENCE)
console.log()

if (!AUTH_SECRET) {
  console.error("ERROR: AUTH_SECRET is not set!")
  console.error("Set it in your .env.local file")
  process.exit(1)
}

// Create a test token (same logic as createBackendAccessToken)
const testUser = {
  id: "test-user-123",
  email: "[email protected]",
  name: "Test User",
  image: null,
}

console.log("Creating test JWT token...")
const nowSeconds = Math.floor(Date.now() / 1000)
const secretKey = new TextEncoder().encode(AUTH_SECRET)

try {
  const token = await new SignJWT({
    email: testUser.email,
    name: testUser.name,
    picture: testUser.image ?? undefined,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(testUser.id)
    .setIssuer(AUTH_JWT_ISSUER)
    .setAudience(AUTH_JWT_AUDIENCE)
    .setIssuedAt(nowSeconds)
    .setExpirationTime(nowSeconds + 5 * 60)
    .sign(secretKey)

  console.log("✓ Token created successfully")
  console.log("  Token length:", token.length)
  console.log("  Token preview:", token.substring(0, 80) + "...")
  console.log()

  // Decode without verification to inspect claims
  const decoded = decodeJwt(token)
  console.log("Decoded JWT Claims:")
  console.log(JSON.stringify(decoded, null, 2))
  console.log()

  console.log("Backend Verification Requirements:")
  console.log("  The backend needs these environment variables:")
  console.log(`  - AUTH_SECRET="${AUTH_SECRET}"`)
  console.log(`  - AUTH_JWT_ISSUER="${AUTH_JWT_ISSUER}"`)
  console.log(`  - AUTH_JWT_AUDIENCE="${AUTH_JWT_AUDIENCE}"`)
  console.log()

  console.log("Fly.io Secrets Check:")
  console.log("  Run this command to verify backend secrets:")
  console.log("  fly secrets list --app catwalk-live-backend-dev")
  console.log()
  console.log("  Expected output should include:")
  console.log("  - AUTH_SECRET")
  console.log("  - AUTH_JWT_ISSUER")
  console.log("  - AUTH_JWT_AUDIENCE")
  console.log()

  console.log("If secrets don't match, set them with:")
  console.log(`  fly secrets set AUTH_SECRET="${AUTH_SECRET}" --app catwalk-live-backend-dev`)
  console.log(`  fly secrets set AUTH_JWT_ISSUER="${AUTH_JWT_ISSUER}" --app catwalk-live-backend-dev`)
  console.log(`  fly secrets set AUTH_JWT_AUDIENCE="${AUTH_JWT_AUDIENCE}" --app catwalk-live-backend-dev`)
  console.log()

} catch (error) {
  console.error("✗ Error creating token:")
  console.error(error)
  process.exit(1)
}

console.log("=== Debug Complete ===")
