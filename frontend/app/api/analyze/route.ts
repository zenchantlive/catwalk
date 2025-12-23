import { NextResponse } from "next/server"

import { auth } from "@/auth"
import { createBackendAccessToken } from "@/lib/backend-access-token"

const backendUrl =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

async function forwardToBackend(request: Request): Promise<Response> {
  const session = await auth()

  // DEBUG: Log session
  console.log("[API /analyze] Session:", {
    hasSession: !!session,
    hasUser: !!session?.user,
    email: session?.user?.email,
  })

  if (!session?.user?.email) {
    console.error("[API /analyze] Unauthorized - session missing or incomplete")
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  const token = await createBackendAccessToken({
    id: session.user.id,
    email: session.user.email,
    name: session.user.name,
    image: session.user.image,
  })

  // DEBUG: Read and log request body
  const bodyText = request.method === "GET" || request.method === "DELETE" ? undefined : await request.text()
  console.log("[API /analyze] Request body:", bodyText)
  console.log("[API /analyze] Request method:", request.method)
  console.log("[API /analyze] Backend URL:", backendUrl)

  // DEBUG: Validate JSON before sending
  if (bodyText) {
    try {
      const parsed = JSON.parse(bodyText)
      console.log("[API /analyze] Parsed body:", parsed)
    } catch (e) {
      console.error("[API /analyze] Invalid JSON in request body:", e)
      return NextResponse.json({
        detail: "Invalid JSON in request body"
      }, { status: 400 })
    }
  }

  const url = new URL(request.url)
  const backendEndpoint = `${backendUrl}/api/analyze${url.search}`

  console.log("[API /analyze] Forwarding to:", backendEndpoint)

  const backendResponse = await fetch(backendEndpoint, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: bodyText,
    cache: "no-store",
  })

  console.log("[API /analyze] Backend response status:", backendResponse.status)

  // If 422, log response body for debugging
  if (backendResponse.status === 422) {
    const errorText = await backendResponse.text()
    console.error("[API /analyze] 422 error details:", errorText)
    return new Response(errorText, {
      status: 422,
      headers: backendResponse.headers,
    })
  }

  if (!backendResponse.ok) {
    const errorText = await backendResponse.text()
    console.error("[API /analyze] Backend error:", errorText)
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

export async function POST(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}

export async function GET(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}
