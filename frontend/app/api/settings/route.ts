import { NextResponse } from "next/server"

import { auth } from "@/auth"
import { createBackendAccessToken } from "@/lib/backend-access-token"

const backendUrl =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

async function forwardToBackend(request: Request): Promise<Response> {
  const session = await auth()
  
  // DEBUG: Log session state
  console.log("[API /settings] Session check:", {
    hasSession: !!session,
    hasUser: !!session?.user,
    hasEmail: !!session?.user?.email,
    userId: session?.user?.id,
    email: session?.user?.email,
  })
  
  if (!session?.user?.email) {
    console.error("[API /settings] Unauthorized - session missing or incomplete")
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  const token = await createBackendAccessToken({
    id: session.user.id,
    email: session.user.email,
    name: session.user.name,
    image: session.user.image,
  })

  // DEBUG: Log token details
  // console.log("[API /settings] Token created, length:", token.length)
  // console.log("[API /settings] Token preview:", token.substring(0, 50) + "...")
  console.log("[API /settings] Backend URL:", backendUrl)
  console.log("[API /settings] AUTH_SECRET set:", !!process.env.AUTH_SECRET)
  console.log("[API /settings] AUTH_JWT_ISSUER:", process.env.AUTH_JWT_ISSUER || "(not set)")
  console.log("[API /settings] AUTH_JWT_AUDIENCE:", process.env.AUTH_JWT_AUDIENCE || "(not set)")

  const url = new URL(request.url)
  const backendEndpoint = `${backendUrl}/api/settings${url.search}`

  const backendResponse = await fetch(backendEndpoint, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: request.method === "GET" || request.method === "DELETE" ? undefined : await request.text(),
    cache: "no-store",
  })

  console.log("[API /settings] Backend response status:", backendResponse.status)
  if (!backendResponse.ok) {
    const errorText = await backendResponse.text()
    console.error("[API /settings] Backend error:", errorText)
    // Re-create response with the error text we just read
    return new Response(errorText, {
      status: backendResponse.status,
      headers: backendResponse.headers,
    })
  }

  return backendResponse
}

async function toClientResponse(response: Response): Promise<Response> {
  const body = await response.text()
  const contentType = response.headers.get("content-type") ?? "application/json"

  return new NextResponse(body, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  })
}

export async function GET(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}

export async function POST(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}

export async function DELETE(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}
