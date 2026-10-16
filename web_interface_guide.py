#!/usr/bin/env python3
"""
Web Interface Guide - Explore and demonstrate the LLM Evaluator web interface
"""

import requests
import json
import time
from tabulate import tabulate

def get_web_interface_status():
    """Get comprehensive status of the web interface"""
    print("🌐 LLM Evaluator Web Interface Status")
    print("=" * 60)

    # Check health
    try:
        health = requests.get("http://localhost:7500/health", timeout=5).json()
        print(f"✅ App Status: {health['status']}")
        print(f"   Version: {health['version']}")
    except:
        print("❌ App not responding")
        return

    # Check providers
    try:
        providers = requests.get("http://localhost:7500/api/providers/", timeout=5).json()
        print(f"\n📡 Providers ({len(providers)}):")
        for p in providers:
            print(f"   • {p['name']} (ID: {p['id']}) - {p['type']}")
    except Exception as e:
        print(f"❌ Providers error: {e}")

    # Check provider health
    try:
        health = requests.get("http://localhost:7500/api/providers/health", timeout=5).json()
        print(f"\n💚 Provider Health:")
        for provider, status in health.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {provider}: {'Healthy' if status else 'Unhealthy'}")
    except Exception as e:
        print(f"❌ Provider health error: {e}")

def get_models_table():
    """Create a comprehensive models table"""
    print("\n📊 MODELS STATUS TABLE")
    print("=" * 80)

    all_models = []

    # Get Ollama models
    try:
        response = requests.get("http://localhost:7500/api/providers/ollama/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            for model in data.get('db_models', []):
                all_models.append({
                    'id': model['id'],
                    'name': model['name'],
                    'model_id': model['model_id'],
                    'provider': 'Ollama',
                    'enabled': "✅" if model.get('is_enabled') else "❌",
                    'capabilities': ", ".join(model.get('capabilities', [])),
                    'free': "✅" if model.get('is_free') else "❌",
                    'tests_reasoning': "N/A",
                    'tests_coding': "N/A",
                    'tests_text': "N/A",
                    'tests_vision': "N/A"
                })
    except Exception as e:
        print(f"❌ Error getting Ollama models: {e}")

    # Get OpenRouter models
    try:
        response = requests.get("http://localhost:7500/api/providers/openrouter/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            for model in data.get('db_models', []):
                all_models.append({
                    'id': model['id'],
                    'name': model['name'],
                    'model_id': model['model_id'],
                    'provider': 'OpenRouter',
                    'enabled': "✅" if model.get('is_enabled') else "❌",
                    'capabilities': ", ".join(model.get('capabilities', [])),
                    'free': "✅" if model.get('is_free') else "❌",
                    'tests_reasoning': "N/A",
                    'tests_coding': "N/A",
                    'tests_text': "N/A",
                    'tests_vision': "N/A"
                })
    except Exception as e:
        print(f"❌ Error getting OpenRouter models: {e}")

    # Get test results and populate
    try:
        results = requests.get("http://localhost:7500/api/results/runs", timeout=5).json()
        print(f"\n📋 Found {len(results)} test runs")

        # For now, just mark if any tests exist
        if results:
            for model in all_models:
                # Check if this model was tested
                for run in results:
                    if model['id'] in run.get('model_ids', []):
                        model['tests_reasoning'] = "🧪" # Test exists
    except Exception as e:
        print(f"❌ Error getting test results: {e}")

    # Create table
    if all_models:
        table_data = []
        for model in all_models[:15]:  # Show first 15 models
            table_data.append([
                model['name'][:20] + ("..." if len(model['name']) > 20 else ""),
                model['provider'],
                model['enabled'],
                model['free'],
                model['capabilities'][:15] + ("..." if len(model['capabilities']) > 15 else ""),
                model['tests_reasoning'],
                model['tests_coding'],
                model['tests_text'],
                model['tests_vision']
            ])

        headers = ["Model", "Provider", "Enabled", "Free", "Capabilities", "Reasoning", "Coding", "Text", "Vision"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nShowing {len(table_data)} of {len(all_models)} total models")
    else:
        print("❌ No models found")

def get_test_categories():
    """Get available test categories"""
    print("\n🧪 TEST CATEGORIES")
    print("=" * 40)

    try:
        categories = requests.get("http://localhost:7500/api/tests/categories", timeout=5).json()
        for cat in categories:
            print(f"ID: {cat['id']} - {cat['name']}")
            print(f"   Type: {cat['test_type']}")
            print(f"   Description: {cat['description']}")
            print()
    except Exception as e:
        print(f"❌ Error getting categories: {e}")

def get_available_endpoints():
    """Show available web interface endpoints"""
    print("\n🔗 WEB INTERFACE ENDPOINTS")
    print("=" * 40)

    endpoints = [
        ("Dashboard", "http://localhost:7500/", "Main dashboard with stats and controls"),
        ("Tests Page", "http://localhost:7500/tests", "Test configuration and execution"),
        ("Providers Page", "http://localhost:7500/providers", "Provider status and model management"),
        ("Results Page", "http://localhost:7500/results", "Test results and analytics"),
        ("API Docs", "http://localhost:7500/docs", "Interactive API documentation"),
        ("Health Check", "http://localhost:7500/health", "System health status")
    ]

    for name, url, description in endpoints:
        print(f"📄 {name}")
        print(f"   URL: {url}")
        print(f"   Description: {description}")
        print()

def demonstrate_test_execution():
    """Show how tests can be executed"""
    print("\n🚀 TEST EXECUTION METHODS")
    print("=" * 40)

    print("1. 🌐 VIA WEB INTERFACE:")
    print("   • Go to: http://localhost:7500/")
    print("   • Click '🚀 Start Test Run' button")
    print("   • Select test categories and models")
    print("   • Monitor progress in real-time")
    print()

    print("2. 📡 VIA API:")
    print("   • POST to: http://localhost:7500/api/tests/run")
    print("   • Required: test_config_ids, model_ids, run_name")
    print("   • Returns: test_run_id for monitoring")
    print()

    print("3. 🖥️  VIA COMMAND LINE:")
    print("   • make test-simple")
    print("   • make test-reasoning")
    print("   • ENABLE_LOCAL_MODELS=true python archive/test_simple.py")
    print()

    # Show current test runs
    try:
        runs = requests.get("http://localhost:7500/api/results/runs", timeout=5).json()
        if runs:
            print(f"📊 CURRENT TEST RUNS ({len(runs)}):")
            for run in runs:
                status_icon = "🟢" if run['status'] == 'completed' else "🟡" if run['status'] == 'running' else "🔴"
                print(f"   {status_icon} Run {run['id']}: {run['name']} - {run['status']}")
                print(f"      Models: {run['model_ids']}, Tests: {run['test_config_ids']}")
        else:
            print("📊 No test runs found")
    except Exception as e:
        print(f"❌ Error getting test runs: {e}")

def main():
    """Main function to demonstrate the web interface"""
    get_web_interface_status()
    get_models_table()
    get_test_categories()
    get_available_endpoints()
    demonstrate_test_execution()

    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Open http://localhost:7500 in your browser")
    print("2. Navigate to different pages to explore")
    print("3. Use the '🚀 Start Test Run' button to execute tests")
    print("4. Check /results page for test outcomes")
    print("5. Use /providers page to manage models")

if __name__ == "__main__":
    main()