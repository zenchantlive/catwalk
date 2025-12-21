import { handlers } from "@/auth"

/**
 * Auth.js API Route Handler
 *
 * This handles all Auth.js routes:
 * - GET/POST /api/auth/signin - Sign in page
 * - GET/POST /api/auth/signout - Sign out
 * - GET/POST /api/auth/callback/github - OAuth callback
 * - GET /api/auth/session - Get current session
 * - GET /api/auth/providers - Get configured providers
 * - GET /api/auth/csrf - Get CSRF token
 */
export const { GET, POST } = handlers
