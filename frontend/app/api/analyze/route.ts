import { NextResponse } from "next/server"
import { auth } from "@/auth"

const backendUrl =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

async function forwardToBackend(request: Request): Promise<Response> {
  const session = await auth()

  // Session verification log
  if (!session?.user?.email) {
    console.error("[API /analyze] Unauthorized - session missing or incomplete")
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

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

  // Forward relevant headers
  const contentType = request.headers.get("Content-Type") || "application/json"
  const accept = request.headers.get("Accept") || "application/json"

  const backendResponse = await fetch(backendEndpoint, {
    method: request.method,
    headers: {
      "Authorization": `Bearer ${session.user.id}`,
      "X-User-Email": session.user.email,
      "Content-Type": contentType,
      "Accept": accept,
    },
    body: bodyText,
    cache: "no-store",
  })

  // If 422, return error without logging body details which might contain sensitive data
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

export async function DELETE(request: Request): Promise<Response> {
  const response = await forwardToBackend(request)
  return toClientResponse(response)
}
