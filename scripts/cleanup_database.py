#!/usr/bin/env python3
"""
Database cleanup script to remove non-working models and fix configurations.
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
from rich.table import Table
from rich.panel import Panel

console = Console()

# Models to disable (they're causing 404/400 errors)
MODELS_TO_DISABLE = [
    "gemma-3-1b",
    "gemma-3-4b",
    "gemma-3-12b",
    "gemma-3-27b",
    "gemma-2-9b",
    "gemma-2-27b",
    "llama-3.2-11b-vision",
    "llama-3.2-90b-vision",
    "qwen2-vl-7b",
    "qwen2-vl-72b",
    "phi-4-reasoning",
    "phi-4-reasoning-plus",
    "deepseek-chat-v3",
    "deepseek-r1-zero",
    "devstral-small",
    "llama-3.3-8b"
]

async def cleanup_database():
    """Clean up database by disabling problematic models."""
    console.print(Panel.fit("🧹 Database Cleanup Tool", style="bold blue"))

    async with async_session_maker() as session:
        # Get all models
        result = await session.execute(select(Model))
        all_models = result.scalars().all()

        console.print(f"\n[blue]Found {len(all_models)} models in database[/blue]")

        # Find models to disable
        models_to_disable = []
        for model in all_models:
            if model.name in MODELS_TO_DISABLE:
                models_to_disable.append(model)

        if not models_to_disable:
            console.print("[green]✅ No problematic models found![/green]")
            return

        # Show models that will be disabled
        table = Table(title="🚫 Models to Disable", show_header=True, header_style="bold red")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Name", style="cyan")
        table.add_column("Model ID", style="yellow")
        table.add_column("Provider", style="magenta")
        table.add_column("Reason", style="red")

        for model in models_to_disable:
            provider = await session.get(Provider, model.provider_id)
            reason = "404/400 errors in OpenRouter"
            if provider and provider.name.lower() == "ollama":
                reason = "Missing in Ollama"

            table.add_row(
                str(model.id),
                model.name,
                model.model_id,
                provider.name if provider else "Unknown",
                reason
            )

        console.print(table)

        # Confirm action
        confirm = input(f"\nDisable {len(models_to_disable)} models? (y/N): ")
        if confirm.lower() != 'y':
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        # Disable the models
        disabled_count = 0
        for model in models_to_disable:
            model.is_enabled = False
            disabled_count += 1

        await session.commit()

        console.print(f"[green]✅ Disabled {disabled_count} models successfully![/green]")

        # Show remaining enabled models
        result = await session.execute(select(Model).where(Model.is_enabled == True))
        enabled_models = result.scalars().all()

        console.print(f"\n[blue]Remaining enabled models: {len(enabled_models)}[/blue]")

        # Group by provider
        provider_counts = {}
        for model in enabled_models:
            provider = await session.get(Provider, model.provider_id)
            provider_name = provider.name if provider else "Unknown"
            provider_counts[provider_name] = provider_counts.get(provider_name, 0) + 1

        for provider_name, count in provider_counts.items():
            console.print(f"  [cyan]{provider_name}:[/cyan] {count} models")

async def show_model_status():
    """Show current model status."""
    console.print(Panel.fit("📊 Current Model Status", style="bold blue"))

    async with async_session_maker() as session:
        result = await session.execute(
            select(Model, Provider)
            .join(Provider)
            .order_by(Provider.name, Model.name)
        )
        models_with_providers = result.all()

        table = Table(title="🤖 All Models", show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Name", style="cyan")
        table.add_column("Provider", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Free", justify="center")

        for model, provider in models_with_providers:
            status = "🟢 Enabled" if model.is_enabled else "🔴 Disabled"
            free_badge = "✅" if model.is_free else "💰"

            table.add_row(
                str(model.id),
                model.name,
                provider.name,
                status,
                free_badge
            )

        console.print(table)

        # Summary
        enabled_count = sum(1 for model, _ in models_with_providers if model.is_enabled)
        total_count = len(models_with_providers)

        console.print(f"\n[bold green]Summary:[/bold green] {enabled_count} enabled / {total_count} total models")

async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        await show_model_status()
    else:
        await cleanup_database()

if __name__ == "__main__":
    asyncio.run(main())