#!/usr/bin/env python3
"""
CLI Tool for LLM Evaluation Tests
Rich-formatted command line interface for running and viewing test results.
"""

import asyncio
import typer
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.columns import Columns
from rich.rule import Rule
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.tests import TestCategory, TestConfig
from app.models.providers import Provider, Model
from app.models.results import TestRun, TestResult, TestStatus
from app.services.evaluation import run_tests_async

app = typer.Typer(help="🤖 LLM Evaluation CLI Tool", invoke_without_command=True)
console = Console()


@app.callback()
def main(ctx: typer.Context):
    """🤖 LLM Evaluation CLI Tool - Interactive menu system."""
    if ctx.invoked_subcommand is None:
        # Show interactive menu when no command is provided
        asyncio.run(show_interactive_menu())


async def show_interactive_menu():
    """Display interactive main menu."""
    while True:
        console.clear()
        console.print(Panel.fit("🤖 LLM Evaluation CLI Tool", style="bold blue"))

        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column("Option", style="cyan", width=4)
        menu_table.add_column("Description", style="white")

        menu_table.add_row("1", "📋 List available models")
        menu_table.add_row("2", "📝 List test configurations")
        menu_table.add_row("3", "🚀 Run evaluation tests")
        menu_table.add_row("4", "📊 View test results")
        menu_table.add_row("5", "⚡ Show system status")
        menu_table.add_row("6", "🔍 Quick model health check")
        menu_table.add_row("q", "❌ Quit")

        console.print(menu_table)
        console.print()

        choice = Prompt.ask("[bold]Select an option", choices=["1", "2", "3", "4", "5", "6", "q"], default="q")

        try:
            if choice == "1":
                await _list_models()
                input("\nPress Enter to continue...")
            elif choice == "2":
                await _list_tests()
                input("\nPress Enter to continue...")
            elif choice == "3":
                await _interactive_run_tests()
                input("\nPress Enter to continue...")
            elif choice == "4":
                await _interactive_view_results()
                input("\nPress Enter to continue...")
            elif choice == "5":
                await _show_status()
                input("\nPress Enter to continue...")
            elif choice == "6":
                await _quick_health_check()
                input("\nPress Enter to continue...")
            elif choice == "q":
                console.print("👋 Goodbye!")
                break
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            input("\nPress Enter to continue...")


async def _interactive_run_tests():
    """Interactive test run setup."""
    console.print(Panel.fit("🚀 Interactive Test Run Setup", style="bold blue"))

    # Get test run name
    run_name = Prompt.ask("\n[bold]Enter test run name", default=f"Test Run {datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Get description
    description = Prompt.ask("[bold]Enter description (optional)", default="")

    # Model selection
    console.print("\n[bold]Model Selection:[/bold]")
    console.print("1. Select specific models")
    console.print("2. Use all available models")
    console.print("3. Use only free models")

    model_choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="1")

    async with async_session_maker() as session:
        if model_choice == "1":
            selected_models = await _interactive_model_selection(session)
        elif model_choice == "2":
            result = await session.execute(select(Model).where(Model.is_enabled == True))
            selected_models = result.scalars().all()
        else:  # option 3
            result = await session.execute(select(Model).where(Model.is_enabled == True, Model.is_free == True))
            selected_models = result.scalars().all()

        if not selected_models:
            console.print("[red]No models selected![/red]")
            return

        # Test selection
        console.print("\n[bold]Test Selection:[/bold]")
        console.print("1. Select specific tests")
        console.print("2. Use all available tests")
        console.print("3. Select by category")

        test_choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="1")

        if test_choice == "1":
            selected_tests = await _interactive_test_selection(session)
        elif test_choice == "2":
            result = await session.execute(select(TestConfig).where(TestConfig.is_active == True))
            selected_tests = result.scalars().all()
        else:  # option 3
            selected_tests = await _interactive_category_selection(session)

        if not selected_tests:
            console.print("[red]No tests selected![/red]")
            return

        # Confirmation
        console.print(f"\n[bold]📊 Test Run Summary:[/bold]")
        console.print(f"[blue]Name:[/blue] {run_name}")
        if description:
            console.print(f"[blue]Description:[/blue] {description}")
        console.print(f"[blue]Models:[/blue] {len(selected_models)}")
        console.print(f"[blue]Tests:[/blue] {len(selected_tests)}")
        console.print(f"[blue]Total combinations:[/blue] {len(selected_models) * len(selected_tests)}")

        if not Confirm.ask("\nProceed with test run?"):
            console.print("[yellow]Test run cancelled.[/yellow]")
            return

        # Create and run tests
        await _run_tests(run_name, None, None, False, False, description or None, True)


async def _interactive_category_selection(session: AsyncSession) -> List[TestConfig]:
    """Interactive test selection by category."""
    # Get categories
    result = await session.execute(select(TestCategory))
    categories = result.scalars().all()

    console.print("\n[bold]Available Categories:[/bold]")
    for i, category in enumerate(categories, 1):
        console.print(f"[cyan]{i}.[/cyan] {category.name}")

    choices = Prompt.ask("\nSelect categories (comma-separated numbers)")

    try:
        indices = [int(x.strip()) - 1 for x in choices.split(',')]
        selected_categories = [categories[i] for i in indices if 0 <= i < len(categories)]

        # Get tests for selected categories
        category_ids = [cat.id for cat in selected_categories]
        result = await session.execute(
            select(TestConfig).where(TestConfig.category_id.in_(category_ids), TestConfig.is_active == True)
        )
        return result.scalars().all()
    except (ValueError, IndexError):
        console.print("[red]Invalid selection![/red]")
        return []


async def _interactive_view_results():
    """Interactive results viewing."""
    console.print(Panel.fit("📊 View Test Results", style="bold blue"))

    console.print("\n[bold]What would you like to view?[/bold]")
    console.print("1. Latest test run")
    console.print("2. All test runs")
    console.print("3. Specific test run by ID")
    console.print("4. Recent test runs")

    choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4"], default="1")

    if choice == "1":
        await _show_results(None, True, False, True)
    elif choice == "2":
        await _show_results(None, False, True, False)
    elif choice == "3":
        run_id = IntPrompt.ask("Enter test run ID")
        await _show_results(run_id, False, False, True)
    else:  # choice == "4"
        await _show_results(None, False, False, False)


async def _quick_health_check():
    """Quick health check for available models."""
    console.print(Panel.fit("🔍 Quick Model Health Check", style="bold blue"))

    async with async_session_maker() as session:
        result = await session.execute(select(Model, Provider).join(Provider).where(Model.is_enabled == True))
        models_with_providers = result.all()

        if not models_with_providers:
            console.print("[red]No models found![/red]")
            return

        console.print(f"[blue]Checking {len(models_with_providers)} models...[/blue]\n")

        health_table = Table(title="🏥 Model Health Status", show_header=True, header_style="bold blue")
        health_table.add_column("Model", style="cyan")
        health_table.add_column("Provider", style="magenta")
        health_table.add_column("Status", justify="center")
        health_table.add_column("Notes", style="dim")

        for model, provider in models_with_providers:
            # Simple health checks
            status = "🟢 OK"
            notes = "Available"

            if provider.name.lower() == "ollama":
                # Check if Ollama is accessible
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as client_session:
                        async with client_session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                data = await response.json()
                                model_names = [m['name'] for m in data.get('models', [])]
                                if model.model_id in model_names:
                                    status = "🟢 OK"
                                    notes = "Model downloaded"
                                else:
                                    status = "🟡 Missing"
                                    notes = "Model not downloaded"
                            else:
                                status = "🔴 Error"
                                notes = "Ollama not responding"
                except Exception:
                    status = "🔴 Error"
                    notes = "Ollama not accessible"
            elif provider.name.lower() == "openrouter":
                # Check API key
                import os
                if not os.getenv("OPENROUTER_API_KEY"):
                    status = "🟡 Warning"
                    notes = "API key not set"
                else:
                    status = "🟢 OK"
                    notes = "API key configured"

            health_table.add_row(model.name, provider.name, status, notes)

        console.print(health_table)

        # Summary
        ok_count = sum(1 for model, _ in models_with_providers)  # Simplified for demo
        console.print(f"\n[bold green]Health Check Complete:[/bold green] {ok_count} models checked")


