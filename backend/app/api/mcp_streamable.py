"""
MCP Streamable HTTP Transport Implementation

This module implements the MCP Streamable HTTP transport specification (version 2025-06-18).
This is the current recommended transport for remote MCP servers, replacing the deprecated HTTP+SSE transport.

Specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

Key features:
- Single unified endpoint supporting both POST and GET methods
- Protocol version header validation
- Session management (optional but recommended)
- Support for both JSON responses and SSE streaming
"""

from fastapi import APIRouter, Request, Response, Header, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any
from app.core.config import settings
from app.db.session import get_db
from app.models.deployment import Deployment
from app.services.mcp_process_manager import get_server

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active sessions (in production, use Redis or database)
active_sessions: Dict[str, Dict[str, Any]] = {}

# MCP Protocol Version - spec version we support
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
DEFAULT_PROTOCOL_VERSION = "2025-06-18"


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


async def _get_deployment(db: AsyncSession, deployment_id: str) -> Optional[Deployment]:
    try:
        from uuid import UUID

        deployment_uuid = UUID(deployment_id)
    except ValueError:
        return None

    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    return result.scalar_one_or_none()


async def _forward_to_fly_machine_streamable_http(
    *,
    deployment: Deployment,
    message: Dict[str, Any],
    protocol_version: str,
    session_id: Optional[str],
) -> Response:
    import httpx

    # Prefer Fly internal DNS over raw IPs.
    # This avoids relying on the Machines API response shape ("private_ip" varies) and is
    # the most reliable way to reach a specific machine on the 6PN network.
    machine_host_internal = f"{deployment.machine_id}.vm.{settings.FLY_MCP_APP_NAME}.internal"
    machine_url_internal = f"http://{machine_host_internal}:8080/mcp"

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        # mcp-proxy Streamable HTTP requires the client to accept JSON responses
        # (and may also stream server events as SSE).
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": protocol_version,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    async def _do_forward(url: str) -> Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=message, headers=headers) as upstream:
                upstream_headers: Dict[str, str] = {}
                for header_name in ("MCP-Protocol-Version", "Mcp-Session-Id"):
                    header_value = upstream.headers.get(header_name)
                    if header_value is not None:
                        upstream_headers[header_name] = header_value

                content_type = upstream.headers.get("content-type", "")
                if content_type.lower().startswith("text/event-stream"):
                    return StreamingResponse(
                        upstream.aiter_raw(),
                        status_code=upstream.status_code,
                        headers=upstream_headers,
                        media_type="text/event-stream",
                    )

                content = await upstream.aread()
                return Response(
                    content=content,
                    status_code=upstream.status_code,
                    headers=upstream_headers,
                    media_type=content_type.split(";", 1)[0] if content_type else None,
                )

    try:
        logger.info(
            "Forwarding MCP request to Fly machine (internal DNS): machine_id=%s url=%s",
            deployment.machine_id,
            machine_url_internal,
        )
        return await _do_forward(machine_url_internal)
    except httpx.ConnectError as e:
        # Fallback: if internal DNS fails but Machines API is configured, try raw private IPv6.
        logger.warning(
            "ConnectError via internal DNS (%s). Falling back to Machines API lookup. err=%s",
            machine_url_internal,
            str(e),
        )

        if not settings.FLY_API_TOKEN:
            return JSONResponse(
                status_code=502,
                content=_jsonrpc_error(
                    message.get("id"),
                    -32603,
                    f"Error connecting to MCP server (internal DNS failed and no FLY_API_TOKEN for lookup): {str(e)}",
                ),
                headers={"MCP-Protocol-Version": protocol_version},
            )

        try:
            from app.services.fly_deployment_service import FlyDeploymentService

            fly_service = FlyDeploymentService()
            machine_info = await fly_service.get_machine(deployment.machine_id)
        except Exception as lookup_error:
            logger.error("Machines API lookup failed for %s: %s", deployment.machine_id, lookup_error, exc_info=True)
            return JSONResponse(
                status_code=502,
                content=_jsonrpc_error(
                    message.get("id"),
                    -32603,
                    f"Error connecting to MCP server (Machines API lookup failed): {str(lookup_error)}",
                ),
                headers={"MCP-Protocol-Version": protocol_version},
            )

        private_ip = None
        if isinstance(machine_info, dict):
            private_ip = machine_info.get("private_ip")
            if not private_ip:
                private_ips = machine_info.get("private_ips")
                if isinstance(private_ips, list) and private_ips:
                    private_ip = private_ips[0]

        if not private_ip:
            return JSONResponse(
                status_code=502,
                content=_jsonrpc_error(
                    message.get("id"),
                    -32603,
                    "MCP server machine has no private IP address in Machines API response.",
                ),
                headers={"MCP-Protocol-Version": protocol_version},
            )

        machine_url_ipv6 = f"http://[{private_ip}]:8080/mcp"
        try:
            logger.info(
                "Forwarding MCP request to Fly machine (private IPv6): machine_id=%s url=%s",
                deployment.machine_id,
                machine_url_ipv6,
            )
            return await _do_forward(machine_url_ipv6)
        except Exception as final_error:
            logger.error("Error forwarding to Fly machine: %s", final_error, exc_info=True)
            return JSONResponse(
                status_code=502,
                content=_jsonrpc_error(
                    message.get("id"),
                    -32603,
                    f"Error connecting to MCP server: {str(final_error)}",
                ),
                headers={"MCP-Protocol-Version": protocol_version},
            )
    except Exception as e:
        logger.error("Error forwarding to Fly machine: %s", e, exc_info=True)
        return JSONResponse(
            status_code=502,
            content=_jsonrpc_error(message.get("id"), -32603, f"Error connecting to MCP server: {str(e)}"),
            headers={"MCP-Protocol-Version": protocol_version},
        )


