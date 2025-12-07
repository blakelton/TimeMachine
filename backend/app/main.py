"""FastAPI application factory and main entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.api.routes import health
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.rate_limit import limiter, rate_limit_handler

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        version=__version__,
        environment=settings.env,
        debug=settings.debug,
    )

    # Validate authentication configuration
    if settings.auth_enabled:
        try:
            settings.validate_auth()
            logger.info("authentication_enabled", username=settings.auth_username)
        except ValueError as e:
            logger.error("authentication_config_invalid", error=str(e))
            raise

    yield

    # Shutdown
    logger.info("application_stopping")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    # Setup logging first
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title="TimeMachine API",
        description="Observation Chamber Control System for Raspberry Pi",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiter state
    app.state.limiter = limiter

    # Register exception handlers
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Include routers
    app.include_router(health.router, prefix="/api/v1")

    return app


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions.

    Args:
        request: The incoming request.
        exc: The application exception.

    Returns:
        JSON response with error details.
    """
    logger.error(
        "application_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "meta": {"timestamp": None},
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.

    Args:
        request: The incoming request.
        exc: The validation exception.

    Returns:
        JSON response with validation error details.
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            },
            "meta": {"timestamp": None},
        },
    )


# Create app instance
app = create_app()