@app.command("menu")
def interactive_menu():
    """🎯 Show interactive menu."""
    asyncio.run(show_interactive_menu())


@app.command("list-models")
def list_models():
    """📋 List all available models with their providers."""
    asyncio.run(_list_models())


@app.command("list-tests")
def list_tests():
    """📝 List all available test configurations."""
    asyncio.run(_list_tests())


@app.command("run")
def run_tests(
    name: str = typer.Option(..., "--name", "-n", help="Name for the test run"),
    models: Optional[List[str]] = typer.Option(None, "--model", "-m", help="Model names to test (repeat for multiple)"),
    tests: Optional[List[str]] = typer.Option(None, "--test", "-t", help="Test names to run (repeat for multiple)"),
    all_models: bool = typer.Option(False, "--all-models", help="Run tests on all available models"),
    all_tests: bool = typer.Option(False, "--all-tests", help="Run all available tests"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description for the test run"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for tests to complete"),
):
    """🚀 Run LLM evaluation tests."""
    asyncio.run(_run_tests(name, models, tests, all_models, all_tests, description, wait))


@app.command("results")
def show_results(
    run_id: Optional[int] = typer.Option(None, "--run-id", "-r", help="Show results for specific run ID"),
    latest: bool = typer.Option(False, "--latest", "-l", help="Show latest test run"),
    all_runs: bool = typer.Option(False, "--all", "-a", help="Show all test runs"),
    detailed: bool = typer.Option(False, "--detailed", "-v", help="Show detailed results"),
):
    """📊 Display test results and statistics."""
    asyncio.run(_show_results(run_id, latest, all_runs, detailed))


@app.command("status")
def show_status():
    """⚡ Show system status and health."""
    asyncio.run(_show_status())


async def _list_models():
    """List all available models."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Model, Provider)
            .join(Provider)
            .where(Model.is_enabled == True)
            .order_by(Provider.name, Model.name)
        )
        models_with_providers = result.all()

        if not models_with_providers:
            console.print("[red]No models found![/red]")
            return

        table = Table(title="🤖 Available Models", show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Model Name", style="cyan")
        table.add_column("Provider", style="magenta")
        table.add_column("Capabilities", style="green")
        table.add_column("Free", style="yellow", justify="center")
        table.add_column("Status", justify="center")

        for model, provider in models_with_providers:
            capabilities = ", ".join(model.capabilities) if model.capabilities else "N/A"
            free_badge = "✅" if model.is_free else "💰"
            status = "🟢 Active" if model.is_enabled else "🔴 Disabled"

            table.add_row(
                str(model.id),
                model.name,
                provider.name,
                capabilities,
                free_badge,
                status
            )

        console.print(table)
        console.print(f"\n[bold green]Total: {len(models_with_providers)} models[/bold green]")


async def _list_tests():
    """List all available test configurations."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(TestConfig, TestCategory)
            .join(TestCategory)
            .where(TestConfig.is_active == True)
            .order_by(TestCategory.name, TestConfig.name)
        )
        tests_with_categories = result.all()

        if not tests_with_categories:
            console.print("[red]No test configurations found![/red]")
            return

        table = Table(title="📝 Available Test Configurations", show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Test Name", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Max Tokens", style="green", justify="right")
        table.add_column("Temperature", style="blue", justify="right")

        for test_config, category in tests_with_categories:
            difficulty_color = {
                "easy": "green",
                "medium": "yellow",
                "hard": "red",
                "expert": "purple"
            }.get(test_config.difficulty.value, "white")

            table.add_row(
                str(test_config.id),
                test_config.name,
                category.name,
                f"[{difficulty_color}]{test_config.difficulty.value.upper()}[/{difficulty_color}]",
                str(test_config.max_tokens) if test_config.max_tokens else "N/A",
                str(test_config.temperature)
            )

        console.print(table)
        console.print(f"\n[bold green]Total: {len(tests_with_categories)} test configurations[/bold green]")


