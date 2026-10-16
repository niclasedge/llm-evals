#!/usr/bin/env python3
"""
Promptfoo Results Aggregator and Ranking Generator

This script analyzes all promptfoo evaluation results from the results/ directory
and generates a comprehensive ranking of all tested models across all evaluations.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box

@dataclass
class ModelStats:
    """Statistics for a single model across all evaluations"""
    name: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    total_score: float = 0.0
    total_latency_ms: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    evaluations: List[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.error_tests / self.total_tests) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency per test"""
        if self.total_tests == 0:
            return 0.0
        return self.total_latency_ms / self.total_tests

    @property
    def avg_score(self) -> float:
        """Calculate average score"""
        if self.total_tests == 0:
            return 0.0
        return self.total_score / self.total_tests


class PromptfooAnalyzer:
    """Analyzes promptfoo evaluation results and generates rankings"""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.console = Console()
        self.model_stats: Dict[str, ModelStats] = defaultdict(lambda: ModelStats(name=""))

    def load_results(self) -> None:
        """Load all JSON result files from the results directory"""
        json_files = list(self.results_dir.glob("*.json"))

        if not json_files:
            self.console.print(f"[yellow]No JSON files found in {self.results_dir}[/yellow]")
            return

        self.console.print(f"[blue]Found {len(json_files)} evaluation files[/blue]")

        for json_file in json_files:
            try:
                self._process_file(json_file)
            except Exception as e:
                self.console.print(f"[red]Error processing {json_file.name}: {e}[/red]")

    def _process_file(self, file_path: Path) -> None:
        """Process a single JSON result file"""
        with open(file_path, 'r') as f:
            data = json.load(f)

        eval_id = data.get('evalId', 'unknown')
        results = data.get('results', {})

        # Process each prompt/provider combination
        for prompt_data in results.get('prompts', []):
            provider_label = prompt_data.get('provider', 'Unknown')
            metrics = prompt_data.get('metrics', {})

            # Initialize or update model stats
            if provider_label not in self.model_stats:
                self.model_stats[provider_label].name = provider_label

            stats = self.model_stats[provider_label]

            # Aggregate metrics
            stats.total_tests += metrics.get('testPassCount', 0) + metrics.get('testFailCount', 0) + metrics.get('testErrorCount', 0)
            stats.passed_tests += metrics.get('testPassCount', 0)
            stats.failed_tests += metrics.get('testFailCount', 0)
            stats.error_tests += metrics.get('testErrorCount', 0)
            stats.total_score += metrics.get('score', 0)
            stats.total_latency_ms += metrics.get('totalLatencyMs', 0)
            stats.total_cost += metrics.get('cost', 0)

            # Token usage
            token_usage = metrics.get('tokenUsage', {})
            stats.total_tokens += token_usage.get('total', 0)

            # Track which evaluations this model appeared in
            if eval_id not in stats.evaluations:
                stats.evaluations.append(eval_id)

    def get_ranked_models(self, sort_by: str = 'pass_rate') -> List[ModelStats]:
        """
        Get models ranked by specified metric

        Args:
            sort_by: One of 'pass_rate', 'avg_score', 'total_tests', 'avg_latency_ms'
        """
        models = list(self.model_stats.values())

        # Sort based on criteria
        if sort_by == 'pass_rate':
            models.sort(key=lambda m: (m.pass_rate, -m.error_rate, -m.avg_latency_ms), reverse=True)
        elif sort_by == 'avg_score':
            models.sort(key=lambda m: (m.avg_score, m.pass_rate, -m.avg_latency_ms), reverse=True)
        elif sort_by == 'total_tests':
            models.sort(key=lambda m: (m.total_tests, m.pass_rate), reverse=True)
        elif sort_by == 'avg_latency_ms':
            models.sort(key=lambda m: m.avg_latency_ms)
        else:
            raise ValueError(f"Unknown sort criteria: {sort_by}")

        return models

    def display_rankings(self, sort_by: str = 'pass_rate', top_n: int = None) -> None:
        """Display rankings in a beautiful Rich table"""
        models = self.get_ranked_models(sort_by)

        if top_n:
            models = models[:top_n]

        # Create main table
        table = Table(
            title="🏆 LLM Model Rankings Across All Evaluations",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan"
        )

        # Add columns
        table.add_column("Rank", style="cyan", justify="right", width=6)
        table.add_column("Model", style="green", width=30)
        table.add_column("Pass Rate", justify="right", width=10)
        table.add_column("Avg Score", justify="right", width=10)
        table.add_column("Tests", justify="right", width=8)
        table.add_column("Passed", justify="right", width=8)
        table.add_column("Failed", justify="right", width=8)
        table.add_column("Errors", justify="right", width=8)
        table.add_column("Avg Latency", justify="right", width=12)
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Evals", justify="right", width=7)

        # Add rows
        for idx, model in enumerate(models, 1):
            # Color coding for pass rate
            if model.pass_rate >= 80:
                pass_rate_style = "green"
            elif model.pass_rate >= 50:
                pass_rate_style = "yellow"
            else:
                pass_rate_style = "red"

            # Color coding for errors
            error_style = "red" if model.error_tests > 0 else "green"

            table.add_row(
                f"#{idx}",
                model.name,
                f"[{pass_rate_style}]{model.pass_rate:.1f}%[/{pass_rate_style}]",
                f"{model.avg_score:.2f}",
                str(model.total_tests),
                f"[green]{model.passed_tests}[/green]",
                f"[yellow]{model.failed_tests}[/yellow]",
                f"[{error_style}]{model.error_tests}[/{error_style}]",
                f"{model.avg_latency_ms:.0f}ms",
                f"{model.total_tokens:,}",
                str(len(model.evaluations))
            )

        self.console.print(table)

    def display_summary(self) -> None:
        """Display summary statistics"""
        total_models = len(self.model_stats)
        total_evals = len(set(eval_id for stats in self.model_stats.values() for eval_id in stats.evaluations))
        total_tests = sum(stats.total_tests for stats in self.model_stats.values())

        summary = Panel(
            f"[bold]Total Models:[/bold] {total_models}\n"
            f"[bold]Total Evaluations:[/bold] {total_evals}\n"
            f"[bold]Total Tests Run:[/bold] {total_tests:,}",
            title="📊 Summary Statistics",
            border_style="blue"
        )

        self.console.print(summary)

    def display_top_performers(self, n: int = 3) -> None:
        """Display top performing models in different categories"""
        self.console.print("\n[bold cyan]🌟 Top Performers by Category[/bold cyan]\n")

        # Top by pass rate
        top_pass = self.get_ranked_models('pass_rate')[:n]
        self.console.print("[bold green]Highest Pass Rate:[/bold green]")
        for idx, model in enumerate(top_pass, 1):
            self.console.print(f"  {idx}. {model.name}: {model.pass_rate:.1f}%")

        # Top by score
        top_score = self.get_ranked_models('avg_score')[:n]
        self.console.print("\n[bold blue]Highest Average Score:[/bold blue]")
        for idx, model in enumerate(top_score, 1):
            self.console.print(f"  {idx}. {model.name}: {model.avg_score:.2f}")

        # Fastest (lowest latency)
        top_speed = self.get_ranked_models('avg_latency_ms')[:n]
        self.console.print("\n[bold yellow]Fastest Response Time:[/bold yellow]")
        for idx, model in enumerate(top_speed, 1):
            self.console.print(f"  {idx}. {model.name}: {model.avg_latency_ms:.0f}ms")

    def export_to_json(self, output_file: str = "model_rankings.json") -> None:
        """Export rankings to JSON file"""
        models = self.get_ranked_models('pass_rate')

        output_data = {
            "generated_at": Path(output_file).stat().st_mtime if Path(output_file).exists() else None,
            "total_models": len(models),
            "rankings": [
                {
                    "rank": idx,
                    "model": model.name,
                    "pass_rate": round(model.pass_rate, 2),
                    "avg_score": round(model.avg_score, 2),
                    "total_tests": model.total_tests,
                    "passed": model.passed_tests,
                    "failed": model.failed_tests,
                    "errors": model.error_tests,
                    "avg_latency_ms": round(model.avg_latency_ms, 1),
                    "total_tokens": model.total_tokens,
                    "total_cost": round(model.total_cost, 4),
                    "evaluations": model.evaluations
                }
                for idx, model in enumerate(models, 1)
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        self.console.print(f"\n[green]✓ Rankings exported to {output_file}[/green]")


def main():
    """Main execution function"""
    console = Console()

    # Display header
    console.print("\n" + "="*80)
    console.print("[bold cyan]Promptfoo Model Rankings Analyzer[/bold cyan]", justify="center")
    console.print("="*80 + "\n")

    # Initialize analyzer
    analyzer = PromptfooAnalyzer()

    # Load and process results
    with console.status("[bold green]Loading evaluation results..."):
        analyzer.load_results()

    if not analyzer.model_stats:
        console.print("[red]No results found to analyze![/red]")
        return

    # Display summary
    analyzer.display_summary()

    console.print()

    # Display main rankings table
    analyzer.display_rankings(sort_by='pass_rate')

    console.print()

    # Display top performers
    analyzer.display_top_performers(n=3)

    console.print()

    # Export to JSON
    analyzer.export_to_json("model_rankings.json")

    console.print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
