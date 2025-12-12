from fastapi import FastAPI
from app.api import health, analyze

app = FastAPI(
    title="MCP Remote Platform",
    description="Backend API for MCP Remote Platform",
    version="0.1.0"
)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["analysis"])

