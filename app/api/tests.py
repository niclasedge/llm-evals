"""API endpoints for test management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, Request
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_session
from app.models.tests import TestCategory, TestConfig
from app.models.results import TestRun, TestStatus


router = APIRouter()
logger = structlog.get_logger()


@router.get("/categories", response_model=List[TestCategory])
async def list_test_categories(session: AsyncSession = Depends(get_session)):
    """List all test categories."""
    result = await session.execute(select(TestCategory).where(TestCategory.is_active == True))
    return result.scalars().all()


@router.get("/categories/{category_id}/configs", response_model=List[TestConfig])
async def list_category_configs(
    category_id: int,
    session: AsyncSession = Depends(get_session)
):
    """List test configurations for a category."""
    result = await session.execute(
        select(TestConfig)
        .where(TestConfig.category_id == category_id)
        .where(TestConfig.is_active == True)
    )
    return result.scalars().all()


@router.get("/configs", response_model=List[TestConfig])
async def list_test_configs(
    category_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session)
):
    """List all test configurations."""
    query = select(TestConfig).where(TestConfig.is_active == True)
    if category_id:
        query = query.where(TestConfig.category_id == category_id)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/configs/{config_id}")
async def get_test_config(
    config_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific test configuration."""
    config = await session.get(TestConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Test config not found")
    return config


@router.post("/run")
async def start_test_run(
    request: Request,
    background_tasks: BackgroundTasks,
    test_config_ids: List[int] = Form(...),
    model_ids: List[int] = Form(...),
    run_name: str = Form(...),
    run_description: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session)
):
    """Start a new test run."""
    # Log the incoming request for debugging
    try:
        body = await request.body()
        logger.info("Test run request received",
                   url=str(request.url),
                   method=request.method,
                   headers=dict(request.headers),
                   body=body.decode('utf-8') if body else None,
                   run_name=run_name,
                   test_config_ids=test_config_ids,
                   model_ids=model_ids,
                   run_description=run_description)
    except Exception as e:
        logger.error("Error logging request", error=str(e))

    from app.services.evaluation import run_tests_async

    # Create test run
    test_run = TestRun(
        name=run_name,
        description=run_description,
        test_config_ids=test_config_ids,
        model_ids=model_ids,
        total_tests=len(test_config_ids) * len(model_ids),
        status=TestStatus.PENDING
    )

    session.add(test_run)
    await session.commit()
    await session.refresh(test_run)

    # Start test execution in background
    background_tasks.add_task(
        run_tests_async,
        test_run.id,
        test_config_ids,
        model_ids
    )

    return {
        "test_run_id": test_run.id,
        "message": "Test run started successfully"
    }