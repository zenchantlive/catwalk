# Build and push the MCP server Docker image to Fly.io registry
# Usage: .\build-and-push.ps1

Write-Host "🔨 Building and pushing MCP server image to Fly.io..." -ForegroundColor Cyan
Write-Host ""

# Navigate to the deploy directory
Set-Location $PSScriptRoot

# Build and push
Write-Host "Running: fly deploy --build-only --push --app catwalk-live-mcp-servers" -ForegroundColor Yellow
fly deploy --build-only --push --app catwalk-live-mcp-servers

Write-Host ""
Write-Host "✅ Image built and pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy the image name from above (registry.fly.io/catwalk-live-mcp-servers:deployment-XXXXXXXX)"
Write-Host "2. Run: fly secrets set FLY_MCP_IMAGE=`"<image-name>`" --app catwalk-live-backend-dev"
Write-Host "3. Deploy backend: cd ..\backend; fly deploy --app catwalk-live-backend-dev"
