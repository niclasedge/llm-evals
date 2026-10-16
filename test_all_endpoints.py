#!/usr/bin/env python3
"""
Comprehensive endpoint testing script for LLM Evaluator API.
Tests all available endpoints and validates responses.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback


class EndpointTester:
    def __init__(self, base_url: str = "http://localhost:7500"):
        self.base_url = base_url
        self.results = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_result(self, endpoint: str, method: str, status: int,
                  response_type: str, error: str = None, data: Any = None):
        """Log test result."""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "response_type": response_type,
            "timestamp": datetime.now().isoformat(),
            "success": 200 <= status < 400,
            "error": error,
            "data_preview": str(data)[:200] if data else None
        }
        self.results.append(result)

    async def test_endpoint(self, method: str, endpoint: str,
                           data: Dict = None, expected_status: int = 200,
                           description: str = "", form_data: bool = False):
        """Test a single endpoint."""
        full_url = f"{self.base_url}{endpoint}"
        print(f"  Testing {method.upper()} {endpoint} - {description}")

        try:
            if method.upper() == "GET":
                async with self.session.get(full_url) as response:
                    content = await response.text()
                    content_type = response.headers.get('content-type', '')

                    self.log_result(
                        endpoint, method, response.status,
                        content_type, data=content[:100] + "..." if len(content) > 100 else content
                    )

                    if response.status != expected_status:
                        print(f"    ❌ Status {response.status} (expected {expected_status})")
                        return False
                    else:
                        print(f"    ✅ Status {response.status}")
                        return True

            elif method.upper() == "POST":
                if form_data and data:
                    # Send as form data
                    async with self.session.post(full_url, data=data) as response:
                        content = await response.text()
                        content_type = response.headers.get('content-type', '')
                elif data:
                    # Send as JSON
                    async with self.session.post(full_url, json=data) as response:
                        content = await response.text()
                        content_type = response.headers.get('content-type', '')
                else:
                    # No data
                    async with self.session.post(full_url) as response:
                        content = await response.text()
                        content_type = response.headers.get('content-type', '')

                self.log_result(
                    endpoint, method, response.status,
                    content_type, data=content[:100] + "..." if len(content) > 100 else content
                )

                if response.status != expected_status:
                    print(f"    ❌ Status {response.status} (expected {expected_status})")
                    return False
                else:
                    print(f"    ✅ Status {response.status}")
                    return True

        except Exception as e:
            error_msg = str(e)
            self.log_result(endpoint, method, 0, "error", error_msg)
            print(f"    ❌ Error: {error_msg}")
            return False

    async def test_all_endpoints(self):
        """Test all available endpoints."""
        print("🧪 COMPREHENSIVE ENDPOINT TESTING")
        print("=" * 50)

        # Test basic app endpoints
        print("\n📋 Basic Application Endpoints:")
        await self.test_endpoint("GET", "/", description="Root redirect")
        await self.test_endpoint("GET", "/health", description="Health check")

        # Test dashboard endpoints
        print("\n📊 Dashboard Endpoints:")
        await self.test_endpoint("GET", "/dashboard", description="Main dashboard")
        await self.test_endpoint("GET", "/providers", description="Providers page")
        await self.test_endpoint("GET", "/tests", description="Tests page")
        await self.test_endpoint("GET", "/results", description="Results page")

        # Test dashboard partials (HTMX endpoints)
        print("\n🔄 Dashboard Partials (HTMX):")
        await self.test_endpoint("GET", "/partials/provider-health", description="Provider health partial")
        await self.test_endpoint("GET", "/partials/recent-runs", description="Recent runs partial")
        await self.test_endpoint("GET", "/partials/models-table", description="Models table partial")
        await self.test_endpoint("GET", "/partials/logs", description="Live logs partial")
        await self.test_endpoint("GET", "/partials/model-checkboxes", description="Model checkboxes partial")

        # Test provider API endpoints
        print("\n🏗️ Provider API Endpoints:")
        await self.test_endpoint("GET", "/api/providers/", description="List all providers")
        await self.test_endpoint("GET", "/api/providers/health", description="Provider health check")
        await self.test_endpoint("GET", "/api/providers/ollama/models", description="Ollama models", expected_status=200)
        await self.test_endpoint("GET", "/api/providers/openrouter/models", description="OpenRouter models", expected_status=200)
        await self.test_endpoint("POST", "/api/providers/sync", description="Sync providers")

        # Test tests API endpoints
        print("\n🧪 Tests API Endpoints:")
        await self.test_endpoint("GET", "/api/tests/categories", description="List test categories")
        await self.test_endpoint("GET", "/api/tests/configs", description="List test configurations")
        await self.test_endpoint("GET", "/api/tests/configs/1", description="Get specific test config")
        await self.test_endpoint("GET", "/api/tests/categories/1/configs", description="Get category configs")

        # Test results API endpoints
        print("\n📈 Results API Endpoints:")
        await self.test_endpoint("GET", "/api/results/runs", description="List test runs")
        await self.test_endpoint("GET", "/api/results/analytics/summary", description="Analytics summary")

        # Test with existing run IDs if available
        await self.test_endpoint("GET", "/api/results/runs/1", description="Get test run", expected_status=404)  # May not exist
        await self.test_endpoint("GET", "/api/results/runs/1/results", description="Get run results", expected_status=404)

        # Test POST endpoints with sample data
        print("\n📝 POST Endpoints with Sample Data:")

        # Test start-test partial (form data)
        test_form_data = {
            "run_name": "Endpoint Test Run",
            "run_description": "Test run from endpoint testing script"
        }
        await self.test_endpoint("POST", "/partials/start-test", data=test_form_data,
                                form_data=True, description="Start test partial (form data)")

        # Test run endpoint with minimal valid data - may fail if no valid models/configs
        test_run_data = {
            "test_config_ids": [1],
            "model_ids": [1],
            "run_name": "API Endpoint Test"
        }
        await self.test_endpoint("POST", "/api/tests/run", data=test_run_data,
                                expected_status=200, description="Start test run (may fail if no data)")

        # Test static file access
        print("\n📁 Static File Endpoints:")
        await self.test_endpoint("GET", "/static/", description="Static files directory", expected_status=404)  # Expected 404

        print(f"\n✅ TESTING COMPLETE")
        await self.generate_report()

    async def generate_report(self):
        """Generate a comprehensive test report."""
        print("\n📊 TEST REPORT")
        print("=" * 50)

        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests

        print(f"Total Endpoints Tested: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")

        # Group results by status code
        status_counts = {}
        for result in self.results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"\n📋 Status Code Distribution:")
        for status, count in sorted(status_counts.items()):
            status_name = {
                200: "OK",
                302: "Redirect",
                404: "Not Found",
                422: "Unprocessable Entity",
                500: "Internal Server Error",
                0: "Connection Error"
            }.get(status, "Unknown")
            print(f"  {status} ({status_name}): {count} endpoints")

        # Show failed endpoints
        failed_results = [r for r in self.results if not r['success']]
        if failed_results:
            print(f"\n❌ Failed Endpoints:")
            for result in failed_results:
                print(f"  {result['method'].upper()} {result['endpoint']} - Status {result['status']}")
                if result['error']:
                    print(f"    Error: {result['error']}")

        # Show successful critical endpoints
        critical_endpoints = [
            "/health", "/dashboard", "/partials/models-table",
            "/partials/logs", "/api/providers/", "/api/tests/categories"
        ]

        critical_results = [r for r in self.results if r['endpoint'] in critical_endpoints]
        critical_success = sum(1 for r in critical_results if r['success'])

        print(f"\n🎯 Critical Endpoints Status: {critical_success}/{len(critical_results)} working")

        # Save detailed report to file
        report_file = f"endpoint_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "successful": successful_tests,
                    "failed": failed_tests,
                    "success_rate": (successful_tests/total_tests)*100,
                    "test_timestamp": datetime.now().isoformat()
                },
                "results": self.results
            }, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")


async def main():
    """Main function to run endpoint tests."""
    print("🚀 LLM Evaluator - Comprehensive Endpoint Testing")
    print("Starting endpoint tests...")

    try:
        async with EndpointTester() as tester:
            await tester.test_all_endpoints()
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check if server is running
    import requests
    try:
        response = requests.get("http://localhost:7500/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running - proceeding with tests")
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
    except requests.RequestException:
        print("❌ Server is not running at http://localhost:7500")
        print("   Start the server with: make start")
        sys.exit(1)

    # Run the tests
    asyncio.run(main())