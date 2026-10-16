#!/usr/bin/env python3
"""
LLM CLI Validation Script
Validates that LLM CLI is properly set up with OpenRouter and Ollama plugins.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.llm_evaluation.test_framework.llm_cli_client import LLMCLIClient


async def validate_llm_cli_basic() -> bool:
    """Validate basic LLM CLI functionality."""
    print("🔍 Validating LLM CLI basic functionality...")
    
    client = LLMCLIClient()
    
    # Check if LLM CLI is available
    if not client.is_available():
        print("❌ LLM CLI is not available")
        print("   Please install it with: pip install llm")
        return False
    
    print("✅ LLM CLI is available")
    return True


async def validate_model_listing() -> bool:
    """Validate that we can list models."""
    print("🔍 Validating model listing...")
    
    client = LLMCLIClient()
    
    try:
        models = await client.list_models()
        
        if not models:
            print("⚠️  No models found. This might be expected if no plugins are installed.")
            return False
        
        print(f"✅ Found {len(models)} models")
        
        # Show first few models
        for i, model in enumerate(models[:5]):
            print(f"   {i+1}. {model}")
        
        if len(models) > 5:
            print(f"   ... and {len(models) - 5} more models")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return False


async def validate_openrouter_plugin() -> bool:
    """Validate OpenRouter plugin functionality."""
    print("🔍 Validating OpenRouter plugin...")
    
    client = LLMCLIClient()
    
    try:
        models = await client.list_models()
        
        # Check if we have OpenRouter models
        openrouter_models = [m for m in models if 'openrouter' in m.lower()]
        
        if not openrouter_models:
            print("⚠️  No OpenRouter models found")
            print("   This might indicate the OpenRouter plugin is not installed or configured")
            return False
        
        print(f"✅ Found {len(openrouter_models)} OpenRouter models")
        
        # Show first few OpenRouter models
        for i, model in enumerate(openrouter_models[:3]):
            print(f"   {i+1}. {model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking OpenRouter models: {e}")
        return False


async def validate_openrouter_api_key() -> bool:
    """Validate OpenRouter API key is configured."""
    print("🔍 Validating OpenRouter API key...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        return False
    
    if api_key == 'your_openrouter_api_key_here':
        print("❌ OPENROUTER_API_KEY is set to the placeholder value")
        print("   Please set your actual API key in .env file")
        return False
    
    # Check if key looks valid (basic format check)
    if len(api_key) < 10:
        print("❌ OPENROUTER_API_KEY seems too short to be valid")
        return False
    
    print("✅ OpenRouter API key is configured")
    print(f"   Key format: {api_key[:8]}...{api_key[-4:]}")
    return True


async def validate_openrouter_connection() -> bool:
    """Validate OpenRouter connection with a free model."""
    print("🔍 Validating OpenRouter connection...")
    
    client = LLMCLIClient()
    
    # Check if API key is configured first
    if not await validate_openrouter_api_key():
        return False
    
    try:
        # Use a free model for testing
        test_model = "openrouter/meta-llama/llama-3.3-8b-instruct:free"
        test_prompt = "Hello! Please respond with just 'Hello back!'"
        
        print(f"   Testing with model: {test_model}")
        print(f"   Prompt: {test_prompt}")
        
        response = await client.run_prompt(test_prompt, model=test_model)
        
        if response and response.get('success'):
            print("✅ OpenRouter connection test successful")
            print(f"   Response: {response['response'][:100]}...")
            print(f"   Response time: {response['_timing']['response_time']:.2f}s")
            return True
        else:
            error_msg = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ OpenRouter connection test failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing OpenRouter connection: {e}")
        return False


async def validate_ollama_plugin() -> bool:
    """Validate Ollama plugin functionality."""
    print("🔍 Validating Ollama plugin...")
    
    client = LLMCLIClient()
    
    try:
        models = await client.list_models()
        
        # Check if we have Ollama models
        ollama_models = [m for m in models if 'ollama' in m.lower()]
        
        if not ollama_models:
            print("ℹ️  No Ollama models found")
            print("   This is expected if Ollama is not running or no models are installed")
            return False
        
        print(f"✅ Found {len(ollama_models)} Ollama models")
        
        # Show first few Ollama models
        for i, model in enumerate(ollama_models[:3]):
            print(f"   {i+1}. {model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Ollama models: {e}")
        return False


async def validate_ollama_connection() -> bool:
    """Validate Ollama connection if available."""
    print("🔍 Validating Ollama connection...")
    
    client = LLMCLIClient()
    
    try:
        models = await client.list_models()
        ollama_models = [m for m in models if 'ollama' in m.lower()]
        
        if not ollama_models:
            print("ℹ️  No Ollama models available for testing")
            return False
        
        # Try to use the first available Ollama model
        test_model = ollama_models[0]
        test_prompt = "Hello! Please respond with just 'Hello back!'"
        
        print(f"   Testing with model: {test_model}")
        print(f"   Prompt: {test_prompt}")
        
        response = await client.run_prompt(test_prompt, model=test_model)
        
        if response and response.get('success'):
            print("✅ Ollama connection test successful")
            print(f"   Response: {response['response'][:100]}...")
            print(f"   Response time: {response['_timing']['response_time']:.2f}s")
            return True
        else:
            error_msg = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Ollama connection test failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Ollama connection: {e}")
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


async def main():
    """Main validation function."""
    print("🔍 Validating LLM CLI setup...")
    print("=" * 60)
    
    # Load environment variables
    load_environment_variables()
    
    tests = [
        ("Basic LLM CLI", validate_llm_cli_basic),
        ("Model listing", validate_model_listing),
        ("OpenRouter plugin", validate_openrouter_plugin),
        ("OpenRouter API key", validate_openrouter_api_key),
        ("OpenRouter connection", validate_openrouter_connection),
        ("Ollama plugin", validate_ollama_plugin),
        ("Ollama connection", validate_ollama_connection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
        
        print()  # Add spacing between tests
    
    # Summary
    print("=" * 60)
    print("Validation Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validations passed! LLM CLI is properly set up.")
    elif passed >= total - 2:  # Allow for Ollama not being available
        print("✅ Core validations passed! LLM CLI is working correctly.")
        print("   (Some optional features like Ollama may not be available)")
    else:
        print("⚠️  Some validations failed. Please check the setup.")
    
    return passed >= total - 2


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)