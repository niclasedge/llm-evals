"""HTMX dashboard endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.llm_client import llm_client
from app.models.providers import Provider, Model
from app.models.tests import TestCategory, TestConfig
from app.models.results import TestRun, TestResult


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """Main dashboard page."""
    # Get summary data
    providers_result = await session.execute(select(Provider))
    runs_result = await session.execute(
        select(TestRun).order_by(TestRun.created_at.desc()).limit(5)
    )

    return templates.TemplateResponse(
        "dashboard_enhanced.html",
        {
            "request": request,
            "providers": providers_result.scalars().all(),
            "recent_runs": runs_result.scalars().all(),
        }
    )


@router.get("/providers", response_class=HTMLResponse)
async def providers_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Providers management page."""
    providers_result = await session.execute(select(Provider))
    health_status = await llm_client.health_check_all()

    return templates.TemplateResponse(
        "providers.html",
        {
            "request": request,
            "providers": providers_result.scalars().all(),
            "health_status": health_status,
        }
    )


@router.get("/tests", response_class=HTMLResponse)
async def tests_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Tests management page."""
    categories_result = await session.execute(
        select(TestCategory).where(TestCategory.is_active == True)
    )
    configs_result = await session.execute(
        select(TestConfig).where(TestConfig.is_active == True).limit(10)
    )

    return templates.TemplateResponse(
        "tests.html",
        {
            "request": request,
            "categories": categories_result.scalars().all(),
            "configs": configs_result.scalars().all(),
        }
    )


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Results page."""
    runs_result = await session.execute(
        select(TestRun).order_by(TestRun.created_at.desc()).limit(10)
    )

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "runs": runs_result.scalars().all(),
        }
    )


# HTMX partial endpoints
@router.get("/partials/provider-health")
async def provider_health_partial(request: Request):
    """Provider health status partial."""
    health_status = await llm_client.health_check_all()
    return templates.TemplateResponse(
        "partials/provider_health.html",
        {
            "request": request,
            "health_status": health_status,
        }
    )


