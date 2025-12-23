import { NextResponse } from "next/server"

import { auth } from "@/auth"
import { createBackendAccessToken } from "@/lib/backend-access-token"

const backendUrl =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

async function forwardToBackend(request: Request): Promise<Response> {
  const session = await auth()

  // Session verification log
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

  // Read request body for forwarding
  const bodyText = request.method === "GET" || request.method === "DELETE" ? undefined : await request.text()

  // Basic validation without logging body
  if (bodyText) {
    try {
      JSON.parse(bodyText)
    } catch {
      console.error("[API /analyze] Invalid JSON in request body")
      return NextResponse.json({
        detail: "Invalid JSON in request body"
      }, { status: 400 })
    }
  }

  const url = new URL(request.url)
  const backendEndpoint = `${backendUrl}/api/analyze${url.search}`

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
