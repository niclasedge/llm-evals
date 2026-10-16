"""Main FastAPI application."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.api import providers, tests, results, dashboard


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting LLM Evaluator", version=settings.app_version)
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down LLM Evaluator")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])
app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(dashboard.router, prefix="", tags=["dashboard"])


# Add error handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging."""
    try:
        body = await request.body()

        # Safely extract form data
        form_data_dict = {}
        if request.method == "POST":
            try:
                form_data = await request.form()
                form_data_dict = {key: value for key, value in form_data.items()}
            except Exception:
                form_data_dict = {"error": "Could not parse form data"}

        logger.error("Request validation error",
                    url=str(request.url),
                    method=request.method,
                    headers=dict(request.headers),
                    body=body.decode('utf-8') if body else None,
                    form_data=form_data_dict,
                    errors=exc.errors())
    except Exception as e:
        logger.error("Error in validation handler", error=str(e))

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main dashboard page - redirect to enhanced dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )