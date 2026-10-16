"""Provider management services."""

import yaml
from typing import Dict, Any, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.providers import Provider, Model, ProviderType
from app.core.config import settings


async def sync_providers_from_config(session: AsyncSession) -> Dict[str, Any]:
    """Sync providers and models from YAML configuration."""
    config_path = "configs/llm_model_mapping.yaml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Fallback to archive config if available
        try:
            with open("archive/configs/llm_model_mapping.yaml", 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            return {"providers": 0, "models": 0, "error": "Config file not found"}

    providers_synced = 0
    models_synced = 0

    for provider_name, provider_config in config.get('providers', {}).items():
        # Create or update provider
        result = await session.execute(
            select(Provider).where(Provider.name == provider_name)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            provider = Provider(
                name=provider_name,
                type=ProviderType(provider_name.lower()),
                base_url=provider_config['base_url'],
                api_key_env=provider_config.get('api_key_env'),
                is_active=True
            )
            session.add(provider)
            providers_synced += 1
        else:
            # Update existing provider
            provider.base_url = provider_config['base_url']
            provider.api_key_env = provider_config.get('api_key_env')

        await session.commit()
        await session.refresh(provider)

        # Sync models for this provider
        for model_config in provider_config.get('models', []):
            result = await session.execute(
                select(Model).where(
                    Model.model_id == model_config['model_id'],
                    Model.provider_id == provider.id
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                model = Model(
                    name=model_config['name'],
                    model_id=model_config['model_id'],
                    provider_id=provider.id,
                    aliases=model_config.get('aliases', []),
                    capabilities=model_config.get('capabilities', []),
                    is_free=model_config.get('free', True),
                    is_enabled=model_config.get('enabled', True),
                    context_length=model_config.get('metadata', {}).get('context_length'),
                    description=model_config.get('metadata', {}).get('description'),
                    metadata_=model_config.get('metadata', {})
                )
                session.add(model)
                models_synced += 1
            else:
                # Update existing model
                model.name = model_config['name']
                model.aliases = model_config.get('aliases', [])
                model.capabilities = model_config.get('capabilities', [])
                model.is_free = model_config.get('free', True)
                model.is_enabled = model_config.get('enabled', True)
                model.context_length = model_config.get('metadata', {}).get('context_length')
                model.description = model_config.get('metadata', {}).get('description')
                model.metadata_ = model_config.get('metadata', {})

    await session.commit()

    return {
        "providers": providers_synced,
        "models": models_synced
    }


async def get_enabled_models(session: AsyncSession, capabilities: List[str] = None) -> List[Model]:
    """Get all enabled models, optionally filtered by capabilities."""
    query = select(Model).where(Model.is_enabled == True)

    if capabilities:
        # Filter models that have at least one of the required capabilities
        # This is a simplified implementation - in practice you might want more complex filtering
        result = await session.execute(query)
        models = result.scalars().all()
        filtered_models = []
        for model in models:
            if any(cap in model.capabilities for cap in capabilities):
                filtered_models.append(model)
        return filtered_models

    result = await session.execute(query)
    return result.scalars().all()


async def get_free_models(session: AsyncSession) -> List[Model]:
    """Get all free models."""
    result = await session.execute(
        select(Model).where(Model.is_free == True, Model.is_enabled == True)
    )
    return result.scalars().all()