@router.get("/{deployment_id}")
@router.post("/{deployment_id}")
async def handle_mcp_endpoint(
    deployment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    mcp_protocol_version: Optional[str] = Header(None, alias="MCP-Protocol-Version"),
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
    token: Optional[str] = None, # Access token from query param (preferred for SSE)
    authorization: Optional[str] = Header(None) # Access token from Bearer header
):
    """
    Unified MCP endpoint supporting both GET and POST methods.

    GET:  Opens an SSE stream for server-initiated messages
    POST: Sends JSON-RPC requests, notifications, or responses

    This endpoint implements the Streamable HTTP transport (MCP spec 2025-06-18).
    Authentication: Requires valid 'access_token' query param or Bearer token.
    """

    # 1. Authenticate Request
    # Check query param 'token' first, then Authorization Header
    access_token = token
    if not access_token and authorization:
        if authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
        else:
            access_token = authorization

    deployment = await _get_deployment(db, deployment_id)
    if not deployment:
         return JSONResponse(
            status_code=404,
            content=_jsonrpc_error(None, -32001, f"Deployment not found: {deployment_id}"),
            headers={"MCP-Protocol-Version": mcp_protocol_version or DEFAULT_PROTOCOL_VERSION},
        )
    
    # Verify token matches deployment's access_token
    # Use constant-time comparison to prevent timing attacks
    import secrets
    if not access_token or not deployment.access_token or not secrets.compare_digest(access_token, deployment.access_token):
        logger.warning(f"Unauthorized access attempt for deployment {deployment_id}")
        return JSONResponse(
            status_code=401,
            content=_jsonrpc_error(None, -32001, "Unauthorized: Invalid access token"),
             headers={"MCP-Protocol-Version": mcp_protocol_version or DEFAULT_PROTOCOL_VERSION},
        )

    # Validate protocol version
    protocol_version = mcp_protocol_version or DEFAULT_PROTOCOL_VERSION
    if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
        logger.warning(f"Unsupported protocol version: {protocol_version}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": f"Unsupported protocol version: {protocol_version}",
                    "data": {"supported_versions": SUPPORTED_PROTOCOL_VERSIONS}
                }
            }
        )

    logger.info(f"MCP {request.method} request for deployment {deployment_id}, protocol {protocol_version}")

    # Handle GET request - Open SSE stream for server-initiated messages
    if request.method == "GET":
        return await handle_get_sse_stream(deployment_id, mcp_session_id, protocol_version)

    # Handle POST request - Process JSON-RPC message
    elif request.method == "POST":
        return await handle_post_message(deployment_id, request, db, mcp_session_id, protocol_version)


async def handle_get_sse_stream(
    deployment_id: str,
    session_id: Optional[str],
    protocol_version: str
) -> EventSourceResponse:
    """
    Handle GET request to open SSE stream for server-initiated messages.

    This keeps a persistent connection open so the server can send messages
    to the client at any time (e.g., notifications, progress updates).
    """
    logger.info(f"Opening SSE stream for deployment {deployment_id}, session {session_id}")

    async def event_generator():
        """
        Generator that yields SSE events.

        In a real implementation, this would listen for server-initiated messages
        from the deployed MCP server subprocess and forward them to the client.
        """
        try:
            # Send initial keep-alive to signal connection established
            yield {
                "comment": "connection-established"
            }
            # Keep the connection alive with periodic comments
            # In production, this would also send real server-initiated messages
            while True:
                await asyncio.sleep(30)
                # Send keep-alive comment (SSE comments start with ':')
                yield {
                    "comment": "keep-alive"
                }
        except asyncio.CancelledError:
            logger.info(f"SSE stream closed for deployment {deployment_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for {deployment_id}: {e}")

    return EventSourceResponse(
        event_generator(),
        headers={
            "MCP-Protocol-Version": protocol_version,
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        }
    )