async def _run_tests(name: str, models: Optional[List[str]], tests: Optional[List[str]],
                    all_models: bool, all_tests: bool, description: Optional[str], wait: bool):
    """Run tests with the specified parameters."""
    console.print(Panel.fit("🚀 Starting LLM Evaluation Tests", style="bold blue"))

    async with async_session_maker() as session:
        # Get available models
        if all_models:
            model_result = await session.execute(
                select(Model).where(Model.is_enabled == True)
            )
            selected_models = model_result.scalars().all()
        elif models:
            model_result = await session.execute(
                select(Model).where(Model.name.in_(models), Model.is_enabled == True)
            )
            selected_models = model_result.scalars().all()

            # Check for missing models
            found_names = {m.name for m in selected_models}
            missing = set(models) - found_names
            if missing:
                console.print(f"[red]Warning: Models not found: {', '.join(missing)}[/red]")
        else:
            # Interactive selection
            selected_models = await _interactive_model_selection(session)

        if not selected_models:
            console.print("[red]No models selected![/red]")
            return

        # Get available test configs
        if all_tests:
            test_result = await session.execute(
                select(TestConfig).where(TestConfig.is_active == True)
            )
            selected_tests = test_result.scalars().all()
        elif tests:
            test_result = await session.execute(
                select(TestConfig).where(TestConfig.name.in_(tests), TestConfig.is_active == True)
            )
            selected_tests = test_result.scalars().all()

            # Check for missing tests
            found_names = {t.name for t in selected_tests}
            missing = set(tests) - found_names
            if missing:
                console.print(f"[red]Warning: Tests not found: {', '.join(missing)}[/red]")
        else:
            # Interactive selection
            selected_tests = await _interactive_test_selection(session)

        if not selected_tests:
            console.print("[red]No tests selected![/red]")
            return

        # Show selection summary
        console.print("\n[bold]📊 Test Run Summary:[/bold]")
        console.print(f"[blue]Name:[/blue] {name}")
        if description:
            console.print(f"[blue]Description:[/blue] {description}")
        console.print(f"[blue]Models:[/blue] {len(selected_models)}")
        console.print(f"[blue]Tests:[/blue] {len(selected_tests)}")
        console.print(f"[blue]Total combinations:[/blue] {len(selected_models) * len(selected_tests)}")

        # Create test run
        test_run = TestRun(
            name=name,
            description=description,
            test_config_ids=[t.id for t in selected_tests],
            model_ids=[m.id for m in selected_models],
            total_tests=len(selected_models) * len(selected_tests),
            status=TestStatus.PENDING
        )

        session.add(test_run)
        await session.commit()
        await session.refresh(test_run)

        console.print(f"\n[green]✅ Test run created with ID: {test_run.id}[/green]")

        if wait:
            # Start tests and show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running tests...", total=None)

                # Start the tests
                task_coro = run_tests_async(
                    test_run.id,
                    [t.id for t in selected_tests],
                    [m.id for m in selected_models]
                )
                await task_coro

                progress.update(task, description="Tests completed!")

            # Show final results
            await _show_results(run_id=test_run.id, latest=False, all_runs=False, detailed=True)
        else:
            console.print("[yellow]Tests started in background. Use 'cli_runner.py results --latest' to check progress.[/yellow]")


async def _interactive_model_selection(session: AsyncSession) -> List[Model]:
    """Interactive model selection."""
    result = await session.execute(select(Model).where(Model.is_enabled == True))
    available_models = result.scalars().all()

    console.print("\n[bold]Available Models:[/bold]")
    for i, model in enumerate(available_models, 1):
        console.print(f"[cyan]{i}.[/cyan] {model.name} ({model.provider_id})")

    choices = Prompt.ask("\nSelect models (comma-separated numbers, or 'all')")

    if choices.lower() == 'all':
        return available_models

    try:
        indices = [int(x.strip()) - 1 for x in choices.split(',')]
        return [available_models[i] for i in indices if 0 <= i < len(available_models)]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection![/red]")
        return []


