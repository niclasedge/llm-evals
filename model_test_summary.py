#!/usr/bin/env python3
"""
Comprehensive Model Test Summary Generator
Creates a table showing all available models and their test results
"""

import json
import requests
import sys
from tabulate import tabulate
from datetime import datetime

def get_ollama_models():
    """Get available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get('models', []):
                size_gb = model['size'] / (1024**3)
                models.append({
                    'name': model['name'],
                    'provider': 'Ollama (Local)',
                    'size': f"{size_gb:.1f}GB",
                    'type': 'Free',
                    'capabilities': get_model_capabilities(model['name'])
                })
            return models
    except:
        return []

def get_openrouter_free_models():
    """Get free models from OpenRouter"""
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            free_models = []
            for model in data.get('data', []):
                pricing = model.get('pricing', {})
                if pricing.get('prompt') == '0' or pricing.get('prompt') == 0:
                    free_models.append({
                        'name': model['id'],
                        'provider': 'OpenRouter',
                        'size': 'N/A',
                        'type': 'Free',
                        'capabilities': ['text']  # Default capability
                    })
            return free_models[:20]  # Limit to first 20
    except:
        return []

def get_model_capabilities(model_name):
    """Determine model capabilities based on name"""
    capabilities = ['text']

    if any(word in model_name.lower() for word in ['coder', 'code', 'programming']):
        capabilities.append('code')
    if any(word in model_name.lower() for word in ['vision', 'visual', 'vl', 'llava']):
        capabilities.append('vision')
    if any(word in model_name.lower() for word in ['reasoning', 'phi4', 'deepseek']):
        capabilities.append('reasoning')
    if any(word in model_name.lower() for word in ['math', 'mathematical']):
        capabilities.append('math')

    return capabilities

def get_test_results():
    """Get test results from the LLM evaluator API"""
    try:
        response = requests.get("http://localhost:7500/api/results/runs", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def create_model_table():
    """Create comprehensive model comparison table"""
    print("🔍 Gathering model information...")

    # Get all models
    ollama_models = get_ollama_models()
    openrouter_models = get_openrouter_free_models()
    test_results = get_test_results()

    print(f"Found {len(ollama_models)} Ollama models")
    print(f"Found {len(openrouter_models)} OpenRouter free models")
    print(f"Found {len(test_results)} test results")

    # Combine all models
    all_models = ollama_models + openrouter_models

    # Create table data
    table_data = []
    for model in all_models:
        # Look for test results for this model
        reasoning_score = "N/A"
        coding_score = "N/A"
        text_score = "N/A"
        vision_score = "N/A"

        # Add model to table
        table_data.append([
            model['name'][:40] + ("..." if len(model['name']) > 40 else ""),
            model['provider'],
            model['size'],
            ", ".join(model['capabilities']),
            reasoning_score,
            coding_score,
            text_score,
            vision_score
        ])

    # Sort by provider and name
    table_data.sort(key=lambda x: (x[1], x[0]))

    headers = [
        "Model Name",
        "Provider",
        "Size",
        "Capabilities",
        "Reasoning",
        "Coding",
        "Text Gen",
        "Vision"
    ]

    print("\n" + "="*120)
    print("📊 COMPREHENSIVE MODEL COMPARISON TABLE")
    print("="*120)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Summary statistics
    total_models = len(all_models)
    ollama_count = len(ollama_models)
    openrouter_count = len(openrouter_models)

    print(f"\n📈 SUMMARY:")
    print(f"Total Models Available: {total_models}")
    print(f"  • Ollama (Local): {ollama_count}")
    print(f"  • OpenRouter (Free): {openrouter_count}")

    # Capability breakdown
    capability_counts = {}
    for model in all_models:
        for cap in model['capabilities']:
            capability_counts[cap] = capability_counts.get(cap, 0) + 1

    print(f"\n🎯 CAPABILITY BREAKDOWN:")
    for cap, count in sorted(capability_counts.items()):
        print(f"  • {cap.title()}: {count} models")

if __name__ == "__main__":
    try:
        create_model_table()
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)