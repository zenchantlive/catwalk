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
 * - AUTH_GITHUB_ID: GitHub OAuth App Client ID
 * - AUTH_GITHUB_SECRET: GitHub OAuth App Client Secret
 */
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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (token as any).githubId = profile.id as string
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (token as any).avatarUrl = (profile as any).avatar_url
      }
      return token
    },
    async session({ session, token }) {
      // Add custom fields to session
      if (session.user) {
        session.user.id = token.sub!
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        session.user.githubId = (token as any).githubId as string
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        session.user.avatarUrl = (token as any).avatarUrl as string
      }
      return session
    },
    async signIn({ user, account: _account, profile }) {
      // Sync user to backend after successful sign-in
      try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL?.replace("/:path*", "") || "http://localhost:8000"

        await fetch(`${backendUrl}/auth/sync-user`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Auth-Secret": process.env.AUTH_SECRET || "", // Use AUTH_SECRET as the shared secret
          },
          body: JSON.stringify({
            email: user.email!,
            name: user.name || null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            avatar_url: (profile as any)?.avatar_url || user.image || null,
            github_id: profile?.id || null,
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

// declare module "next-auth/jwt" {
//   interface JWT {
//     githubId?: string
//     avatarUrl?: string
//   }
// }
