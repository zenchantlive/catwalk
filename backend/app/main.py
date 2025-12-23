from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.api import health, analyze, forms, deployments, mcp, mcp_streamable, registry, auth, settings
from app.services.mcp_process_manager import stop_all_servers
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("MCP Remote Platform starting up...")
    yield
    # Shutdown
    logger.info("MCP Remote Platform shutting down, stopping all MCP servers...")
    await stop_all_servers()
    logger.info("All MCP servers stopped")

app = FastAPI(
    title="MCP Remote Platform",
    description="Backend API for MCP Remote Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Add validation error handler to log 422 errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"[VALIDATION ERROR] on {request.url}: {exc.errors()}")
    logger.error(f"[VALIDATION ERROR] Body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# Configure CORS
# Allow all origins for MCP SSE connections from Claude Desktop/Web
# Claude's infrastructure connects from various Google Cloud IPs
# In production, you may want to restrict this to specific origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MCP client compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers for SSE
)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["analysis"])
app.include_router(forms.router, prefix="/api/forms", tags=["forms"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])
app.include_router(registry.router, prefix="/api/registry", tags=["registry"])

# MCP Streamable HTTP transport (new spec 2025-06-18) - single unified endpoint
app.include_router(mcp_streamable.router, prefix="/api/mcp", tags=["mcp-streamable"])

# Legacy MCP SSE transport (deprecated 2024-11-05) - for backwards compatibility
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp-legacy"])
