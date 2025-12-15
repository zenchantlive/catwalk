#!/bin/bash
# Build and push the MCP server Docker image to Fly.io registry
# Usage: ./build-and-push.sh

set -e  # Exit on error

echo "🔨 Building and pushing MCP server image to Fly.io..."
echo ""

# Navigate to the deploy directory
cd "$(dirname "$0")"

# Build and push
echo "Running: fly deploy --build-only --push --app catwalk-live-mcp-servers"
fly deploy --build-only --push --app catwalk-live-mcp-servers

echo ""
echo "✅ Image built and pushed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy the image name from above (registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX)"
echo "2. Run: fly secrets set FLY_MCP_IMAGE=\"<image-name>\" --app catwalk-live-backend-dev"
echo "3. Deploy backend: cd ../backend && fly deploy --app catwalk-live-backend-dev"
