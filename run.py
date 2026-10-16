"""Development runner for LLM Evaluator."""

import asyncio
import uvicorn
from app.core.config import settings


def run_dev():
    """Run development server with auto-reload."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )


def run_prod():
    """Run production server."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
        workers=4
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "prod":
        run_prod()
    else:
        run_dev()