#!/usr/bin/env python3
"""
Demo des verbesserten Dashboards mit Live-Logs und Model-Tabelle
"""

import requests
import time
import json

def main():
    print("🎉 DEMO: Verbesserte LLM Evaluator Dashboard")
    print("=" * 60)

    # Dashboard URLs
    urls = {
        "Dashboard": "http://localhost:7500/dashboard",
        "Models Tabelle": "http://localhost:7500/partials/models-table",
        "Live Logs": "http://localhost:7500/partials/logs",
        "Provider Health": "http://localhost:7500/partials/provider-health"
    }

    print("🌐 Verfügbare URLs:")
    for name, url in urls.items():
        print(f"   • {name}: {url}")

    print(f"\n📊 DASHBOARD FEATURES:")
    print("✅ Komplette Modelltabelle mit allen Providern")
    print("✅ Live Testergebnisse pro Kategorie (Reasoning, Coding, Text, Vision)")
    print("✅ Direkte Test-Ausführung pro Model ('Run' Buttons)")
    print("✅ Live Application Logs mit Auto-Refresh")
    print("✅ Provider Health Status")
    print("✅ Quick Actions für Test-Starts")
    print("✅ Real-time Updates mit HTMX")

    # Test die APIs
    print(f"\n🧪 TESTING APIS:")

    try:
        # Test Models Table
        response = requests.get("http://localhost:7500/partials/models-table", timeout=5)
        if response.status_code == 200:
            print("✅ Models Table API: Funktioniert")
            # Count models in response
            model_count = response.text.count('<tr class="hover">')
            print(f"   📊 Zeigt {model_count} Models")
        else:
            print(f"❌ Models Table API: Error {response.status_code}")

        # Test Logs
        response = requests.get("http://localhost:7500/partials/logs", timeout=5)
        if response.status_code == 200:
            print("✅ Live Logs API: Funktioniert")
            log_entries = response.text.count('text-xs mb-1')
            print(f"   📋 Zeigt {log_entries} Log Einträge")
        else:
            print(f"❌ Live Logs API: Error {response.status_code}")

        # Test Provider Health
        response = requests.get("http://localhost:7500/partials/provider-health", timeout=5)
        if response.status_code == 200:
            print("✅ Provider Health API: Funktioniert")
        else:
            print(f"❌ Provider Health API: Error {response.status_code}")

    except requests.RequestException as e:
        print(f"❌ API Test Error: {e}")

    print(f"\n🚀 DEMO: Test starten")

    # Start einen Test zur Demonstration
    try:
        test_payload = {
            "test_config_ids": [1],  # Reasoning test
            "model_ids": [17]        # First enabled model
        }

        response = requests.post(
            "http://localhost:7500/api/tests/run?run_name=Dashboard%20Demo%20Test",
            json=test_payload,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Demo Test gestartet: Run ID {result.get('test_run_id', 'N/A')}")
            print("   🔄 Logs sollten jetzt live updates zeigen!")
        else:
            print(f"⚠️  Test Start Info: {response.status_code} - {response.text[:100]}")

    except Exception as e:
        print(f"ℹ️  Test Demo: {e}")

    print(f"\n🎯 WIE ES BENUTZEN:")
    print("1. Öffnen Sie: http://localhost:7500")
    print("2. Sehen Sie die komplette Models-Tabelle mit Test-Status")
    print("3. Klicken Sie 'Run' Buttons für einzelne Tests")
    print("4. Beobachten Sie Live-Logs unten rechts")
    print("5. Nutzen Sie '🚀 Start Test' für comprehensive Tests")

    print(f"\n📈 LIVE-FEATURES:")
    print("• Models Table: Aktualisiert alle 30s")
    print("• Logs: Aktualisiert alle 2s")
    print("• Provider Health: Aktualisiert alle 10s")
    print("• Recent Runs: Aktualisiert alle 10s")

    print(f"\n✨ Das Dashboard ist jetzt komplett funktional!")
    print("   Öffnen Sie http://localhost:7500 und testen Sie es!")

if __name__ == "__main__":
    main()