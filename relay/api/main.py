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

# Enable CORS for Next.js frontend visualization
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(checkpoint.router)
app.include_router(benchmark.router)


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "relay-ai",
        "version": __version__
    }
