from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core import settings
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)
from app.core.logging import logger, setup_logging
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize logging and database when the application starts."""
    setup_logging()

    logger.info(
        "Starting %s in %s mode",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
    )

    init_db()

    yield

    logger.info(
        "Shutting down %s",
        settings.PROJECT_NAME,
    )


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    setup_logging()

    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Production-grade decision support platform for farmers "
            "offering crop tracking, weather & market observation ingestion, "
            "deterministic indicators, decision engine assessments, "
            "price forecasting, explanations, and harvest & sell recommendations."
        ),
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------

    cors_origins = [
        str(origin).rstrip("/")
        for origin in settings.BACKEND_CORS_ORIGINS
    ]

    # Never allow "*" with credentials in production
    if settings.ENVIRONMENT == "production":
        cors_origins = [
            origin
            for origin in cors_origins
            if origin != "*"
        ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------
    # EXCEPTION HANDLERS
    # ------------------------------------------------------------

    @application.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(
        request: Request,
        exc: EntityNotFoundException,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @application.exception_handler(BusinessRuleViolationException)
    async def business_rule_violation_handler(
        request: Request,
        exc: BusinessRuleViolationException,
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled server exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ------------------------------------------------------------
    # API ROUTES
    # ------------------------------------------------------------

    application.include_router(
        api_router,
        prefix=settings.API_V1_STR,
    )

    return application


app = create_application()from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core import settings
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)
from app.core.logging import logger, setup_logging
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize logging and database when the application starts."""
    setup_logging()

    logger.info(
        "Starting %s in %s mode",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
    )

    init_db()

    yield

    logger.info(
        "Shutting down %s",
        settings.PROJECT_NAME,
    )


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    setup_logging()

    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Production-grade decision support platform for farmers "
            "offering crop tracking, weather & market observation ingestion, "
            "deterministic indicators, decision engine assessments, "
            "price forecasting, explanations, and harvest & sell recommendations."
        ),
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------

    cors_origins = [
        str(origin).rstrip("/")
        for origin in settings.BACKEND_CORS_ORIGINS
    ]

    # Never allow "*" with credentials in production
    if settings.ENVIRONMENT == "production":
        cors_origins = [
            origin
            for origin in cors_origins
            if origin != "*"
        ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------
    # EXCEPTION HANDLERS
    # ------------------------------------------------------------

    @application.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(
        request: Request,
        exc: EntityNotFoundException,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @application.exception_handler(BusinessRuleViolationException)
    async def business_rule_violation_handler(
        request: Request,
        exc: BusinessRuleViolationException,
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled server exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ------------------------------------------------------------
    # API ROUTES
    # ------------------------------------------------------------

    application.include_router(
        api_router,
        prefix=settings.API_V1_STR,
    )

    return application


app = create_application()
