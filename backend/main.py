# main.py
# FastAPI application entry point for the Nocos backend.
# Registers all API routers, configures CORS, and starts the background
# sync scheduler. Business logic lives in services/ — not here.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import config
from routers import health, issues, projects, stats, subscribers, sync
from services.sync import create_scheduler

# Configure structured logging.
# In production, pipe this to a log aggregator (e.g. Papertrail, Datadog).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Database session factory ─────────────────────────────────────────────────
# Created once at module level so it can be passed to the scheduler and routers.
# The engine is only created if DATABASE_URL is set — allowing the app to start
# without a DB for health checks and local testing.
_engine = None
_SessionLocal = None

if config.DATABASE_URL:
    _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def get_db():
    """
    FastAPI dependency that yields a database session per request.

    The session is closed in the finally block regardless of whether the
    request succeeded or raised an exception.
    """
    if _SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs startup logic before the app begins accepting requests:
      1. Validate required environment variables (fail fast on missing config)
      2. Start the background sync scheduler

    Runs cleanup on shutdown:
      1. Stop the scheduler gracefully
    """
    # Startup
    logger.info("Starting Nocos backend", extra={"env": config.APP_ENV})
    config.validate()
    logger.info("Configuration validated successfully")

    # Start the freshness sync scheduler only if we have a DB connection.
    # This allows the app to boot in environments without a DB (e.g. CI).
    scheduler = None
    if _SessionLocal is not None:
        scheduler = create_scheduler(_SessionLocal)
        scheduler.start()
        logger.info("Background sync scheduler started")

    yield  # App handles requests here

    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background sync scheduler stopped")

    logger.info("Shutting down Nocos backend")


app = FastAPI(
    title="Nocos API",
    description="Backend API for the Nocos open source discovery platform.",
    version="1.0.0",
    lifespan=lifespan,
    # API docs are disabled in production — they expose schema info unnecessarily
    docs_url=None if config.is_production else "/docs",
    redoc_url=None if config.is_production else "/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Allow all origins in development so the Next.js dev server can call the API.
# In production, restrict to nocos.cc only.
allowed_origins = (
    [
        "https://nocos.cc",
        "https://www.nocos.cc",
        # Vercel preview deployments — remove once nocos.cc domain is verified
        "https://nocos-git-main-nocos-projects-2bff4141.vercel.app",
    ]
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
app.include_router(health.router, prefix="/api/v1")
app.include_router(issues.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(subscribers.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
