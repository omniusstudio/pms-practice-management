"""Main FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from api.admin import router as admin_router
from api.appointments import router as appointments_router
from api.auth import router as auth_api_router
from api.clients import router as clients_router
from api.events import router as events_router
from api.feature_flags import router as feature_flags_router
from api.ledger import router as ledger_router
from api.mock_services import router as mock_services_router
from api.notes import router as notes_router
from api.patients import router as patients_router
from api.providers import router as providers_router
from middleware.correlation import CorrelationIDMiddleware, get_correlation_id
from middleware.metrics import PrometheusMetricsMiddleware, metrics_endpoint
from middleware.session_middleware import add_session_middleware
from routers.auth_router import router as auth_router
from routers.oidc import router as oidc_router
from services.etl_pipeline import initialize_etl_pipeline
from services.event_bus import initialize_event_bus
from services.feature_flags_service import get_feature_flags_service
from utils.error_handlers import APIError, api_error_handler, general_exception_handler
from utils.logging_config import configure_structured_logging

# TrustedHostMiddleware removed - not needed for Kubernetes deployment


# Configure structured logging with PHI scrubbing
configure_structured_logging(
    environment=os.getenv("ENVIRONMENT", "development"),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json_output=(os.getenv("ENVIRONMENT", "development") == "production"),
)

logger = structlog.get_logger()

# Environment configuration
environment = os.getenv("ENVIRONMENT", "development")
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
s3_bucket = os.getenv("S3_BUCKET", "pms-analytics-data")
aws_region = os.getenv("AWS_REGION", "us-east-1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Starting PMS application", extra={"environment": environment})

    try:
        # Initialize event bus
        event_bus = initialize_event_bus(redis_url=redis_url, environment=environment)
        await event_bus.connect()

        # Initialize ETL pipeline
        etl_pipeline = initialize_etl_pipeline(
            environment=environment,
            s3_bucket=s3_bucket,
            aws_region=aws_region,
        )

        # Start ETL pipeline in background
        asyncio.create_task(etl_pipeline.start())

        # Initialize feature flags service
        feature_flags_service = get_feature_flags_service()
        logger.info(
            "Feature flags service initialized",
            extra={
                "provider": feature_flags_service.config.provider,
                "environment": feature_flags_service.config.environment,
            },
        )

        logger.info(
            "Event bus and ETL pipeline initialized",
            extra={
                "environment": environment,
                "redis_url": redis_url,
                "s3_bucket": s3_bucket,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to initialize event system",
            extra={"error": str(e)},
        )
        # Continue without event system for now

    yield

    # Shutdown
    try:
        from services.etl_pipeline import get_etl_pipeline
        from services.event_bus import get_event_bus

        # Stop ETL pipeline
        try:
            etl_pipeline = get_etl_pipeline()
            await etl_pipeline.stop()
        except Exception:
            pass

        # Disconnect event bus
        try:
            event_bus = get_event_bus()
            await event_bus.disconnect()
        except Exception:
            pass

        logger.info("Event system shutdown complete")

    except Exception as e:
        logger.error("Error during shutdown", extra={"error": str(e)})


# Create FastAPI app with lifespan manager
# Load version information
def load_version_info():
    """Load version information from various sources."""
    import json

    version_info = {
        "version": os.getenv("VERSION", "1.0.0"),
        "gitSha": os.getenv("GIT_SHA", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "releaseType": "unknown",
        "buildTime": "unknown",
    }

    # Try to read from version.json if it exists
    try:
        with open("version.json", "r") as f:
            build_info = json.load(f)
            version_info.update(build_info)
    except FileNotFoundError:
        logger.info("version.json not found, using environment variables")
    except Exception as e:
        logger.warning("Failed to read version.json", error=str(e))

    return version_info


# Load version info at startup
version_info = load_version_info()

# Security scheme for OpenAPI
security = HTTPBearer()

app = FastAPI(
    title="Mental Health Practice Management System",
    description="HIPAA-compliant Practice Management System API",
    version=version_info["version"],
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


# Custom OpenAPI schema with security schemes
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Add error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Custom 404 handler for proper error format
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    from middleware.correlation import get_correlation_id
    from utils.error_handlers import NotFoundError

    correlation_id = get_correlation_id()
    error = NotFoundError(
        message="The requested resource was not found", correlation_id=correlation_id
    )

    return JSONResponse(
        status_code=404,
        content={
            "error": error.error_type,
            "message": error.message,
            "correlation_id": error.correlation_id,
            "details": error.details or {},
        },
    )


# Add session middleware for Auth0 authentication
add_session_middleware(app)

# Add correlation ID middleware first
app.add_middleware(CorrelationIDMiddleware)

# Add metrics middleware
app.add_middleware(PrometheusMetricsMiddleware, environment=environment)

# TrustedHost middleware disabled for Kubernetes internal networking
# Kubernetes handles host validation at the ingress level

# CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
async def root(request: Request):
    """Root endpoint for health check."""
    correlation_id = get_correlation_id()
    logger.info(
        "Health check requested",
        correlation_id=correlation_id,
        endpoint="root",
    )
    return {
        "message": "Mental Health PMS API",
        "status": "healthy",
        "correlation_id": correlation_id,
    }


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    correlation_id = get_correlation_id()
    return {
        "status": "healthy",
        "service": "pms-backend",
        "correlation_id": correlation_id,
    }


@app.get("/healthz")
async def healthz():
    """Enhanced health check with version information."""
    # Reload version info to get latest updates
    current_version_info = load_version_info()

    return {
        "status": "healthy",
        "service": "pms-backend",
        "timestamp": os.getenv("BUILD_TIMESTAMP", "unknown"),
        **current_version_info,
    }


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint with database connectivity."""
    from sqlalchemy import text

    from database import get_async_db

    try:
        # Test database connectivity
        async for db in get_async_db():
            # Simple query to test connection
            await db.execute(text("SELECT 1"))
            break

        return {
            "status": "ready",
            "service": "pms-backend",
            "database": "connected",
        }
    except Exception as e:
        logger.error("Database connectivity check failed", error=str(e))
        return {
            "status": "not ready",
            "service": "pms-backend",
            "database": "disconnected",
            "error": str(e),
        }


@app.get("/version")
async def get_version():
    """Dedicated version endpoint for deployment verification."""
    current_version_info = load_version_info()

    return {
        "service": "pms-backend",
        "timestamp": os.getenv("BUILD_TIMESTAMP", "unknown"),
        "deployment": {"status": "active", "health": "healthy"},
        **current_version_info,
    }


@app.get("/error")
async def trigger_error(request: Request):
    """Test endpoint to trigger errors for alert testing."""
    logger.error("Test error endpoint triggered")
    raise ValueError("Test error for alert testing")


# Metrics endpoint
@app.get("/metrics")
async def get_metrics(request: Request):
    """Prometheus metrics endpoint."""
    return await metrics_endpoint(request)


# Include API routers
app.include_router(events_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(providers_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(ledger_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(auth_api_router, prefix="/api")
app.include_router(feature_flags_router, prefix="/api")
app.include_router(mock_services_router, prefix="/api")
app.include_router(oidc_router, prefix="/oidc")
app.include_router(auth_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