async def _interactive_test_selection(session: AsyncSession) -> List[TestConfig]:
    """Interactive test selection."""
    result = await session.execute(select(TestConfig).where(TestConfig.is_active == True))
    available_tests = result.scalars().all()

    console.print("\n[bold]Available Tests:[/bold]")
    for i, test in enumerate(available_tests, 1):
        console.print(f"[cyan]{i}.[/cyan] {test.name}")

    choices = Prompt.ask("\nSelect tests (comma-separated numbers, or 'all')")

    if choices.lower() == 'all':
        return available_tests

    try:
        indices = [int(x.strip()) - 1 for x in choices.split(',')]
        return [available_tests[i] for i in indices if 0 <= i < len(available_tests)]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection![/red]")
        return []


async def _show_results(run_id: Optional[int], latest: bool, all_runs: bool, detailed: bool):
    """Show test results."""
    async with async_session_maker() as session:
        if run_id:
            # Show specific run
            test_run = await session.get(TestRun, run_id)
            if not test_run:
                console.print(f"[red]Test run {run_id} not found![/red]")
                return
            await _display_test_run(session, test_run, detailed)

        elif latest:
            # Show latest run
            result = await session.execute(
                select(TestRun).order_by(TestRun.created_at.desc()).limit(1)
            )
            test_run = result.scalar_one_or_none()
            if not test_run:
                console.print("[red]No test runs found![/red]")
                return
            await _display_test_run(session, test_run, detailed)

        elif all_runs:
            # Show all runs
            await _display_all_runs(session)

        else:
            # Show recent runs
            result = await session.execute(
                select(TestRun).order_by(TestRun.created_at.desc()).limit(10)
            )
            runs = result.scalars().all()

            if not runs:
                console.print("[red]No test runs found![/red]")
                return

            table = Table(title="📊 Recent Test Runs", show_header=True, header_style="bold blue")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Name", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Total", justify="right")
            table.add_column("Completed", justify="right", style="green")
            table.add_column("Failed", justify="right", style="red")
            table.add_column("Created", style="dim")

            for run in runs:
                status_color = {
                    TestStatus.PENDING: "yellow",
                    TestStatus.RUNNING: "blue",
                    TestStatus.COMPLETED: "green",
                    TestStatus.FAILED: "red",
                    TestStatus.TIMEOUT: "orange"
                }.get(run.status, "white")

                table.add_row(
                    str(run.id),
                    run.name,
                    f"[{status_color}]{run.status.value.upper()}[/{status_color}]",
                    str(run.total_tests),
                    str(run.completed_tests or 0),
                    str(run.failed_tests or 0),
                    run.created_at.strftime("%Y-%m-%d %H:%M")
                )

            console.print(table)
            console.print(f"\n[dim]Use --run-id <ID> to see detailed results for a specific run[/dim]")


