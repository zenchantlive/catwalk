import { auth } from "@/auth"
import { NextResponse } from "next/server"

/**
 * Middleware to protect routes requiring authentication
 *
 * Protected routes:
 * - /dashboard - Deployment list (requires sign-in)
 * - /configure - Create deployment (requires sign-in)
 * - /settings - User settings (requires sign-in)
 *
 * Public routes:
 * - / - Landing page
 * - /signin - Sign in page
 * - /api/auth/* - Auth.js API routes
 */
export default auth((req) => {
  const isAuthenticated = !!req.auth
  const pathname = req.nextUrl.pathname

  // Define protected routes
  const protectedRoutes = ["/dashboard", "/configure", "/settings"]
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  )

  // Redirect to sign-in if accessing protected route without auth
  if (isProtectedRoute && !isAuthenticated) {
    const signInUrl = new URL("/signin", req.url)
    signInUrl.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(signInUrl)
  }

  // Redirect to dashboard if already signed in and visiting sign-in page
  if (pathname === "/signin" && isAuthenticated) {
    return NextResponse.redirect(new URL("/dashboard", req.url))
  }

  return NextResponse.next()
})

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes - handle auth separately)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
}
