"""Main FastAPI application entry point for Go Contract AI."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered contract generation and legal assistance API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Attach limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Logging middleware to debug CORS and Origins
@app.middleware("http")
async def log_origin_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        logger.info(f"Incoming request from origin: {origin}")
    response = await call_next(request)
    return response

# CORS - Secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for contract downloads (local uploads)
import os
uploads_path = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


@app.get("/health")
async def health_check():
    """Health check endpoint - no auth required."""
    return {"status": "ok", "project": settings.PROJECT_NAME}


# Global exception handler to prevent internal error exposure
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )


# =============================================================================
# ROUTERS - All CRUD endpoints organized by resource
# =============================================================================

from app.routers import (
    auth,           # Authentication: register, login, logout, password reset
    profile,        # Profile CRUD: get, update, delete user profile
    plans,          # Plans: list, get subscription plans (read-only)
    subscriptions,  # Subscriptions CRUD: create, read, update, delete
    templates,      # Templates: list, get contract templates (read-only)
    contracts,      # Contracts CRUD: generate, create, read, update, delete
    agents,         # Agents: list, get, chat with AI agents
    chat,           # General chat with AI (non-agent)
    drafts,         # Contract drafts: save, list, get, update, delete
    dashboard,      # Dashboard: user metrics and stats
)

# Authentication & User Management
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth")
app.include_router(profile.router, prefix=f"{settings.API_V1_STR}/profile")

# Subscription Management
app.include_router(plans.router, prefix=f"{settings.API_V1_STR}/plans")
app.include_router(subscriptions.router, prefix=f"{settings.API_V1_STR}/subscriptions")

# Contract Generation & Management
app.include_router(templates.router, prefix=f"{settings.API_V1_STR}/templates")
app.include_router(contracts.router, prefix=f"{settings.API_V1_STR}/contracts")
app.include_router(drafts.router, prefix=f"{settings.API_V1_STR}/drafts")
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard")

# AI Features
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents")
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat")