async def _display_test_run(session: AsyncSession, test_run: TestRun, detailed: bool):
    """Display detailed information about a test run."""
    console.print(Panel.fit(f"📊 Test Run: {test_run.name}", style="bold blue"))

    # Basic info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Key", style="blue", width=15)
    info_table.add_column("Value", style="white")

    info_table.add_row("ID", str(test_run.id))
    info_table.add_row("Status", f"[bold]{test_run.status.value.upper()}[/bold]")
    info_table.add_row("Created", test_run.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    if test_run.completed_at:
        info_table.add_row("Completed", test_run.completed_at.strftime("%Y-%m-%d %H:%M:%S"))
    if test_run.duration:
        info_table.add_row("Duration", f"{test_run.duration:.2f}s")
    if test_run.description:
        info_table.add_row("Description", test_run.description)

    console.print(info_table)
    console.print()

    # Test results summary
    summary_table = Table(title="Summary", show_header=True, header_style="bold blue")
    summary_table.add_column("Metric", style="blue")
    summary_table.add_column("Count", justify="right")
    summary_table.add_column("Percentage", justify="right")

    total = test_run.total_tests
    completed = test_run.completed_tests or 0
    failed = test_run.failed_tests or 0
    pending = total - completed - failed

    summary_table.add_row("Total Tests", str(total), "100%")
    summary_table.add_row("Completed", str(completed), f"{(completed/total*100):.1f}%" if total > 0 else "0%")
    summary_table.add_row("Failed", str(failed), f"{(failed/total*100):.1f}%" if total > 0 else "0%")
    summary_table.add_row("Pending", str(pending), f"{(pending/total*100):.1f}%" if total > 0 else "0%")

    console.print(summary_table)

    if detailed:
        # Individual test results
        await _display_detailed_results(session, test_run)


async def _display_detailed_results(session: AsyncSession, test_run: TestRun):
    """Display detailed individual test results with evaluation scores."""
    from app.models.results import Evaluation

    result = await session.execute(
        select(TestResult, TestConfig, Model)
        .join(TestConfig)
        .join(Model)
        .where(TestResult.test_run_id == test_run.id)
        .order_by(Model.name, TestConfig.name)
    )
    test_results = result.all()

    if not test_results:
        console.print("[yellow]No detailed results available yet.[/yellow]")
        return

    console.print("\n" + "="*80)
    console.print("[bold]📋 Detailed Test Results with Evaluation Scores[/bold]")
    console.print("="*80)

    results_table = Table(show_header=True, header_style="bold blue")
    results_table.add_column("Model", style="cyan", width=20)
    results_table.add_column("Test", style="magenta", width=20)
    results_table.add_column("Status", justify="center", width=10)
    results_table.add_column("Response Time", justify="right", width=12)
    results_table.add_column("Score", justify="center", width=8)
    results_table.add_column("Evaluation", justify="center", width=12)

    for test_result, test_config, model in test_results:
        status_color = {
            TestStatus.PENDING: "yellow",
            TestStatus.RUNNING: "blue",
            TestStatus.COMPLETED: "green",
            TestStatus.FAILED: "red",
            TestStatus.TIMEOUT: "orange"
        }.get(test_result.status, "white")

        response_time = f"{test_result.response_time:.2f}s" if test_result.response_time else "N/A"

        # Get evaluation data
        eval_result = await session.execute(
            select(Evaluation).where(Evaluation.test_result_id == test_result.id)
        )
        evaluation = eval_result.scalars().first()

        if evaluation and evaluation.overall_score is not None:
            score_display = f"{evaluation.overall_score:.2f}"
            raw_score = evaluation.metadata_.get("raw_score", "N/A") if evaluation.metadata_ else "N/A"
            eval_status = f"{raw_score}/10" if raw_score != "N/A" else "N/A"

            # Color code the score
            if evaluation.overall_score >= 0.8:
                score_display = f"[green]{score_display}[/green]"
                eval_status = f"[green]{eval_status}[/green]"
            elif evaluation.overall_score >= 0.6:
                score_display = f"[yellow]{score_display}[/yellow]"
                eval_status = f"[yellow]{eval_status}[/yellow]"
            else:
                score_display = f"[red]{score_display}[/red]"
                eval_status = f"[red]{eval_status}[/red]"
        else:
            score_display = "[dim]N/A[/dim]"
            eval_status = "[dim]Pending[/dim]"

        results_table.add_row(
            model.name[:19] + "..." if len(model.name) > 19 else model.name,
            test_config.name[:19] + "..." if len(test_config.name) > 19 else test_config.name,
            f"[{status_color}]{test_result.status.value.upper()}[/{status_color}]",
            response_time,
            score_display,
            eval_status
        )

    console.print(results_table)

    # Show evaluation details for completed tests
    completed_results = [(r, c, m) for r, c, m in test_results if r.status == TestStatus.COMPLETED]
    if completed_results:
        console.print(f"\n[bold blue]📊 Evaluation Details ({len(completed_results)} completed tests):[/bold blue]")

        for i, (test_result, config, model) in enumerate(completed_results, 1):
            eval_result = await session.execute(
                select(Evaluation).where(Evaluation.test_result_id == test_result.id)
            )
            evaluation = eval_result.scalars().first()

            if evaluation and evaluation.overall_score is not None:
                reasoning = evaluation.metadata_.get("reasoning", "No reasoning provided") if evaluation.metadata_ else "No reasoning provided"
                raw_score = evaluation.metadata_.get("raw_score", "N/A") if evaluation.metadata_ else "N/A"

                console.print(f"\n[cyan]{i}. {model.name} - {config.name}[/cyan]")
                console.print(f"   [bold]Score:[/bold] {raw_score}/10 (normalized: {evaluation.overall_score:.2f})")
                if evaluation.accuracy_score:
                    console.print(f"   [bold]Accuracy:[/bold] {evaluation.accuracy_score:.2f}")
                if evaluation.relevance_score:
                    console.print(f"   [bold]Relevance:[/bold] {evaluation.relevance_score:.2f}")
                console.print(f"   [bold]Reasoning:[/bold] {reasoning}")

                if evaluation.strengths:
                    console.print(f"   [green]Strengths:[/green] {', '.join(evaluation.strengths)}")
                if evaluation.weaknesses:
                    console.print(f"   [red]Weaknesses:[/red] {', '.join(evaluation.weaknesses)}")

    # Show failed tests details
    failed_results = [r for r, _, _ in test_results if r.status == TestStatus.FAILED]
    if failed_results:
        console.print(f"\n[bold red]❌ Failed Tests ({len(failed_results)}):[/bold red]")
        for i, (result, config, model) in enumerate([(r, c, m) for r, c, m in test_results if r.status == TestStatus.FAILED], 1):
            console.print(f"\n[red]{i}. {model.name} - {config.name}[/red]")
            if result.error_message:
                console.print(f"   [dim]Error: {result.error_message}[/dim]")


async def _display_all_runs(session: AsyncSession):
    """Display all test runs."""
    result = await session.execute(select(TestRun).order_by(TestRun.created_at.desc()))
    runs = result.scalars().all()

    if not runs:
        console.print("[red]No test runs found![/red]")
        return

    table = Table(title="📊 All Test Runs", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Progress", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Created", style="dim")

    for run in runs:
        status_color = {
            TestStatus.PENDING: "yellow",
            TestStatus.RUNNING: "blue",
            TestStatus.COMPLETED: "green",
            TestStatus.FAILED: "red",
            TestStatus.TIMEOUT: "orange"
        }.get(run.status, "white")

        completed = run.completed_tests or 0
        total = run.total_tests
        progress = f"{completed}/{total}"

        duration = f"{run.duration:.1f}s" if run.duration else "N/A"

        table.add_row(
            str(run.id),
            run.name,
            f"[{status_color}]{run.status.value.upper()}[/{status_color}]",
            progress,
            duration,
            run.created_at.strftime("%Y-%m-%d %H:%M")
        )

    console.print(table)


async def _show_status():
    """Show system status."""
    console.print(Panel.fit("⚡ System Status", style="bold blue"))

    async with async_session_maker() as session:
        # Count models
        models_result = await session.execute(select(Model).where(Model.is_enabled == True))
        models_count = len(models_result.scalars().all())

        # Count test configs
        tests_result = await session.execute(select(TestConfig).where(TestConfig.is_active == True))
        tests_count = len(tests_result.scalars().all())

        # Count recent runs
        runs_result = await session.execute(
            select(TestRun).order_by(TestRun.created_at.desc()).limit(10)
        )
        recent_runs = runs_result.scalars().all()

        # Create status table
        status_table = Table(show_header=False, box=None)
        status_table.add_column("Metric", style="blue", width=20)
        status_table.add_column("Value", style="green")

        status_table.add_row("Available Models", str(models_count))
        status_table.add_row("Test Configurations", str(tests_count))
        status_table.add_row("Recent Runs", str(len(recent_runs)))

        console.print(status_table)

        if recent_runs:
            console.print(f"\n[bold]🕐 Latest Test Run:[/bold]")
            latest = recent_runs[0]
            console.print(f"[cyan]Name:[/cyan] {latest.name}")
            console.print(f"[cyan]Status:[/cyan] {latest.status.value.upper()}")
            console.print(f"[cyan]Created:[/cyan] {latest.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    app()