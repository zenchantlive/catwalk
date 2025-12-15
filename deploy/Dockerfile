# Dockerfile for MCP Server Containers
# This image runs user-deployed MCP servers via mcp-proxy
# Each deployment creates a new machine from this image with dynamic MCP_PACKAGE env var

FROM python:3.12-slim

WORKDIR /app

# Install Node.js 20 (needed for npx to run MCP packages)
# This is the same installation as the backend - proven to work
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install mcp-proxy
# This proxies stdio MCP servers to Streamable HTTP (/mcp) and legacy SSE (/sse)
RUN pip install --no-cache-dir "mcp-proxy>=0.10.0"

# Expose port 8080 (Fly.io standard)
EXPOSE 8080

# Run mcp-proxy with dynamic MCP package
# The MCP_PACKAGE environment variable is injected by the backend when creating machines
# Example: MCP_PACKAGE=@alexarevalo.ai/mcp-server-ticktick
#
# --host=::: Listen on all interfaces including IPv6 (Fly.io private network uses IPv6)
# --port=8080: Standard Fly.io internal port
# --pass-environment: Pass all env vars to the MCP server (for credentials)
# --: Separator between proxy args and MCP server command
# npx -y: Run the MCP package from npm (auto-install if needed)
# $MCP_PACKAGE: The actual package name (dynamic)
CMD ["sh", "-c", "mcp-proxy --host=:: --port=8080 --pass-environment -- npx -y $MCP_PACKAGE"]
