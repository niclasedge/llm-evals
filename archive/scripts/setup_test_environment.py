#!/usr/bin/env python3
"""
Setup script for LLM evaluation test environment.
Installs dependencies, checks requirements, and configures the testing framework.
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_requirements():
    """Install required packages."""
    print("\nInstalling requirements...")
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Requirements installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False


def install_optional_dependencies():
    """Install optional dependencies for full functionality."""
    print("\nInstalling optional dependencies...")
    
    optional_deps = [
        "aiohttp",  # For Ollama client
        "pyyaml",   # For configuration files
        "pytest",   # For testing framework
        "pytest-asyncio",  # For async testing
    ]
    
    for dep in optional_deps:
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=True, capture_output=True)
            print(f"✅ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install {dep} (optional)")


def check_llm_cli():
    """Check if Simon Willison's LLM CLI is available."""
    print("\nChecking LLM CLI availability...")
    try:
        result = subprocess.run(["llm", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ LLM CLI available: {result.stdout.strip()}")
            return True
        else:
            print("❌ LLM CLI not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ LLM CLI not found")
        print("💡 Install with: pip install llm")
        return False


async def check_ollama():
    """Check if Ollama is running and accessible."""
    print("\nChecking Ollama availability...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    print(f"✅ Ollama available with {len(models)} models")
                    for model in models[:3]:  # Show first 3 models
                        print(f"   - {model['name']}")
                    return True
                else:
                    print(f"❌ Ollama returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Ollama not accessible: {e}")
        print("💡 Start Ollama with: ollama serve")
        return False


def check_openrouter_key():
    """Check if OpenRouter API key is set."""
    print("\nChecking OpenRouter API key...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print(f"✅ OpenRouter API key set ({api_key[:8]}...)")
        return True
    else:
        print("⚠️  OpenRouter API key not set")
        print("💡 Set with: export OPENROUTER_API_KEY='your_key_here'")
        return False


def create_directories():
    """Create necessary directories."""
    print("\nCreating directories...")
    
    base_dir = Path(__file__).parent.parent
    directories = [
        base_dir / "test_results",
        base_dir / "logs",
        base_dir / "data",
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        print(f"✅ Created {directory}")


async def run_basic_test():
    """Run a basic test to verify everything works."""
    print("\nRunning basic functionality test...")
    
    try:
        # Import the test framework
        sys.path.append(str(Path(__file__).parent.parent))
        from src.features.llm_evaluation.test_framework import TestRunner
        from src.features.llm_evaluation.tests.standard_tests import TextGenerationTests
        
        # Create a simple test config
        test_config = {
            'name': 'Setup Test',
            'tests': [{
                'name': 'basic_test',
                'type': 'TextGenerationTest',
                'prompt': 'Say hello and confirm you are working.',
                'system_prompt': 'You are a helpful assistant.',
                'min_length': 5
            }]
        }
        
        async with TestRunner(test_config) as runner:
            # Try to run a simple test
            tests = runner.discover_tests()
            if tests:
                print(f"✅ Test framework loaded with {len(tests)} tests")
                return True
            else:
                print("❌ No tests discovered")
                return False
                
    except Exception as e:
        print(f"❌ Test framework error: {e}")
        return False


def print_summary(results):
    """Print setup summary."""
    print("\n" + "="*50)
    print("SETUP SUMMARY")
    print("="*50)
    
    for check, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check}")
    
    all_good = all(results.values())
    
    if all_good:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run basic tests: python scripts/run_standard_tests.py")
        print("2. Check configuration: src/features/llm_evaluation/config.py")
        print("3. Review test configs: src/features/llm_evaluation/tests/test_configs/")
    else:
        print("\n⚠️  Setup completed with some issues.")
        print("Please address the failed checks above.")
        
        if not results.get("LLM CLI", False):
            print("\nTo install LLM CLI:")
            print("pip install llm")
            
        if not results.get("Ollama", False):
            print("\nTo install and start Ollama:")
            print("1. Download from: https://ollama.ai/")
            print("2. Start with: ollama serve")
            print("3. Pull a model: ollama pull llama3.2")


async def main():
    """Main setup function."""
    print("🚀 Setting up LLM Evaluation Test Environment")
    print("=" * 50)
    
    results = {}
    
    # Check Python version
    results["Python 3.8+"] = check_python_version()
    
    # Install requirements
    results["Requirements"] = install_requirements()
    
    # Install optional dependencies
    install_optional_dependencies()
    
    # Check external tools
    results["LLM CLI"] = check_llm_cli()
    results["Ollama"] = await check_ollama()
    results["OpenRouter Key"] = check_openrouter_key()
    
    # Create directories
    create_directories()
    
    # Run basic test
    if results["Requirements"]:
        results["Test Framework"] = await run_basic_test()
    else:
        results["Test Framework"] = False
    
    # Print summary
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())