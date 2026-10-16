#!/usr/bin/env python3
"""
Promptfoo CLI Integration for llm-evals

This script provides a Python interface to run promptfoo evaluations
and integrates with the existing llm-evals infrastructure.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional, List
import argparse

# Get the promptfoo directory
PROMPTFOO_DIR = Path(__file__).parent
PROJECT_ROOT = PROMPTFOO_DIR.parent

# Available evaluation configurations
EVAL_CONFIGS = {
    "basic": "configs/basic_text.yaml",
    "code": "configs/code_generation.yaml",
    "reasoning": "configs/reasoning.yaml",
}


def check_dependencies():
    """Check if required dependencies are installed."""
    # Check if pnpm is installed
    try:
        subprocess.run(["pnpm", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: pnpm is not installed. Please install Node.js and pnpm first.")
        sys.exit(1)

    # Check if promptfoo is installed
    promptfoo_installed = (PROMPTFOO_DIR / "node_modules" / "promptfoo").exists()
    if not promptfoo_installed:
        print("📦 Promptfoo not installed. Installing dependencies...")
        try:
            subprocess.run(
                ["pnpm", "install"],
                cwd=PROMPTFOO_DIR,
                check=True
            )
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            sys.exit(1)

    # Check if Ollama is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
        else:
            print("⚠️  Warning: Ollama may not be running properly")
    except Exception:
        print("⚠️  Warning: Could not connect to Ollama. Make sure it's running for local models.")


def run_evaluation(
    config: str,
    output_format: str = "json",
    watch: bool = False,
    verbose: bool = False
) -> int:
    """
    Run a promptfoo evaluation.

    Args:
        config: Name of the config file (basic, code, reasoning) or path to custom config
        output_format: Output format (json, yaml, table)
        watch: Enable watch mode for live updates
        verbose: Enable verbose output

    Returns:
        Exit code from promptfoo
    """
    # Resolve config path
    if config in EVAL_CONFIGS:
        config_path = EVAL_CONFIGS[config]
    else:
        config_path = config

    # Build command
    cmd = ["pnpm", "exec", "promptfoo", "eval", "-c", config_path]

    # Note: Don't use -o flag as config file already specifies outputPath
    # if output_format:
    #     cmd.extend(["-o", output_format])

    if watch:
        cmd.append("--watch")

    if verbose:
        cmd.append("--verbose")

    print(f"🚀 Running evaluation: {config}")
    print(f"📝 Config: {config_path}")
    print(f"💻 Command: {' '.join(cmd)}")
    print()

    # Run evaluation
    try:
        result = subprocess.run(
            cmd,
            cwd=PROMPTFOO_DIR,
            check=False
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
        return 130


def view_results(port: int = 15500):
    """Start the promptfoo web viewer."""
    print(f"🌐 Starting promptfoo web viewer on port {port}...")
    print("📊 Open http://localhost:{port} in your browser")
    print("Press Ctrl+C to stop")
    print()

    try:
        subprocess.run(
            ["pnpm", "exec", "promptfoo", "view", "--port", str(port)],
            cwd=PROMPTFOO_DIR,
            check=True
        )
    except KeyboardInterrupt:
        print("\n👋 Viewer stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting viewer: {e}")
        return 1

    return 0


def list_models():
    """List available models from Ollama."""
    print("📋 Available Ollama Models:")
    print()

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Could not list Ollama models. Make sure Ollama is installed and running.")
        return 1

    print("\n📋 OpenRouter Models:")
    print("- meta-llama/llama-3.1-8b-instruct:free")
    print("- qwen/qwen-2-7b-instruct:free")
    print("(Set OPENROUTER_API_KEY environment variable to use)")

    return 0


def show_config_info():
    """Show information about available configurations."""
    print("📚 Available Evaluation Configurations:\n")

    for name, path in EVAL_CONFIGS.items():
        full_path = PROMPTFOO_DIR / path
        print(f"  {name}:")
        print(f"    Path: {path}")

        if full_path.exists():
            # Try to read and parse the YAML to show description
            try:
                import yaml
                with open(full_path) as f:
                    config = yaml.safe_load(f)
                    if "description" in config:
                        print(f"    Description: {config['description']}")
                    if "tests" in config:
                        print(f"    Tests: {len(config['tests'])} test cases")
                    if "providers" in config:
                        print(f"    Models: {len(config['providers'])} providers")
            except Exception as e:
                print(f"    (Could not parse config: {e})")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Promptfoo evaluation CLI for llm-evals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic text evaluation
  python promptfoo_cli.py run basic

  # Run code generation evaluation with verbose output
  python promptfoo_cli.py run code --verbose

  # View results in web browser
  python promptfoo_cli.py view

  # List available models
  python promptfoo_cli.py models

  # Show configuration info
  python promptfoo_cli.py info
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an evaluation")
    run_parser.add_argument(
        "config",
        choices=list(EVAL_CONFIGS.keys()) + ["all"],
        help="Evaluation configuration to run"
    )
    run_parser.add_argument(
        "-f", "--format",
        choices=["json", "yaml", "table"],
        default="json",
        help="Output format (default: json)"
    )
    run_parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Enable watch mode"
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    # View command
    view_parser = subparsers.add_parser("view", help="View results in web browser")
    view_parser.add_argument(
        "-p", "--port",
        type=int,
        default=15500,
        help="Port for web server (default: 15500)"
    )

    # Models command
    subparsers.add_parser("models", help="List available models")

    # Info command
    subparsers.add_parser("info", help="Show configuration information")

    # Check command
    subparsers.add_parser("check", help="Check dependencies and environment")

    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0

    # Handle commands
    if args.command == "check":
        check_dependencies()
        return 0

    elif args.command == "run":
        check_dependencies()

        if args.config == "all":
            # Run all evaluations
            exit_code = 0
            for config_name in EVAL_CONFIGS.keys():
                result = run_evaluation(
                    config_name,
                    output_format=args.format,
                    watch=args.watch,
                    verbose=args.verbose
                )
                if result != 0:
                    exit_code = result
                print()
            return exit_code
        else:
            return run_evaluation(
                args.config,
                output_format=args.format,
                watch=args.watch,
                verbose=args.verbose
            )

    elif args.command == "view":
        return view_results(args.port)

    elif args.command == "models":
        return list_models()

    elif args.command == "info":
        show_config_info()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
