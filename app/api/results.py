"""API endpoints for test results and evaluations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.results import TestRun, TestResult, Evaluation


router = APIRouter()


@router.get("/runs", response_model=List[TestRun])
async def list_test_runs(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
):
    """List test runs."""
    result = await session.execute(
        select(TestRun)
        .order_by(TestRun.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/runs/{run_id}")
async def get_test_run(
    run_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific test run with results."""
    test_run = await session.get(TestRun, run_id)
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    # Get results
    result = await session.execute(
        select(TestResult).where(TestResult.test_run_id == run_id)
    )
    test_results = result.scalars().all()

    return {
        "test_run": test_run,
        "test_results": test_results,
        "summary": {
            "total": len(test_results),
            "completed": len([r for r in test_results if r.status == "completed"]),
            "failed": len([r for r in test_results if r.status == "failed"]),
            "pending": len([r for r in test_results if r.status == "pending"]),
        }
    }


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all results for a test run."""
    result = await session.execute(
        select(TestResult).where(TestResult.test_run_id == run_id)
    )
    return result.scalars().all()


@router.get("/results/{result_id}/evaluations")
async def get_result_evaluations(
    result_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get evaluations for a test result."""
    result = await session.execute(
        select(Evaluation).where(Evaluation.test_result_id == result_id)
    )
    return result.scalars().all()


@router.get("/analytics/summary")
async def get_analytics_summary(session: AsyncSession = Depends(get_session)):
    """Get analytics summary."""
    # Get total counts
    runs_result = await session.execute(select(TestRun))
    results_result = await session.execute(select(TestResult))

    runs = runs_result.scalars().all()
    results = results_result.scalars().all()

    return {
        "total_runs": len(runs),
        "total_results": len(results),
        "completed_runs": len([r for r in runs if r.status == "completed"]),
        "avg_response_time": sum([r.response_time or 0 for r in results]) / max(len(results), 1),
        "success_rate": len([r for r in results if r.status == "completed"]) / max(len(results), 1),
    }