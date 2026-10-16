"""API endpoints for managing LLM providers and models."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.llm_client import llm_client
from app.models.providers import Provider, Model, ProviderType


router = APIRouter()


@router.get("/", response_model=List[Provider])
async def list_providers(session: AsyncSession = Depends(get_session)):
    """List all providers."""
    result = await session.execute(select(Provider))
    return result.scalars().all()


@router.get("/health")
async def check_provider_health():
    """Check health of all providers."""
    return await llm_client.health_check_all()


@router.get("/{provider_name}/models")
async def list_provider_models(
    provider_name: str,
    session: AsyncSession = Depends(get_session)
):
    """List models for a specific provider."""
    # First check database
    result = await session.execute(
        select(Model)
        .join(Provider)
        .where(Provider.name == provider_name)
    )
    db_models = result.scalars().all()

    # Also get live models from provider
    provider = llm_client.get_provider(provider_name)
    live_models = []
    if provider:
        try:
            live_models = await provider.list_models()
        except Exception:
            pass

    return {
        "provider": provider_name,
        "db_models": db_models,
        "live_models": live_models
    }


@router.post("/sync")
async def sync_providers(session: AsyncSession = Depends(get_session)):
    """Sync providers and models from configuration."""
    from app.services.providers import sync_providers_from_config

    synced = await sync_providers_from_config(session)
    return {
        "message": "Providers synced successfully",
        "providers": synced["providers"],
        "models": synced["models"]
    }