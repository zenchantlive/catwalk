"""
MCP Server Process Manager

Manages long-running MCP server subprocesses for each deployment.
Each deployment gets its own subprocess that communicates via stdio (JSON-RPC).

This is for local testing. In production (Fly.io), each deployment will be a separate container.
"""

import asyncio
import json
import logging
import uuid
import sys
import subprocess
import threading
from typing import Dict, Any, Optional
from asyncio.subprocess import Process

logger = logging.getLogger(__name__)

# Detect Windows platform
IS_WINDOWS = sys.platform == "win32"

# Global registry of running MCP server processes
# Key: deployment_id (UUID), Value: ServerProcess instance
_running_servers: Dict[str, "ServerProcess"] = {}


class ServerProcess:
    """
    Represents a running MCP server subprocess.

    Handles JSON-RPC communication over stdin/stdout with the MCP server.
    """

    def __init__(self, deployment_id: str, package: str, env_vars: Dict[str, str]):
        """
        Initialize a server process configuration.

        Args:
            deployment_id: Unique identifier for the deployment
            package: NPM package name (e.g., '@alexarevalo.ai/mcp-server-ticktick')
            env_vars: Environment variables to pass to the server
        """
        self.deployment_id = deployment_id
        self.package = package
        self.env_vars = env_vars
        self.process: Optional[Process] = None
        self.lock = asyncio.Lock()  # Prevent concurrent stdin/stdout access

    async def start(self) -> bool:
        """
        Start the MCP server subprocess.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Build the command to run the MCP server
            # For npm packages: npx -y <package>
            # For Python packages: python -m <module> or uv run <package>
            if self.package.startswith("@") or "/" in self.package:
                # NPM package (e.g., @alexarevalo.ai/mcp-server-ticktick)
                cmd = ["npx", "-y", self.package]
            else:
                # Python package (simple heuristic)
                cmd = ["python", "-m", self.package]

            logger.info(f"Starting MCP server for deployment {self.deployment_id}")
            logger.info(f"  Package: {self.package}")
            logger.info(f"  Command: {' '.join(cmd)}")
            logger.info(f"  Env vars: {list(self.env_vars.keys())}")
            logger.info(f"  Platform: {'Windows' if IS_WINDOWS else 'Unix'}")

            if IS_WINDOWS:
                # Windows: Use synchronous subprocess.Popen (asyncio subprocesses don't work on Windows)
                logger.warning("Running on Windows - using synchronous subprocess (asyncio subprocess not supported)")
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**self.env_vars},
                    text=False  # Binary mode for JSON-RPC
                )
                logger.info(f"MCP server started for deployment {self.deployment_id} (PID: {self.process.pid})")
                return True
            else:
                # Unix/Linux: Use asyncio subprocess (preferred)
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**self.env_vars}  # Pass credentials as environment variables
                )

                logger.info(f"MCP server started for deployment {self.deployment_id} (PID: {self.process.pid})")

                # Start background task to log stderr
                asyncio.create_task(self._log_stderr())

                return True

        except Exception as e:
            import traceback
            logger.error(f"Failed to start MCP server for {self.deployment_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def _log_stderr(self):
        """Background task to log stderr output from the MCP server."""
        if not self.process or not self.process.stderr:
            return

        try:
            async for line in self.process.stderr:
                logger.warning(f"MCP server {self.deployment_id} stderr: {line.decode().strip()}")
        except Exception as e:
            logger.error(f"Error reading stderr for {self.deployment_id}: {e}")

    async def call_tool(self, method: str, params: Dict[str, Any], msg_id: Any) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the MCP server and get the response.

        Args:
            method: JSON-RPC method name (e.g., 'tools/call')
            params: Method parameters
            msg_id: JSON-RPC message ID

        Returns:
            JSON-RPC response from the server
        """
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError(f"MCP server not running for deployment {self.deployment_id}")

        async with self.lock:
            try:
                # Build JSON-RPC request
                request = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": method,
                    "params": params
                }

                request_line = json.dumps(request) + "\n"
                logger.debug(f"Sent to MCP server {self.deployment_id}: {request}")

                if IS_WINDOWS:
                    # Windows: Use threading for synchronous I/O
                    return await self._call_tool_windows(request_line, msg_id)
                else:
                    # Unix: Use async I/O
                    return await self._call_tool_unix(request_line, msg_id)

            except Exception as e:
                logger.error(f"Error communicating with MCP server {self.deployment_id}: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }

    async def _call_tool_unix(self, request_line: str, msg_id: Any) -> Dict[str, Any]:
        """Handle tool call on Unix using asyncio subprocess."""
        # Send request to server via stdin
        self.process.stdin.write(request_line.encode())
        await self.process.stdin.drain()

        # Read response from stdout
        response_line = await asyncio.wait_for(
            self.process.stdout.readline(),
            timeout=30.0
        )

        if not response_line:
            raise RuntimeError("MCP server closed stdout")

        response = json.loads(response_line.decode())
        logger.debug(f"Received from MCP server {self.deployment_id}: {response}")
        return response

    async def _call_tool_windows(self, request_line: str, msg_id: Any) -> Dict[str, Any]:
        """Handle tool call on Windows using synchronous I/O in a thread."""
        def _sync_io():
            # Write request
            self.process.stdin.write(request_line.encode())
            self.process.stdin.flush()

            # Read response (blocking)
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("MCP server closed stdout")

            return json.loads(response_line.decode())

        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_io)
        logger.debug(f"Received from MCP server {self.deployment_id}: {response}")
        return response

    async def stop(self):
        """Stop the MCP server subprocess gracefully."""
        if not self.process:
            return

        try:
            logger.info(f"Stopping MCP server for deployment {self.deployment_id}")

            if IS_WINDOWS:
                # Windows: Use synchronous terminate/kill
                self.process.terminate()
                try:
                    self.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    logger.warning(f"MCP server {self.deployment_id} did not terminate gracefully, killing")
                    self.process.kill()
                    self.process.wait()
            else:
                # Unix: Use async terminate/kill
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"MCP server {self.deployment_id} did not terminate gracefully, killing")
                    self.process.kill()
                    await self.process.wait()

            logger.info(f"MCP server stopped for deployment {self.deployment_id}")

        except Exception as e:
            logger.error(f"Error stopping MCP server {self.deployment_id}: {e}")


# Global process manager functions

async def start_server(deployment_id: str, package: str, env_vars: Dict[str, str]) -> bool:
    """
    Start an MCP server for a deployment.

    Args:
        deployment_id: Unique deployment identifier
        package: NPM/Python package name
        env_vars: Environment variables (credentials)

    Returns:
        True if started successfully
    """
    # Check if already running
    if deployment_id in _running_servers:
        logger.warning(f"MCP server already running for deployment {deployment_id}")
        return True

    # Create and start the server process
    server = ServerProcess(deployment_id, package, env_vars)
    success = await server.start()

    if success:
        _running_servers[deployment_id] = server

    return success


async def stop_server(deployment_id: str):
    """Stop the MCP server for a deployment."""
    server = _running_servers.pop(deployment_id, None)
    if server:
        await server.stop()


async def get_server(deployment_id: str) -> Optional[ServerProcess]:
    """Get the running server process for a deployment."""
    return _running_servers.get(deployment_id)


async def stop_all_servers():
    """Stop all running MCP servers (for graceful shutdown)."""
    logger.info(f"Stopping all {len(_running_servers)} MCP servers")

    for deployment_id, server in list(_running_servers.items()):
        await server.stop()

    _running_servers.clear()
