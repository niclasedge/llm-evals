#!/usr/bin/env python3
"""
Test Runner Script - Execute tests via API and populate results
"""

import requests
import json
import time
import sys

def start_test_run(category_id, models, config=None):
    """Start a test run via API"""
    url = "http://localhost:7500/api/tests/run"

    payload = {
        "test_category_id": category_id,
        "models": models,
        "test_config": config or {"max_tests": 2, "timeout": 30}
    }

    try:
        print(f"🚀 Starting test for category {category_id} with models: {models}")
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test started successfully!")
            print(f"   Run ID: {result.get('run_id', 'N/A')}")
            return result
        else:
            print(f"❌ Failed to start test: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error starting test: {e}")
        return None

def get_test_results():
    """Get all test runs"""
    try:
        response = requests.get("http://localhost:7500/api/results/runs", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_available_models():
    """Get available models from providers"""
    models = {
        "ollama": [],
        "openrouter": []
    }

    try:
        # Get Ollama models
        response = requests.get("http://localhost:7500/api/providers/ollama/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            ollama_models = [m['model_id'] for m in data.get('db_models', []) if m.get('is_enabled', False)]
            # Add some common ones from live models
            live_models = [m['name'] for m in data.get('live_models', [])]
            models["ollama"] = ollama_models[:3] + [
                m for m in live_models
                if any(word in m.lower() for word in ['phi4', 'deepseek', 'qwen2.5-coder'])
            ][:2]
    except Exception as e:
        print(f"⚠️  Could not get Ollama models: {e}")

    try:
        # Use configured OpenRouter models
        models["openrouter"] = [
            "meta-llama/llama-3.3-8b-instruct:free",
            "microsoft/phi-4-reasoning:free"
        ]
    except Exception as e:
        print(f"⚠️  Could not get OpenRouter models: {e}")

    return models

def main():
    print("🧪 LLM Evaluator Test Runner")
    print("=" * 40)

    # Get available models
    models = get_available_models()
    print(f"Available Ollama models: {models['ollama']}")
    print(f"Available OpenRouter models: {models['openrouter']}")

    # Test categories
    categories = [
        (1, "Reasoning"),
        (2, "Coding"),
        (3, "Text Generation")
    ]

    print("\n🚀 Starting test runs...")

    # Run tests for each category with a small set of models
    for category_id, category_name in categories:
        print(f"\n--- Testing {category_name} (ID: {category_id}) ---")

        # Try local models first
        test_models = []
        if models["ollama"]:
            test_models.append(models["ollama"][0])  # First Ollama model
        if models["openrouter"]:
            test_models.append(models["openrouter"][0])  # First OpenRouter model

        if test_models:
            result = start_test_run(category_id, test_models[:1])  # Test with just one model to start
            if result:
                print(f"   ✅ {category_name} test started")
            else:
                print(f"   ❌ {category_name} test failed to start")

            # Small delay between tests
            time.sleep(2)

    # Show current results
    print("\n📊 Current Test Results:")
    results = get_test_results()
    if results:
        for run in results:
            print(f"   Run {run.get('id')}: {run.get('status')} - {run.get('created_at')}")
    else:
        print("   No test results found yet")

    print("\n🌐 View results in the web interface:")
    print("   Dashboard: http://localhost:7500")
    print("   Tests: http://localhost:7500/tests")
    print("   Results: http://localhost:7500/results")

if __name__ == "__main__":
    main()