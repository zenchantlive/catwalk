from fastapi import APIRouter, Request, HTTPException, Response
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import logging
from typing import Any, Dict
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active connections or state if needed (for now, stateless mock)

@router.get("/{deployment_id}/sse")
async def handle_sse(deployment_id: str, request: Request):
    """
    Handle MCP SSE connection.

    This endpoint establishes a Server-Sent Events (SSE) connection for the MCP protocol.
    It first sends an 'endpoint' event with the URL for JSON-RPC message submission,
    then maintains the connection with periodic keep-alive comments.
    """
    logger.info(f"New SSE connection for deployment {deployment_id}")

    async def event_generator():
        # 1. Send the 'endpoint' event pointing to the POST messages URL
        # Use PUBLIC_URL if configured (for ngrok), otherwise fall back to request.base_url
        # This ensures the client gets the correct public-facing URL
        base_url = settings.PUBLIC_URL if settings.PUBLIC_URL else str(request.base_url).rstrip("/")
        messages_url = f"{base_url}{settings.API_V1_STR}/mcp/{deployment_id}/messages"

        logger.info(f"Sending endpoint event: {messages_url}")

        # Send the endpoint event as per MCP SSE transport spec
        yield {
            "event": "endpoint",
            "data": messages_url
        }

        # Keep connection alive with periodic comments or pings
        # SSE connections need periodic data to prevent timeouts by proxies/clients
        try:
            while True:
                # Send a comment every 15 seconds to keep the connection alive
                # Comments are lines starting with ':' and are ignored by clients
                await asyncio.sleep(15)
                # Using SSE comment format for keep-alive (preferred for MCP)
                yield {
                    "comment": "keep-alive"
                }
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for {deployment_id}")
        except Exception as e:
            logger.error(f"Error in SSE connection for {deployment_id}: {e}")

    return EventSourceResponse(event_generator())

@router.post("/{deployment_id}/messages")
async def handle_messages(deployment_id: str, request: Request):
    """
    Handle MCP JSON-RPC messages.

    This endpoint receives JSON-RPC 2.0 messages from the MCP client.
    It handles initialization, tool listing, and other protocol methods.

    Per JSON-RPC 2.0 spec:
    - Requests have an 'id' field and expect a response
    - Notifications have NO 'id' field and expect NO response
    """
    body = await request.json()
    logger.info(f"Received message for {deployment_id}: {body}")

    method = body.get("method")
    msg_id = body.get("id")

    # Check if this is a notification (no 'id' field)
    is_notification = msg_id is None

    # Minimal Mock Implementation of MCP Protocol

    # Handle 'initialize' method - MCP handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "Catwalk Mock Server",
                    "version": "0.1.0"
                }
            }
        }

    # Handle 'notifications/initialized' - Client acknowledging initialization
    # This is a NOTIFICATION (no response expected per JSON-RPC 2.0 spec)
    if method == "notifications/initialized":
        logger.info(f"Client initialized for deployment {deployment_id}")
        # Return HTTP 204 No Content for notifications (no JSON-RPC response)
        return Response(status_code=204)

    # Handle 'tools/list' method - Return available tools
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "mock_tool",
                        "description": "A mock tool to verify connection",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            },
                            "required": []
                        }
                    }
                ]
            }
        }

    # Handle 'ping' method - Connection health check
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    # Handle other notifications (log and return 204)
    if is_notification:
        logger.info(f"Received notification '{method}' for deployment {deployment_id}")
        return Response(status_code=204)

    # Default fallback for unknown methods (requests only)
    logger.warning(f"Unknown method '{method}' for deployment {deployment_id}")
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    }