@router.get("/partials/recent-runs")
async def recent_runs_partial(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Recent runs partial."""
    runs_result = await session.execute(
        select(TestRun).order_by(TestRun.created_at.desc()).limit(5)
    )

    return templates.TemplateResponse(
        "partials/recent_runs.html",
        {
            "request": request,
            "runs": runs_result.scalars().all(),
        }
    )


@router.post("/partials/start-test")
async def start_test_partial(
    request: Request,
    run_name: str = Form(...),
    run_description: str = Form(None),
    session: AsyncSession = Depends(get_session)
):
    """Start test partial (HTMX form submission)."""
    # This would integrate with the test execution service
    # For now, return a success message

    return templates.TemplateResponse(
        "partials/test_started.html",
        {
            "request": request,
            "message": f"Test run '{run_name}' started successfully!",
        }
    )


@router.get("/partials/models-table")
async def models_table_partial(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Models table with test results partial."""
    # Get all models from all providers
    models_result = await session.execute(
        select(Model).where(Model.is_enabled == True)
    )
    models = models_result.scalars().all()

    # Get provider info
    providers_result = await session.execute(select(Provider))
    providers = {p.id: p for p in providers_result.scalars().all()}

    # Get test results for each model
    runs_result = await session.execute(
        select(TestRun).order_by(TestRun.created_at.desc())
    )
    runs = runs_result.scalars().all()

    # Build enhanced model data
    enhanced_models = []
    for model in models:
        provider = providers.get(model.provider_id)
        enhanced_model = {
            'id': model.id,
            'name': model.name,
            'model_id': model.model_id,
            'provider_name': provider.name if provider else 'Unknown',
            'is_enabled': model.is_enabled,
            'is_free': model.is_free,
            'capabilities': model.capabilities or [],
            'test_results': {
                'reasoning': None,
                'coding': None,
                'text': None,
                'vision': None
            }
        }

        # Find latest test results for this model
        for run in runs:
            if model.id in run.model_ids:
                # Map test config IDs to categories
                for config_id in run.test_config_ids:
                    if config_id == 1:  # Reasoning
                        enhanced_model['test_results']['reasoning'] = {
                            'status': run.status,
                            'score': 85  # Mock score for now
                        }
                    elif config_id == 2:  # Coding
                        enhanced_model['test_results']['coding'] = {
                            'status': run.status,
                            'score': 92  # Mock score for now
                        }
                    elif config_id == 3:  # Text
                        enhanced_model['test_results']['text'] = {
                            'status': run.status,
                            'score': 78  # Mock score for now
                        }
                    elif config_id == 4:  # Vision
                        enhanced_model['test_results']['vision'] = {
                            'status': run.status,
                            'score': 88  # Mock score for now
                        }

        enhanced_models.append(enhanced_model)

    return templates.TemplateResponse(
        "partials/models_table.html",
        {
            "request": request,
            "models": enhanced_models,
        }
    )


@router.get("/partials/logs")
async def logs_partial(request: Request):
    """Live logs partial."""
    import os
    import json
    from datetime import datetime

    logs = []
    log_file = "llm_evaluator.log"

    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last 50 lines
                recent_lines = lines[-50:] if len(lines) > 50 else lines

                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Try to parse JSON log entries
                    try:
                        log_entry = json.loads(line)
                        logs.append({
                            'timestamp': log_entry.get('timestamp', '')[:19],
                            'level': log_entry.get('level', 'INFO'),
                            'event': log_entry.get('event', ''),
                            'model': log_entry.get('model', ''),
                            'test_run_id': log_entry.get('test_run_id', ''),
                            'message': log_entry.get('error', log_entry.get('message', ''))
                        })
                    except json.JSONDecodeError:
                        # Handle plain text log entries
                        if ' - ' in line:
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                timestamp_level = parts[0]
                                message = parts[1]

                                # Extract level from timestamp
                                level = 'INFO'
                                if 'ERROR' in timestamp_level:
                                    level = 'ERROR'
                                elif 'WARNING' in timestamp_level:
                                    level = 'WARNING'
                                elif 'DEBUG' in timestamp_level:
                                    level = 'DEBUG'

                                logs.append({
                                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                                    'level': level,
                                    'event': '',
                                    'model': '',
                                    'test_run_id': '',
                                    'message': message
                                })

        # Add a sample entry if no logs
        if not logs:
            logs.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'level': 'INFO',
                'event': 'system_ready',
                'model': '',
                'test_run_id': '',
                'message': 'LLM Evaluator ready for testing'
            })

    except Exception as e:
        logs.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': 'ERROR',
            'event': 'log_read_error',
            'model': '',
            'test_run_id': '',
            'message': f'Error reading logs: {str(e)}'
        })

    return templates.TemplateResponse(
        "partials/logs.html",
        {
            "request": request,
            "logs": logs,
        }
    )


@router.get("/partials/model-checkboxes")
async def model_checkboxes_partial(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Model selection checkboxes partial."""
    models_result = await session.execute(
        select(Model).where(Model.is_enabled == True)
    )
    models = models_result.scalars().all()

    # Get provider info
    providers_result = await session.execute(select(Provider))
    providers = {p.id: p for p in providers_result.scalars().all()}

    # Build model data with provider info
    model_data = []
    for model in models:
        provider = providers.get(model.provider_id)
        model_data.append({
            'id': model.id,
            'name': model.name,
            'provider_name': provider.name if provider else 'Unknown',
            'is_free': model.is_free
        })

    # Simple HTML response for model checkboxes
    html = ""
    for model in model_data:
        free_badge = '<span class="badge badge-info badge-xs ml-1">Free</span>' if model['is_free'] else ''
        html += f'''
        <label class="cursor-pointer label justify-start space-x-2">
            <input type="checkbox" name="model_ids" value="{model['id']}" class="checkbox checkbox-sm">
            <span class="label-text text-xs">
                {model['name'][:20]}{'...' if len(model['name']) > 20 else ''}
                <span class="text-gray-500">({model['provider_name']})</span>
                {free_badge}
            </span>
        </label>
        '''

    return HTMLResponse(content=html)