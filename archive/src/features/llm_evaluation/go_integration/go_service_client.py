"""
Go service client for LLM evaluation testing.
Provides API client for the Go service proxy to Ollama.
"""

import asyncio
import json
import time
from typing import List, Dict, Optional, Any
import aiohttp
import logging

logger = logging.getLogger(__name__)


class GoServiceClient:
    """Client for interacting with Go service API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def health_check(self) -> bool:
        """Check if Go service is running and accessible."""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('status') == 'healthy'
                return False
        except Exception as e:
            logger.debug(f"Go service health check failed: {e}")
            return False
    
    async def get_service_info(self) -> Optional[Dict[str, Any]]:
        """Get Go service version and capabilities."""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/api/status") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.debug(f"Failed to get Go service info: {e}")
            return None
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get list of available models via Go service."""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/api/models") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('models', [])
                else:
                    logger.error(f"Error listing models via Go service: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error listing models via Go service: {e}")
            return []
    
    async def generate(self, model: str, prompt: str, system_prompt: Optional[str] = None, 
                      stream: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate response using Go service proxy to Ollama."""
        try:
            await self._ensure_session()
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                **kwargs
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            start_time = time.time()
            async with self.session.post(f"{self.base_url}/api/generate", 
                                       json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    end_time = time.time()
                    
                    # Add timing information
                    result['_timing'] = {
                        'response_time': end_time - start_time,
                        'timestamp': start_time,
                        'via_go_service': True
                    }
                    
                    return result
                else:
                    logger.error(f"Error generating response via Go service: HTTP {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error details: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Error generating response via Go service: {e}")
            return None
    
    async def chat(self, model: str, messages: List[Dict[str, str]], 
                   stream: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Chat interaction using Go service proxy to Ollama."""
        try:
            await self._ensure_session()
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                **kwargs
            }
            
            start_time = time.time()
            async with self.session.post(f"{self.base_url}/api/chat", 
                                       json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    end_time = time.time()
                    
                    # Add timing information
                    result['_timing'] = {
                        'response_time': end_time - start_time,
                        'timestamp': start_time,
                        'via_go_service': True
                    }
                    
                    return result
                else:
                    logger.error(f"Error in chat via Go service: HTTP {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error details: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Error in chat via Go service: {e}")
            return None
    
    async def pull_model(self, model: str) -> bool:
        """Pull/download a model via Go service."""
        try:
            await self._ensure_session()
            
            payload = {"name": model}
            
            # Use longer timeout for model pulling
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minutes
            async with self.session.post(f"{self.base_url}/api/pull", 
                                       json=payload, timeout=timeout) as response:
                if response.status == 200:
                    # For streaming responses, we need to read the stream
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if data.get('status') == 'success':
                                    return True
                            except json.JSONDecodeError:
                                continue
                    return True
                else:
                    logger.error(f"Error pulling model via Go service: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error pulling model via Go service: {e}")
            return False
    
    async def model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model via Go service."""
        try:
            await self._ensure_session()
            
            payload = {"name": model}
            
            async with self.session.post(f"{self.base_url}/api/show", 
                                       json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error getting model info via Go service: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting model info via Go service: {e}")
            return None
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None


# Test function for Go service client
async def test_go_service_client():
    """Test the Go service client functionality."""
    async with GoServiceClient() as client:
        print("Testing Go service client...")
        
        # Health check
        is_healthy = await client.health_check()
        print(f"Go service health check: {'✓' if is_healthy else '✗'}")
        
        if not is_healthy:
            print("Go service is not accessible. Please ensure the Go service is running.")
            return
        
        # Get service info
        service_info = await client.get_service_info()
        if service_info:
            print(f"Go service info: {service_info}")
        
        # List models
        models = await client.list_models()
        print(f"Available models via Go service: {[m['name'] for m in models]}")
        
        if not models:
            print("No models available via Go service.")
            return
        
        # Test with first available model
        test_model = models[0]['name']
        print(f"Testing with model: {test_model}")
        
        # Generate test
        response = await client.generate(
            model=test_model,
            prompt="What is the capital of France?",
            system_prompt="You are a helpful assistant."
        )
        
        if response:
            print(f"Generate response: {response.get('response', 'No response')}")
            print(f"Response time: {response.get('_timing', {}).get('response_time', 0):.2f}s")
            print(f"Via Go service: {response.get('_timing', {}).get('via_go_service', False)}")


if __name__ == "__main__":
    asyncio.run(test_go_service_client())