async def handle_post_message(
    deployment_id: str,
    request: Request,
    db: AsyncSession,
    session_id: Optional[str],
    protocol_version: str
) -> Response:
    """
    Handle POST request to process JSON-RPC messages.

    The client sends JSON-RPC requests, notifications, or responses.
    The server responds with either:
    - 202 Accepted (for notifications/responses)
    - 200 OK with JSON response (for requests)
    - 200 OK with SSE stream (for long-running requests)
    """

    # Parse the JSON-RPC message from the request body
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            }
        )

    logger.info(f"Received message for {deployment_id}: {body}")

    method = body.get("method")
    msg_id = body.get("id")

    deployment = await _get_deployment(db, deployment_id)
    if not deployment:
        return JSONResponse(
            status_code=404,
            content=_jsonrpc_error(msg_id, -32001, f"Deployment not found: {deployment_id}"),
            headers={"MCP-Protocol-Version": protocol_version},
        )

    if deployment.machine_id:
        return await _forward_to_fly_machine_streamable_http(
            deployment=deployment,
            message=body,
            protocol_version=protocol_version,
            session_id=session_id,
        )

    # Check if this is a notification (no 'id' field) or response
    is_notification = msg_id is None and method is not None
    is_response = "result" in body or "error" in body

    # Handle notifications - return 202 Accepted with no body
    if is_notification:
        logger.info(f"Received notification '{method}' for deployment {deployment_id}")
        # Process notification asynchronously (in production, forward to MCP server subprocess)
        return Response(
            status_code=202,
            headers={"MCP-Protocol-Version": protocol_version}
        )

    # Handle responses from client - return 202 Accepted with no body
    if is_response:
        logger.info(f"Received response for deployment {deployment_id}: {msg_id}")
        # Process response (in production, forward to MCP server subprocess)
        return Response(
            status_code=202,
            headers={"MCP-Protocol-Version": protocol_version}
        )

    # Handle requests - process and return JSON-RPC response
    response_data = await process_jsonrpc_request(deployment, deployment_id, body, session_id, protocol_version)

    # Return JSON response with MCP protocol version header
    return JSONResponse(
        status_code=200,
        content=response_data,
        headers={"MCP-Protocol-Version": protocol_version}
    )


async def process_jsonrpc_request(
    deployment: Deployment,
    deployment_id: str,
    message: Dict[str, Any],
    session_id: Optional[str],
    protocol_version: str
) -> Dict[str, Any]:
    """
    Process a JSON-RPC request and return the response.

    Fetches the deployment configuration from the database and returns
    the configured MCP server capabilities (tools, resources, prompts).
    """

    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})

    # Extract MCP server configuration from schedule_config
    # Expected structure: deployment.schedule_config = {"mcp_config": {...}}
    mcp_config = deployment.schedule_config.get("mcp_config", {}) if deployment.schedule_config else {}

    # Handle 'initialize' method - MCP handshake
    if method == "initialize":
        # Generate or retrieve session ID
        if not session_id:
            session_id = str(uuid.uuid4())
            active_sessions[session_id] = {
                "deployment_id": deployment_id,
                "protocol_version": protocol_version,
                "initialized": True
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "Catwalk Live Mock Server",
                    "version": "0.2.0"
                },
                "_meta": {
                    "sessionId": session_id
                }
            }
        }

    # Handle 'tools/list' method - Return available tools
    if method == "tools/list":
        # Get tools from the MCP server configuration
        # If no tools configured, return empty list (not mock tools)
        configured_tools = mcp_config.get("tools", [])

        logger.info(f"Returning {len(configured_tools)} configured tools for deployment {deployment_id}")

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": configured_tools
            }
        }

    # Handle 'tools/call' method - Execute a tool
    if method == "tools/call":
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})

        logger.info(f"Tool call request for deployment {deployment_id}: {tool_name} with args: {tool_arguments}")

        # Fallback: Try local subprocess (for local development)
        logger.info("No machine_id, trying local subprocess")
        server = await get_server(deployment_id)

        if not server:
            logger.error(f"No running MCP server found for deployment {deployment_id}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"MCP server not running for this deployment. Try recreating the deployment."
                }
            }

        # Forward the tool call to the real MCP server subprocess
        try:
            response = await server.call_tool(method, params, msg_id)
            return response
        except Exception as e:
            logger.error(f"Error calling tool on MCP server {deployment_id}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"Error executing tool: {str(e)}"
                }
            }

    # Handle 'ping' method - Connection health check
    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        }

    # Handle 'resources/list' method
    if method == "resources/list":
        # Get resources from the MCP server configuration
        configured_resources = mcp_config.get("resources", [])

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "resources": configured_resources
            }
        }

    # Handle 'prompts/list' method
    if method == "prompts/list":
        # Get prompts from the MCP server configuration
        configured_prompts = mcp_config.get("prompts", [])

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "prompts": configured_prompts
            }
        }

    # Unknown method - return error
    logger.warning(f"Unknown method '{method}' for deployment {deployment_id}")
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }
