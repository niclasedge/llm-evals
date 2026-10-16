"""
Unified CLI Interface for LLM Evaluations

This module provides a single command-line interface that consolidates
all evaluation types (coding, vision, tool calls, intelligence) with
LLM CLI syntax and ease of use.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import click
from datetime import datetime

from src.core.llm_unified_config import get_unified_config
from .models import (
    EvaluationType,
    OutputFormat,
    ModelSelection,
    OutputConfig,
    EvaluationRequest
)
from .service import EvaluationService


@click.group()
@click.version_option()
def cli():
    """LLM Evaluation CLI - Unified interface for all evaluation types"""
    pass


@cli.command()
@click.option('--model', '-m', 'models', multiple=True, help='Models to evaluate (supports LLM CLI format)')
@click.option('--provider', '-p', 'providers', multiple=True, help='Filter by provider')
@click.option('--capability', '-c', 'capabilities', multiple=True, help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only use free models')
@click.option('--problems', multiple=True, help='Specific problems to test')
@click.option('--languages', multiple=True, help='Programming languages to test')
@click.option('--difficulty', help='Problem difficulty filter')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'markdown', 'csv', 'console']),
              default='console', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--no-progress', is_flag=True, help='Disable progress indicators')
@click.option('--timeout', type=int, default=300, help='Timeout in seconds')
@click.option('--parallel/--sequential', default=True, help='Run evaluations in parallel')
def coding(models, providers, capabilities, free_only, problems, languages, 
          difficulty, output, output_format, verbose, no_progress, timeout, parallel):
    """Run coding evaluation tests"""
    
    # Build model selection
    model_selection = ModelSelection(
        models=list(models) if models else [],
        providers=list(providers),
        capabilities=list(capabilities),
        free_only=free_only
    )
    
    # Build output config
    output_config = OutputConfig(
        format=OutputFormat(output_format),
        file_path=Path(output) if output else None,
        verbose=verbose,
        progress=not no_progress
    )
    
    # Build evaluation request
    request = EvaluationRequest(
        evaluation_type=EvaluationType.CODING,
        model_selection=model_selection,
        output_config=output_config,
        problems=list(problems) if problems else None,
        languages=list(languages) if languages else None,
        difficulty=difficulty,
        timeout=timeout,
        parallel=parallel
    )
    
    # Run evaluation
    asyncio.run(_run_evaluation(request))


@cli.command()
@click.option('--model', '-m', 'models', multiple=True, help='Models to evaluate (supports LLM CLI format)')
@click.option('--provider', '-p', 'providers', multiple=True, help='Filter by provider')
@click.option('--capability', '-c', 'capabilities', multiple=True, help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only use free models')
@click.option('--images', multiple=True, help='Specific images to test')
@click.option('--categories', multiple=True, help='Vision test categories')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'markdown', 'csv', 'console']),
              default='console', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--no-progress', is_flag=True, help='Disable progress indicators')
@click.option('--timeout', type=int, default=300, help='Timeout in seconds')
@click.option('--parallel/--sequential', default=True, help='Run evaluations in parallel')
def vision(models, providers, capabilities, free_only, images, categories,
          output, output_format, verbose, no_progress, timeout, parallel):
    """Run vision evaluation tests"""
    
    # Build model selection
    model_selection = ModelSelection(
        models=list(models) if models else [],
        providers=list(providers),
        capabilities=list(capabilities) if capabilities else ['vision'],
        free_only=free_only
    )
    
    # Build output config
    output_config = OutputConfig(
        format=OutputFormat(output_format),
        file_path=Path(output) if output else None,
        verbose=verbose,
        progress=not no_progress
    )
    
    # Build evaluation request
    request = EvaluationRequest(
        evaluation_type=EvaluationType.VISION,
        model_selection=model_selection,
        output_config=output_config,
        images=list(images) if images else None,
        categories=list(categories) if categories else None,
        timeout=timeout,
        parallel=parallel
    )
    
    # Run evaluation
    asyncio.run(_run_evaluation(request))


@cli.command()
@click.option('--model', '-m', 'models', multiple=True, help='Models to evaluate (supports LLM CLI format)')
@click.option('--provider', '-p', 'providers', multiple=True, help='Filter by provider')
@click.option('--capability', '-c', 'capabilities', multiple=True, help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only use free models')
@click.option('--scenarios', multiple=True, help='Tool call scenarios to test')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'markdown', 'csv', 'console']),
              default='console', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--no-progress', is_flag=True, help='Disable progress indicators')
@click.option('--timeout', type=int, default=300, help='Timeout in seconds')
@click.option('--parallel/--sequential', default=True, help='Run evaluations in parallel')
def tools(models, providers, capabilities, free_only, scenarios,
         output, output_format, verbose, no_progress, timeout, parallel):
    """Run tool call evaluation tests"""
    
    # Build model selection
    model_selection = ModelSelection(
        models=list(models) if models else [],
        providers=list(providers),
        capabilities=list(capabilities),
        free_only=free_only
    )
    
    # Build output config
    output_config = OutputConfig(
        format=OutputFormat(output_format),
        file_path=Path(output) if output else None,
        verbose=verbose,
        progress=not no_progress
    )
    
    # Build evaluation request
    request = EvaluationRequest(
        evaluation_type=EvaluationType.TOOLS,
        model_selection=model_selection,
        output_config=output_config,
        scenarios=list(scenarios) if scenarios else None,
        timeout=timeout,
        parallel=parallel
    )
    
    # Run evaluation
    asyncio.run(_run_evaluation(request))


@cli.command()
@click.option('--model', '-m', 'models', multiple=True, help='Models to evaluate (supports LLM CLI format)')
@click.option('--provider', '-p', 'providers', multiple=True, help='Filter by provider')
@click.option('--capability', '-c', 'capabilities', multiple=True, help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only use free models')
@click.option('--categories', multiple=True, help='Intelligence test categories')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'markdown', 'csv', 'console']),
              default='console', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--no-progress', is_flag=True, help='Disable progress indicators')
@click.option('--timeout', type=int, default=300, help='Timeout in seconds')
@click.option('--parallel/--sequential', default=True, help='Run evaluations in parallel')
def intelligence(models, providers, capabilities, free_only, categories,
                output, output_format, verbose, no_progress, timeout, parallel):
    """Run intelligence/reasoning evaluation tests"""
    
    # Build model selection
    model_selection = ModelSelection(
        models=list(models) if models else [],
        providers=list(providers),
        capabilities=list(capabilities),
        free_only=free_only
    )
    
    # Build output config
    output_config = OutputConfig(
        format=OutputFormat(output_format),
        file_path=Path(output) if output else None,
        verbose=verbose,
        progress=not no_progress
    )
    
    # Build evaluation request
    request = EvaluationRequest(
        evaluation_type=EvaluationType.INTELLIGENCE,
        model_selection=model_selection,
        output_config=output_config,
        categories=list(categories) if categories else None,
        timeout=timeout,
        parallel=parallel
    )
    
    # Run evaluation
    asyncio.run(_run_evaluation(request))


@cli.command()
@click.option('--models', multiple=True, help='Models to evaluate (supports LLM CLI format)')
@click.option('--provider', '-p', 'providers', multiple=True, help='Filter by provider')
@click.option('--capability', '-c', 'capabilities', multiple=True, help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only use free models')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['json', 'markdown', 'csv', 'console']),
              default='console', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--no-progress', is_flag=True, help='Disable progress indicators')
@click.option('--timeout', type=int, default=600, help='Timeout in seconds')
@click.option('--parallel/--sequential', default=True, help='Run evaluations in parallel')
def all(models, providers, capabilities, free_only, output, output_format, 
        verbose, no_progress, timeout, parallel):
    """Run comprehensive evaluation across all types"""
    
    # Build model selection
    model_selection = ModelSelection(
        models=list(models) if models else [],
        providers=list(providers),
        capabilities=list(capabilities),
        free_only=free_only
    )
    
    # Build output config
    output_config = OutputConfig(
        format=OutputFormat(output_format),
        file_path=Path(output) if output else None,
        verbose=verbose,
        progress=not no_progress
    )
    
    # Build evaluation request
    request = EvaluationRequest(
        evaluation_type=EvaluationType.ALL,
        model_selection=model_selection,
        output_config=output_config,
        timeout=timeout,
        parallel=parallel
    )
    
    # Run evaluation
    asyncio.run(_run_evaluation(request))


@cli.command()
@click.option('--provider', '-p', help='Filter by provider')
@click.option('--capability', '-c', help='Filter by capability')
@click.option('--free-only', is_flag=True, help='Only show free models')
@click.option('--enabled-only', is_flag=True, default=True, help='Only show enabled models')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'list']),
              default='table', help='Output format')
def models(provider, capability, free_only, enabled_only, output_format):
    """List available models"""
    
    config = get_unified_config()
    available_models = config.list_models(
        provider=provider,
        capability=capability,
        free_only=free_only,
        enabled_only=enabled_only
    )
    
    if output_format == 'json':
        import json
        model_data = [
            {
                'name': m.name,
                'provider': m.provider,
                'model_id': m.model_id,
                'aliases': m.aliases,
                'capabilities': m.capabilities,
                'free': m.free,
                'enabled': m.enabled
            }
            for m in available_models
        ]
        click.echo(json.dumps(model_data, indent=2))
    
    elif output_format == 'list':
        for model in available_models:
            click.echo(f"{model.name} ({model.provider})")
    
    else:  # table format
        click.echo("Available Models:")
        click.echo("================")
        for model in available_models:
            capabilities_str = ', '.join(model.capabilities)
            aliases_str = ', '.join(model.aliases) if model.aliases else 'None'
            free_str = 'Free' if model.free else 'Paid'
            click.echo(f"Name: {model.name}")
            click.echo(f"  Provider: {model.provider}")
            click.echo(f"  Model ID: {model.model_id}")
            click.echo(f"  Aliases: {aliases_str}")
            click.echo(f"  Capabilities: {capabilities_str}")
            click.echo(f"  Cost: {free_str}")
            click.echo()


@cli.command()
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['table', 'json', 'list']),
              default='table', help='Output format')
def providers(output_format):
    """List available providers"""
    
    config = get_unified_config()
    available_providers = config.list_providers()
    
    if output_format == 'json':
        import json
        provider_data = {
            provider: config.get_provider_config(provider)
            for provider in available_providers
        }
        click.echo(json.dumps(provider_data, indent=2))
    
    elif output_format == 'list':
        for provider in available_providers:
            click.echo(provider)
    
    else:  # table format
        click.echo("Available Providers:")
        click.echo("===================")
        for provider in available_providers:
            provider_config = config.get_provider_config(provider)
            models_count = len(provider_config.get('models', []))
            click.echo(f"Provider: {provider}")
            click.echo(f"  Models: {models_count}")
            if 'base_url' in provider_config:
                click.echo(f"  Base URL: {provider_config['base_url']}")
            click.echo()


@cli.command()
@click.argument('model_name')
def test_model(model_name):
    """Test model connectivity and availability"""
    
    config = get_unified_config()
    model = config.resolve_model_name(model_name)
    
    if not model:
        click.echo(f"❌ Model '{model_name}' not found")
        return
    
    click.echo(f"Testing model: {model.name}")
    click.echo(f"Provider: {model.provider}")
    click.echo(f"Model ID: {model.model_id}")
    
    # Test availability
    if config.validate_model_availability(model_name):
        click.echo("✅ Model is available and properly configured")
    else:
        click.echo("❌ Model is not available or not properly configured")
        if model.provider == 'openrouter':
            api_key = config.get_api_key('openrouter')
            if not api_key:
                click.echo("   - Missing OPENROUTER_API_KEY environment variable")


async def _run_evaluation(request: EvaluationRequest):
    """Run the evaluation with the given request"""
    
    try:
        service = EvaluationService()
        
        # Show initial configuration
        if request.output_config.verbose:
            click.echo(f"Evaluation Type: {request.evaluation_type.value}")
            click.echo(f"Models: {request.model_selection.models}")
            click.echo(f"Output Format: {request.output_config.format.value}")
            click.echo()
        
        # Run evaluation
        result = await service.run_evaluation(request)
        
        # Output results
        from .formatters import get_formatter
        formatter = get_formatter(request.output_config.format)
        output = formatter.format_result(result)
        
        if request.output_config.file_path:
            with open(request.output_config.file_path, 'w') as f:
                f.write(output)
            click.echo(f"Results saved to: {request.output_config.file_path}")
        else:
            click.echo(output)
            
    except Exception as e:
        click.echo(f"❌ Evaluation failed: {str(e)}", err=True)
        if request.output_config.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()