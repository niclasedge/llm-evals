#!/usr/bin/env python3
"""
Add working OpenRouter models to the database.
"""

import asyncio
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.providers import Model, Provider
from rich.console import Console
from rich.panel import Panel

console = Console()

# Working OpenRouter models
WORKING_OPENROUTER_MODELS = [
    {
        "name": "llama-3.1-8b-openrouter",
        "model_id": "meta-llama/llama-3.1-8b-instruct:free",
        "capabilities": ["text", "code"],
        "description": "Meta's Llama 3.1 8B parameter model"
    },
    {
        "name": "qwen2-7b-openrouter",
        "model_id": "qwen/qwen-2-7b-instruct:free",
        "capabilities": ["text", "code"],
        "description": "Qwen2 7B model with strong coding capabilities"
    }
]

async def add_working_models():
    """Add working OpenRouter models to the database."""
    console.print(Panel.fit("➕ Adding Working OpenRouter Models", style="bold green"))

    async with async_session_maker() as session:
        # Get OpenRouter provider
        result = await session.execute(select(Provider).where(Provider.name == "openrouter"))
        openrouter_provider = result.scalar_one_or_none()

        if not openrouter_provider:
            console.print("[red]❌ OpenRouter provider not found![/red]")
            return

        console.print(f"[blue]Found OpenRouter provider (ID: {openrouter_provider.id})[/blue]")

        added_count = 0
        for model_data in WORKING_OPENROUTER_MODELS:
            # Check if model already exists
            result = await session.execute(
                select(Model).where(Model.name == model_data["name"])
            )
            existing_model = result.scalar_one_or_none()

            if existing_model:
                # Enable if disabled
                if not existing_model.is_enabled:
                    existing_model.is_enabled = True
                    console.print(f"[yellow]✅ Re-enabled existing model: {model_data['name']}[/yellow]")
                    added_count += 1
                else:
                    console.print(f"[dim]⏭️  Model already exists and enabled: {model_data['name']}[/dim]")
            else:
                # Create new model
                new_model = Model(
                    name=model_data["name"],
                    model_id=model_data["model_id"],
                    provider_id=openrouter_provider.id,
                    capabilities=model_data["capabilities"],
                    is_enabled=True,
                    is_free=True,
                    description=model_data["description"]
                )
                session.add(new_model)
                console.print(f"[green]➕ Added new model: {model_data['name']}[/green]")
                added_count += 1

        await session.commit()

        console.print(f"\n[bold green]✅ Successfully processed {added_count} models![/bold green]")

        # Show current OpenRouter models
        result = await session.execute(
            select(Model).where(
                Model.provider_id == openrouter_provider.id,
                Model.is_enabled == True
            )
        )
        enabled_openrouter_models = result.scalars().all()

        console.print(f"\n[blue]Enabled OpenRouter models: {len(enabled_openrouter_models)}[/blue]")
        for model in enabled_openrouter_models:
            console.print(f"  [cyan]• {model.name}[/cyan] ({model.model_id})")

if __name__ == "__main__":
    asyncio.run(add_working_models())