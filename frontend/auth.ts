import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"

/**
 * Auth.js configuration for Catwalk Live
 *
 * Uses GitHub OAuth for authentication (no database adapter - JWT only).
 * User info is synced to backend after sign-in.
 *
 * Environment variables required:
 * - AUTH_SECRET: Random secret for JWT signing (generate with: openssl rand -base64 32)
 * - AUTH_SYNC_SECRET: Shared secret for backend `/api/auth/sync-user` (server-only; do not expose to browser)
 * - AUTH_GITHUB_ID: GitHub OAuth App Client ID
 * - AUTH_GITHUB_SECRET: GitHub OAuth App Client Secret
 */
type GitHubProfileFields = {
  id?: string | number
  avatar_url?: string
}

function getGitHubProfileFields(profile: unknown): GitHubProfileFields {
  if (!profile || typeof profile !== "object") return {}
  const maybeProfile = profile as Partial<Record<keyof GitHubProfileFields, unknown>>
  const id = maybeProfile.id
  const avatarUrl = maybeProfile.avatar_url

  return {
    id: typeof id === "string" || typeof id === "number" ? id : undefined,
    avatar_url: typeof avatarUrl === "string" ? avatarUrl : undefined,
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
      // Request user email and profile info
      authorization: {
        params: {
          scope: "read:user user:email",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // On first sign-in, add GitHub info to token
      if (account && profile) {
        const { id, avatar_url } = getGitHubProfileFields(profile)
        const tokenRecord = token as unknown as Record<string, unknown>
        tokenRecord.githubId = id != null ? String(id) : undefined
        tokenRecord.avatarUrl = avatar_url
      }
      return token
    },
    async session({ session, token }) {
      // Add custom fields to session
      if (session.user) {
        const tokenRecord = token as unknown as Record<string, unknown>
        const githubId = typeof tokenRecord.githubId === "string" ? tokenRecord.githubId : ""
        const avatarUrl = typeof tokenRecord.avatarUrl === "string" ? tokenRecord.avatarUrl : ""

        session.user.id = token.sub!
        session.user.githubId = githubId
        session.user.avatarUrl = avatarUrl
      }
      return session
    },
    async signIn({ user, account: _account, profile }) {
      // Sync user to backend after successful sign-in
      try {
        const syncSecret = process.env.AUTH_SYNC_SECRET
        if (!syncSecret) {
          if (process.env.NODE_ENV === "production") {
            throw new Error("AUTH_SYNC_SECRET is required in production")
          }
          console.warn("AUTH_SYNC_SECRET is not set; skipping backend user sync")
          return true
        }

        // Use dedicated backend URL for direct backend calls
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"
        const { id, avatar_url } = getGitHubProfileFields(profile)

        await fetch(`${backendUrl}/api/auth/sync-user`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Auth-Secret": syncSecret,
          },
          body: JSON.stringify({
            email: user.email!,
            name: user.name || null,
            avatar_url: avatar_url || user.image || null,
            github_id: id != null ? String(id) : null,
          }),
        })
      } catch (error) {
        console.error("Failed to sync user to backend:", error)
        // Allow sign-in to continue even if backend sync fails
      }

      return true
    },
  },
  pages: {
    signIn: "/signin",
    error: "/auth/error",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  secret: process.env.AUTH_SECRET,
})

// Extend NextAuth types
declare module "next-auth" {
  interface Session {
    user: {
      id: string
      email: string
      name?: string | null
      image?: string | null
      githubId: string
      avatarUrl: string
    }
  }
}
