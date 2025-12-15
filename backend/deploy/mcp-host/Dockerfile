FROM python:3.11-slim

# Install Node.js 20 (LTS) for NPM-based MCP servers
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install mcp-proxy to bridge stdio -> Streamable HTTP (/mcp)
RUN pip install --no-cache-dir "mcp-proxy>=0.10.0"

# Create a working directory
WORKDIR /app

# Expose the standard Fly.io port
EXPOSE 8080

# The CMD assumes environment variables are injected:
# MCP_PACKAGE: The NPM package (e.g. @modelcontextprotocol/server-filesystem) or Python package
#
# Default entrypoint runs mcp-proxy, which spawns the MCP server.
# Using 'sh -c' allows using the environment variable in the command.
# Note: We use "npx -y" to auto-install and run without prompting.
#
# IMPORTANT: This command is a template. The actual MCP server command
# is constructed dynamically. For now, we support NPM packages out of the box.
CMD ["sh", "-c", "mcp-proxy --host=0.0.0.0 --port=8080 --pass-environment -- npx -y ${MCP_PACKAGE}"]
