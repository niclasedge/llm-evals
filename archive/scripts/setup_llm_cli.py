#!/usr/bin/env python3
"""
LLM CLI Setup Script
Sets up Simon Willison's LLM CLI with OpenRouter and Ollama plugins.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional


def run_command(cmd: List[str], timeout: int = 60) -> Dict[str, any]:
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }


def check_llm_cli_installed() -> bool:
    """Check if LLM CLI is installed."""
    result = run_command(['llm', '--version'])
    return result['success']


def install_llm_cli() -> bool:
    """Install LLM CLI if not present."""
    if check_llm_cli_installed():
        print("✅ LLM CLI is already installed")
        return True
    
    print("📦 Installing LLM CLI...")
    result = run_command([sys.executable, '-m', 'pip', 'install', 'llm'])
    
    if result['success']:
        print("✅ LLM CLI installed successfully")
        return True
    else:
        print(f"❌ Failed to install LLM CLI: {result['stderr']}")
        return False


def install_plugin(plugin_name: str) -> bool:
    """Install a specific LLM CLI plugin."""
    print(f"📦 Installing {plugin_name}...")
    result = run_command(['llm', 'install', plugin_name])
    
    if result['success']:
        print(f"✅ {plugin_name} installed successfully")
        return True
    else:
        print(f"❌ Failed to install {plugin_name}: {result['stderr']}")
        return False


def configure_openrouter_key() -> bool:
    """Configure OpenRouter API key."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("⚠️  OPENROUTER_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        return False
    
    if api_key == 'your_openrouter_api_key_here':
        print("⚠️  OPENROUTER_API_KEY is set to the placeholder value")
        print("   Please set your actual API key in .env file")
        return False
    
    print("🔑 Configuring OpenRouter API key...")
    
    # Use llm keys set command
    try:
        process = subprocess.Popen(
            ['llm', 'keys', 'set', 'openrouter'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=api_key)
        
        if process.returncode == 0:
            print("✅ OpenRouter API key configured successfully")
            return True
        else:
            print(f"❌ Failed to configure OpenRouter API key: {stderr}")
            return False
    except Exception as e:
        print(f"❌ Error configuring OpenRouter API key: {e}")
        return False


def test_openrouter_connection() -> bool:
    """Test OpenRouter connection with a free model."""
    print("🧪 Testing OpenRouter connection...")
    
    # Use a free model for testing
    test_model = "openrouter/meta-llama/llama-3.3-8b-instruct:free"
    test_prompt = "Hello, world!"
    
    result = run_command([
        'llm', '-m', test_model, test_prompt
    ], timeout=30)
    
    if result['success'] and result['stdout']:
        print("✅ OpenRouter connection test successful")
        print(f"   Response: {result['stdout'][:100]}...")
        return True
    else:
        print(f"❌ OpenRouter connection test failed: {result['stderr']}")
        return False


def test_ollama_connection() -> bool:
    """Test Ollama connection if available."""
    print("🧪 Testing Ollama connection...")
    
    # Check if Ollama is running
    ollama_result = run_command(['ollama', 'list'])
    if not ollama_result['success']:
        print("ℹ️  Ollama is not running or not installed")
        return False
    
    # Try to use LLM CLI with Ollama
    result = run_command([
        'llm', 'models', 'list'
    ])
    
    if result['success']:
        # Check if any ollama models are listed
        if 'ollama' in result['stdout'].lower():
            print("✅ Ollama connection test successful")
            return True
        else:
            print("ℹ️  Ollama is running but no models are available via LLM CLI")
            return False
    else:
        print(f"❌ Ollama connection test failed: {result['stderr']}")
        return False


def list_available_models() -> bool:
    """List available models."""
    print("📋 Listing available models...")
    
    result = run_command(['llm', 'models', 'list'])
    
    if result['success']:
        print("Available models:")
        for line in result['stdout'].split('\n'):
            if line.strip():
                print(f"  {line}")
        return True
    else:
        print(f"❌ Failed to list models: {result['stderr']}")
        return False


def load_environment_variables():
    """Load environment variables from .env file if it exists."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📋 Loaded environment variables from {env_path}")
        else:
            print("ℹ️  No .env file found. Using system environment variables.")
    except ImportError:
        print("ℹ️  python-dotenv not installed. Using system environment variables.")


def main():
    """Main setup function."""
    print("🚀 Setting up LLM CLI with OpenRouter and Ollama plugins...")
    print("=" * 60)
    
    # Load environment variables
    load_environment_variables()
    
    success_count = 0
    total_steps = 0
    
    # Step 1: Install LLM CLI
    total_steps += 1
    if install_llm_cli():
        success_count += 1
    
    # Step 2: Install OpenRouter plugin
    total_steps += 1
    if install_plugin('llm-openrouter'):
        success_count += 1
    
    # Step 3: Install Ollama plugin
    total_steps += 1
    if install_plugin('llm-ollama'):
        success_count += 1
    
    # Step 4: Configure OpenRouter API key
    total_steps += 1
    if configure_openrouter_key():
        success_count += 1
    
    # Step 5: Test OpenRouter connection
    total_steps += 1
    if test_openrouter_connection():
        success_count += 1
    
    # Step 6: Test Ollama connection (optional)
    total_steps += 1
    if test_ollama_connection():
        success_count += 1
    
    # Step 7: List available models
    total_steps += 1
    if list_available_models():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Setup Summary: {success_count}/{total_steps} steps completed successfully")
    
    if success_count == total_steps:
        print("🎉 LLM CLI setup completed successfully!")
        print("\nNext steps:")
        print("1. Set your actual API key in .env file")
        print("2. Run 'make validate-llm-cli' to test the setup")
        print("3. Try: llm -m openrouter/meta-llama/llama-3.3-8b-instruct:free 'Hello!'")
        return True
    else:
        print("⚠️  Some setup steps failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)