"""
Ollama API client for LLM evaluation testing.
Provides direct API access to Ollama models for standardized testing.
"""

import asyncio
import json
import time
from typing import List, Dict, Optional, Any
import aiohttp
import logging
try:
    from ..config import (
        OLLAMA_BASE_URL, ENABLE_GO_SERVICE, GO_SERVICE_URL, GO_SERVICE_FALLBACK,
        GO_SERVICE_TIMEOUT, GO_SERVICE_RETRY_ATTEMPTS, GO_SERVICE_CIRCUIT_BREAKER_THRESHOLD,
        GO_SERVICE_CIRCUIT_BREAKER_TIMEOUT, OLLAMA_VIA_GO_SERVICE
    )
    from ..go_integration import (
        GoServiceClient, GoServiceDiscovery, RequestAdapter, ResponseMapper, FallbackManager
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from src.features.llm_evaluation.config import (
        OLLAMA_BASE_URL, ENABLE_GO_SERVICE, GO_SERVICE_URL, GO_SERVICE_FALLBACK,
        GO_SERVICE_TIMEOUT, GO_SERVICE_RETRY_ATTEMPTS, GO_SERVICE_CIRCUIT_BREAKER_THRESHOLD,
        GO_SERVICE_CIRCUIT_BREAKER_TIMEOUT, OLLAMA_VIA_GO_SERVICE
    )
    from src.features.llm_evaluation.go_integration import (
        GoServiceClient, GoServiceDiscovery, RequestAdapter, ResponseMapper, FallbackManager
    )

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API endpoints with Go service integration."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, use_go_service: Optional[bool] = None):
        self.base_url = base_url.rstrip('/')
        self.session = None
        
        # Go service integration configuration
        self.use_go_service = use_go_service if use_go_service is not None else ENABLE_GO_SERVICE
        self.go_service_url = GO_SERVICE_URL
        self.fallback_enabled = GO_SERVICE_FALLBACK
        
        # Initialize Go service components if enabled
        if self.use_go_service:
            self.go_client = None  # Will be initialized in __aenter__
            self.service_discovery = GoServiceDiscovery(self.go_service_url)
            self.request_adapter = RequestAdapter()
            self.response_mapper = ResponseMapper()
            self.fallback_manager = FallbackManager(
                max_retries=GO_SERVICE_RETRY_ATTEMPTS,
                circuit_breaker_threshold=GO_SERVICE_CIRCUIT_BREAKER_THRESHOLD,
                circuit_breaker_timeout=GO_SERVICE_CIRCUIT_BREAKER_TIMEOUT
            )
            self.fallback_manager.configure_fallback(
                enabled=self.fallback_enabled,
                prefer_go_service=True
            )
        else:
            self.go_client = None
            self.service_discovery = None
            self.request_adapter = None
            self.response_mapper = None
            self.fallback_manager = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        
        # Initialize Go service client if enabled
        if self.use_go_service:
            self.go_client = GoServiceClient(self.go_service_url)
            await self.go_client.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        
        # Close Go service client if initialized
        if self.go_client:
            await self.go_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Ensure Go service client is initialized if enabled
        if self.use_go_service and not self.go_client:
            self.go_client = GoServiceClient(self.go_service_url)
            await self.go_client.__aenter__()
    
    async def health_check(self) -> bool:
        """Check if Ollama server is running and accessible."""
        await self._ensure_session()
        
        if self.use_go_service and self.fallback_manager:
            # Check both Go service and direct Ollama health
            async def check_go_service():
                return await self.go_client.health_check()
            
            async def check_direct_ollama():
                try:
                    async with self.session.get(f"{self.base_url}/api/tags") as response:
                        return response.status == 200
                except Exception:
                    return False
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    check_go_service, check_direct_ollama
                )
            except Exception:
                return False
        else:
            # Direct Ollama health check
            try:
                async with self.session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
            except Exception:
                return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from Ollama API."""
        await self._ensure_session()
        
        if self.use_go_service and self.fallback_manager:
            # Use Go service with fallback to direct Ollama
            async def list_via_go_service():
                models = await self.go_client.list_models()
                return self.response_mapper.map_models_response({"models": models})
            
            async def list_via_direct_ollama():
                try:
                    async with self.session.get(f"{self.base_url}/api/tags") as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get('models', [])
                        else:
                            logger.error(f"Error listing models: HTTP {response.status}")
                            return []
                except Exception as e:
                    logger.error(f"Error listing models: {e}")
                    return []
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    list_via_go_service, list_via_direct_ollama
                )
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                return []
        else:
            # Direct Ollama only
            try:
                async with self.session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('models', [])
                    else:
                        logger.error(f"Error listing models: HTTP {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                return []
    
    async def generate(self, model: str, prompt: str, system_prompt: Optional[str] = None, 
                      stream: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate response using Ollama API."""
        await self._ensure_session()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if self.use_go_service and self.fallback_manager:
            # Use Go service with fallback to direct Ollama
            async def generate_via_go_service():
                adapted_payload = self.request_adapter.adapt_generate_request(payload)
                result = await self.go_client.generate(**adapted_payload)
                if result:
                    return self.response_mapper.map_generate_response(result)
                return result
            
            async def generate_via_direct_ollama():
                try:
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
                                'via_go_service': False
                            }
                            
                            return result
                        else:
                            logger.error(f"Error generating response: HTTP {response.status}")
                            error_text = await response.text()
                            logger.error(f"Error details: {error_text}")
                            return None
                except Exception as e:
                    logger.error(f"Error generating response: {e}")
                    return None
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    generate_via_go_service, generate_via_direct_ollama
                )
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                return None
        else:
            # Direct Ollama only
            try:
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
                            'via_go_service': False
                        }
                        
                        return result
                    else:
                        logger.error(f"Error generating response: HTTP {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                return None
    
    async def chat(self, model: str, messages: List[Dict[str, str]], 
                   stream: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
        """Chat interaction using Ollama API."""
        await self._ensure_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if self.use_go_service and self.fallback_manager:
            # Use Go service with fallback to direct Ollama
            async def chat_via_go_service():
                adapted_payload = self.request_adapter.adapt_chat_request(payload)
                result = await self.go_client.chat(**adapted_payload)
                if result:
                    return self.response_mapper.map_chat_response(result)
                return result
            
            async def chat_via_direct_ollama():
                try:
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
                                'via_go_service': False
                            }
                            
                            return result
                        else:
                            logger.error(f"Error in chat: HTTP {response.status}")
                            error_text = await response.text()
                            logger.error(f"Error details: {error_text}")
                            return None
                except Exception as e:
                    logger.error(f"Error in chat: {e}")
                    return None
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    chat_via_go_service, chat_via_direct_ollama
                )
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                return None
        else:
            # Direct Ollama only
            try:
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
                            'via_go_service': False
                        }
                        
                        return result
                    else:
                        logger.error(f"Error in chat: HTTP {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                return None
    
    async def pull_model(self, model: str) -> bool:
        """Pull/download a model if not already available."""
        await self._ensure_session()
        
        if self.use_go_service and self.fallback_manager:
            # Use Go service with fallback to direct Ollama
            async def pull_via_go_service():
                return await self.go_client.pull_model(model)
            
            async def pull_via_direct_ollama():
                try:
                    payload = {"name": model}
                    
                    async with self.session.post(f"{self.base_url}/api/pull", 
                                               json=payload) as response:
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
                            logger.error(f"Error pulling model: HTTP {response.status}")
                            return False
                except Exception as e:
                    logger.error(f"Error pulling model: {e}")
                    return False
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    pull_via_go_service, pull_via_direct_ollama
                )
            except Exception as e:
                logger.error(f"Error pulling model: {e}")
                return False
        else:
            # Direct Ollama only
            try:
                payload = {"name": model}
                
                async with self.session.post(f"{self.base_url}/api/pull", 
                                           json=payload) as response:
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
                        logger.error(f"Error pulling model: HTTP {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Error pulling model: {e}")
                return False
    
    async def model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        await self._ensure_session()
        
        if self.use_go_service and self.fallback_manager:
            # Use Go service with fallback to direct Ollama
            async def info_via_go_service():
                result = await self.go_client.model_info(model)
                if result:
                    return self.response_mapper.map_show_response(result)
                return result
            
            async def info_via_direct_ollama():
                try:
                    payload = {"name": model}
                    
                    async with self.session.post(f"{self.base_url}/api/show", 
                                               json=payload) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"Error getting model info: HTTP {response.status}")
                            return None
                except Exception as e:
                    logger.error(f"Error getting model info: {e}")
                    return None
            
            try:
                return await self.fallback_manager.execute_with_fallback(
                    info_via_go_service, info_via_direct_ollama
                )
            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                return None
        else:
            # Direct Ollama only
            try:
                payload = {"name": model}
                
                async with self.session.post(f"{self.base_url}/api/show", 
                                           json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Error getting model info: HTTP {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                return None
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None
        
        # Close Go service client if initialized
        if self.go_client:
            await self.go_client.close()
            self.go_client = None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for Go service integration."""
        if self.fallback_manager:
            return self.fallback_manager.get_performance_stats()
        return {}
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the current configuration."""
        info = {
            "use_go_service": self.use_go_service,
            "go_service_url": self.go_service_url,
            "fallback_enabled": self.fallback_enabled,
            "ollama_base_url": self.base_url,
        }
        
        if self.fallback_manager:
            info["performance_stats"] = self.fallback_manager.get_performance_stats()
        
        return info


# Example usage and test function
async def test_ollama_client():
    """Test the Ollama client functionality."""
    async with OllamaClient() as client:
        print("Testing Ollama client...")
        
        # Health check
        is_healthy = await client.health_check()
        print(f"Ollama health check: {'✓' if is_healthy else '✗'}")
        
        if not is_healthy:
            print("Ollama server is not accessible. Please ensure Ollama is running.")
            return
        
        # List models
        models = await client.list_models()
        print(f"Available models: {[m['name'] for m in models]}")
        
        if not models:
            print("No models available. Please pull a model first (e.g., 'ollama pull llama3.2')")
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
        
        # Chat test
        chat_response = await client.chat(
            model=test_model,
            messages=[
                {"role": "user", "content": "Hello! How are you?"}
            ]
        )
        
        if chat_response:
            print(f"Chat response: {chat_response.get('message', {}).get('content', 'No content')}")
            print(f"Chat response time: {chat_response.get('_timing', {}).get('response_time', 0):.2f}s")


if __name__ == "__main__":
    asyncio.run(test_ollama_client())