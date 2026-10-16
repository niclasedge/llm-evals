"""
Service discovery for Go service integration.
Handles health checking and service availability detection.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)


class GoServiceDiscovery:
    """Service discovery and health checking for Go service."""
    
    def __init__(self, service_url: str = "http://localhost:8080", 
                 health_check_interval: int = 30):
        self.service_url = service_url.rstrip('/')
        self.health_check_interval = health_check_interval
        self.last_health_check = 0
        self.last_health_status = False
        self.service_info_cache = None
        self.cache_expiry = 60  # Cache service info for 1 minute
        self.last_info_check = 0
        self.timeout = aiohttp.ClientTimeout(total=5)
    
    async def is_service_available(self, force_check: bool = False) -> bool:
        """
        Check if Go service is running and healthy.
        
        Args:
            force_check: Skip cache and force fresh health check
            
        Returns:
            True if service is available and healthy
        """
        current_time = time.time()
        
        # Use cached result if recent and not forcing check
        if (not force_check and 
            current_time - self.last_health_check < self.health_check_interval):
            return self.last_health_status
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.service_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.last_health_status = data.get('status') == 'healthy'
                    else:
                        self.last_health_status = False
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            self.last_health_status = False
        
        self.last_health_check = current_time
        return self.last_health_status
    
    async def get_service_info(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get Go service version and capabilities.
        
        Args:
            force_refresh: Skip cache and force fresh info retrieval
            
        Returns:
            Service information dict or None if unavailable
        """
        current_time = time.time()
        
        # Use cached result if recent and not forcing refresh
        if (not force_refresh and 
            self.service_info_cache and 
            current_time - self.last_info_check < self.cache_expiry):
            return self.service_info_cache
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.service_url}/api/status") as response:
                    if response.status == 200:
                        self.service_info_cache = await response.json()
                        self.last_info_check = current_time
                        return self.service_info_cache
                    else:
                        logger.debug(f"Failed to get service info: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.debug(f"Failed to get service info: {e}")
            return None
    
    async def wait_for_service(self, timeout: int = 60, check_interval: int = 2) -> bool:
        """
        Wait for Go service to become available.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            True if service becomes available within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.is_service_available(force_check=True):
                return True
            
            logger.debug(f"Go service not available, waiting {check_interval}s...")
            await asyncio.sleep(check_interval)
        
        return False
    
    async def get_service_capabilities(self) -> Dict[str, Any]:
        """
        Get service capabilities and supported features.
        
        Returns:
            Dictionary with capability information
        """
        service_info = await self.get_service_info()
        if not service_info:
            return {}
        
        capabilities = {
            'available': await self.is_service_available(),
            'version': service_info.get('version', 'unknown'),
            'features': service_info.get('features', []),
            'ollama_connection': service_info.get('ollama_connected', False),
            'supported_endpoints': service_info.get('endpoints', []),
            'performance_metrics': service_info.get('metrics', {}),
            'last_updated': service_info.get('timestamp', 0)
        }
        
        return capabilities
    
    async def test_service_endpoint(self, endpoint: str) -> bool:
        """
        Test if a specific service endpoint is available.
        
        Args:
            endpoint: Endpoint path to test (e.g., '/api/generate')
            
        Returns:
            True if endpoint is available
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Use HEAD request to test endpoint availability
                async with session.head(f"{self.service_url}{endpoint}") as response:
                    # Accept any response that's not a connection error
                    return response.status < 500
        except Exception as e:
            logger.debug(f"Endpoint test failed for {endpoint}: {e}")
            return False
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get service performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.service_url}/metrics") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.debug(f"Failed to get metrics: HTTP {response.status}")
                        return {}
        except Exception as e:
            logger.debug(f"Failed to get metrics: {e}")
            return {}
    
    def reset_cache(self):
        """Reset all cached information."""
        self.last_health_check = 0
        self.last_health_status = False
        self.service_info_cache = None
        self.last_info_check = 0


# Test function for service discovery
async def test_service_discovery():
    """Test the service discovery functionality."""
    discovery = GoServiceDiscovery()
    
    print("Testing Go service discovery...")
    
    # Test health check
    is_available = await discovery.is_service_available()
    print(f"Service available: {'✓' if is_available else '✗'}")
    
    if not is_available:
        print("Testing wait for service (5 second timeout)...")
        available = await discovery.wait_for_service(timeout=5)
        print(f"Service became available: {'✓' if available else '✗'}")
    
    # Test service info
    service_info = await discovery.get_service_info()
    if service_info:
        print(f"Service info: {service_info}")
    
    # Test capabilities
    capabilities = await discovery.get_service_capabilities()
    print(f"Service capabilities: {capabilities}")
    
    # Test endpoint availability
    endpoints = ['/api/generate', '/api/chat', '/api/models', '/health']
    for endpoint in endpoints:
        available = await discovery.test_service_endpoint(endpoint)
        print(f"Endpoint {endpoint}: {'✓' if available else '✗'}")
    
    # Test metrics
    metrics = await discovery.get_service_metrics()
    if metrics:
        print(f"Service metrics: {metrics}")


if __name__ == "__main__":
    asyncio.run(test_service_discovery())