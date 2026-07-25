"""
FastAPI Application Entry Point for Relay Backend API Server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from relay import __version__
from relay.api.routes import checkpoint, benchmark

app = FastAPI(
    title="Relay API — Agent Context Continuity & Benchmark Server",
    description="REST API for structured knowledge checkpointing, hybrid retrieval, and RelayBench evaluation.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for Next.js frontend visualization & external web apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(checkpoint.router)
app.include_router(benchmark.router)


@app.get("/", tags=["System"])
def root():
    """Root metadata endpoint."""
    return {
        "status": "online",
        "service": "Relay API — Context Continuity Middleware",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "relay-ai",
        "version": __version__
    }
