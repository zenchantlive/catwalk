import { SignJWT } from "jose"

type BackendTokenUser = {
  id: string
  email: string
  name?: string | null
  image?: string | null
}

export async function createBackendAccessToken(user: BackendTokenUser): Promise<string> {
  const secret = process.env.AUTH_SECRET
  if (!secret) {
    throw new Error("AUTH_SECRET is not set")
  }

  const issuer = process.env.AUTH_JWT_ISSUER || "catwalk-live"
  const audience = process.env.AUTH_JWT_AUDIENCE || "catwalk-live-backend"

  const nowSeconds = Math.floor(Date.now() / 1000)
  const secretKey = new TextEncoder().encode(secret)

  return new SignJWT({
    email: user.email,
    name: user.name ?? undefined,
    picture: user.image ?? undefined,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.id)
    .setIssuer(issuer)
    .setAudience(audience)
    .setIssuedAt(nowSeconds)
    .setExpirationTime(nowSeconds + 5 * 60)
    .sign(secretKey)
}
