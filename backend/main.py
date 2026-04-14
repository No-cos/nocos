# main.py
# FastAPI application entry point for the Nocos backend.
# Registers all API routers and configures CORS.
# The app is intentionally thin — business logic lives in services/, not here.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from routers import health, issues, projects, subscribers

# Configure structured logging.
# In production, pipe this to a log aggregator (e.g. Papertrail, Datadog).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs startup logic before the app begins accepting requests, and
    cleanup logic on shutdown. We validate config here so the app fails
    fast if required environment variables are missing.
    """
    # Startup — validate required environment variables before accepting traffic
    logger.info("Starting Nocos backend", extra={"env": config.APP_ENV})
    config.validate()
    logger.info("Configuration validated successfully")

    yield  # App runs here

    # Shutdown — clean up any resources (schedulers, DB connections)
    logger.info("Shutting down Nocos backend")


app = FastAPI(
    title="Nocos API",
    description="Backend API for the Nocos open source discovery platform.",
    version="1.0.0",
    lifespan=lifespan,
    # Disable the default /docs and /redoc in production — they expose schema info
    docs_url=None if config.is_production else "/docs",
    redoc_url=None if config.is_production else "/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Allow all origins in development so the Next.js dev server can call the API.
# In production, restrict to nocos.cc only.
allowed_origins = (
    ["https://nocos.cc", "https://www.nocos.cc"]
    if config.is_production
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
# All routes are versioned under /api/v1 from day one.
# This means we can introduce /api/v2 without breaking existing clients.
app.include_router(health.router, prefix="/api/v1")
app.include_router(issues.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(subscribers.router, prefix="/api/v1")
