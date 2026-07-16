"""
PRODAFLT FastAPI — Main application entry point
Gambling creative production system REST API.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import users, links, content_analysis, tz_specs, patterns, campaign_metrics, alerts, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # Startup
    print(f"🚀 PRODAFLT API v{os.getenv('APP_VERSION', '1.0.0')} starting...")
    yield
    # Shutdown
    print("🛑 PRODAFLT API shutting down...")


app = FastAPI(
    title="PRODAFLT API",
    description="Gambling Creative Production System — REST API for links, content analysis, TZ specs, campaign metrics, and alerts.",
    version=os.getenv("APP_VERSION", "1.0.0"),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
origins_raw = os.getenv("API_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(users.router)
app.include_router(links.router)
app.include_router(content_analysis.router)
app.include_router(tz_specs.router)
app.include_router(patterns.router)
app.include_router(campaign_metrics.router)
app.include_router(alerts.router)
app.include_router(stats.router)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "PRODAFLT API",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "docs": "/docs",
        "health": "/api/stats/health",
    }
