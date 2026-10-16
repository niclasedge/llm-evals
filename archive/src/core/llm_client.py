"""
Unified LLM Client for LLM CLI Integration Layer

This module provides a unified interface that abstracts away the differences between
PydanticAI agents and LLM CLI, providing a consistent programmatic interface for
the evaluation system.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Core imports
from .llm_unified_config import get_unified_config, ModelConfig
from .monitoring import get_monitor, EvaluationMonitor

# Feature imports
from ..features.llm_evaluation.test_framework.llm_cli_client import LLMCLIClient
from ..features.llm_evaluation.llm_service import get_llm_agent, run_query, run_vision_query
from pydantic_ai import Agent


@dataclass
class LLMResponse:
    """Standardized response format for all LLM interactions"""
    content: str
    model: str
    provider: str
    success: bool
    duration: float
    timestamp: datetime
    conversation_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Message format for conversation history"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedLLMClient:
    """
    Unified LLM client that can use either PydanticAI or LLM CLI
    
    This class provides a consistent interface for interacting with LLMs
    regardless of the underlying provider implementation.
    """
    
    def __init__(self, provider: str, model: str, system_prompt: str = None):
        """
        Initialize the unified LLM client
        
        Args:
            provider: Provider name (llm_cli, ollama, openrouter)
            model: Model name or identifier
            system_prompt: System prompt for the model
        """
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.conversation_history: List[Message] = []
        self.conversation_id = f"conv_{int(time.time())}"
        
        # Initialize configuration and monitoring
        self.config = get_unified_config()
        self.monitor = get_monitor()
        
        # Initialize provider clients
        self.llm_cli_client = None
        self.pydantic_agent = None
        self.model_config = None
        
        # Resolve model configuration
        self._resolve_model_config()
        
        # Initialize appropriate client
        self._initialize_client()
    
    def _resolve_model_config(self):
        """Resolve model configuration using unified config"""
        self.model_config = self.config.resolve_model_name(self.model)
        if not self.model_config:
            self.monitor.log_warning(f"Model {self.model} not found in unified config", {
                'provider': self.provider,
                'model': self.model
            })
    
    def _initialize_client(self):
        """Initialize the appropriate client based on provider"""
        try:
            if self.provider == "llm_cli" or self._should_use_llm_cli():
                self._initialize_llm_cli()
            else:
                self._initialize_pydantic_agent()
        except Exception as e:
            self.monitor.log_error(f"Failed to initialize client for {self.provider}/{self.model}: {e}", {
                'provider': self.provider,
                'model': self.model,
                'error': str(e)
            })
            raise
    
    def _should_use_llm_cli(self) -> bool:
        """Determine if LLM CLI should be used for this model"""
        # Use LLM CLI if explicitly requested or if it's available and configured
        if self.provider == "llm_cli":
            return True
        
        # Check if LLM CLI is available and model is supported
        if self.llm_cli_client is None:
            try:
                self.llm_cli_client = LLMCLIClient()
                return self.llm_cli_client.is_available()
            except Exception:
                return False
        
        return self.llm_cli_client.is_available()
    
    def _initialize_llm_cli(self):
        """Initialize LLM CLI client"""
        self.llm_cli_client = LLMCLIClient()
        if not self.llm_cli_client.is_available():
            raise RuntimeError("LLM CLI is not available")
        
        self.monitor.log_info(f"Initialized LLM CLI client for model: {self.model}")
    
    def _initialize_pydantic_agent(self):
        """Initialize PydanticAI agent"""
        # Determine provider and model for PydanticAI
        if self.model_config:
            provider = self.model_config.provider
            model_id = self.model_config.model_id
        else:
            provider = self.provider
            model_id = self.model
        
        self.pydantic_agent = get_llm_agent(provider, model_id, self.system_prompt)
        if not self.pydantic_agent:
            raise RuntimeError(f"Failed to create PydanticAI agent for {provider}/{model_id}")
        
        self.monitor.log_info(f"Initialized PydanticAI agent for model: {self.model}")
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate response for a prompt
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with the generated content
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        # Add user message to conversation history
        self.conversation_history.append(Message(
            role="user",
            content=prompt,
            timestamp=timestamp
        ))
        
        try:
            if self.llm_cli_client and (self.provider == "llm_cli" or self._should_use_llm_cli()):
                response = await self._generate_llm_cli(prompt, **kwargs)
            else:
                response = await self._generate_pydantic(prompt, **kwargs)
            
            # Add assistant message to conversation history
            self.conversation_history.append(Message(
                role="assistant",
                content=response.content,
                timestamp=datetime.now()
            ))
            
            # Log successful operation
            self.monitor.log_info(f"Generated response for model {self.model}", {
                'provider': self.provider,
                'model': self.model,
                'duration': response.duration,
                'conversation_id': self.conversation_id
            })
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            error_response = LLMResponse(
                content="",
                model=self.model,
                provider=self.provider,
                success=False,
                duration=duration,
                timestamp=timestamp,
                conversation_id=self.conversation_id,
                error_message=str(e)
            )
            
            self.monitor.log_error(f"Failed to generate response for {self.model}: {e}", {
                'provider': self.provider,
                'model': self.model,
                'duration': duration,
                'conversation_id': self.conversation_id,
                'error': str(e)
            })
            
            return error_response
    
    async def _generate_llm_cli(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using LLM CLI"""
        start_time = time.time()
        
        # Resolve model name for LLM CLI
        model_name = self.model
        if self.model_config:
            model_name = self.config.get_llm_cli_format(self.model) or self.model
        
        # Extract parameters
        temperature = kwargs.get('temperature')
        max_tokens = kwargs.get('max_tokens')
        
        # Call LLM CLI
        response_data = await self.llm_cli_client.run_prompt(
            prompt=prompt,
            model=model_name,
            system_prompt=self.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        duration = time.time() - start_time
        
        if response_data and response_data.get('success'):
            return LLMResponse(
                content=response_data['response'],
                model=response_data.get('resolved_model', self.model),
                provider="llm_cli",
                success=True,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                metadata={
                    'command': response_data.get('command'),
                    'original_model': response_data.get('original_model'),
                    'llm_cli_timing': response_data.get('_timing', {})
                }
            )
        else:
            error_msg = response_data.get('error', 'Unknown LLM CLI error') if response_data else 'LLM CLI returned None'
            return LLMResponse(
                content="",
                model=self.model,
                provider="llm_cli",
                success=False,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                error_message=error_msg,
                metadata={'command': response_data.get('command') if response_data else None}
            )
    
    async def _generate_pydantic(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using PydanticAI"""
        start_time = time.time()
        
        if not self.pydantic_agent:
            raise RuntimeError("PydanticAI agent not initialized")
        
        # Run query
        response_content = await run_query(self.pydantic_agent, prompt)
        duration = time.time() - start_time
        
        if response_content is not None:
            return LLMResponse(
                content=str(response_content),
                model=self.model,
                provider=self.provider,
                success=True,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id
            )
        else:
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider,
                success=False,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                error_message="PydanticAI returned None"
            )
    
    async def chat(self, messages: List[Message]) -> LLMResponse:
        """
        Chat with conversation history
        
        Args:
            messages: List of messages in the conversation
            
        Returns:
            LLMResponse with the generated content
        """
        # For now, use the last message as the prompt
        # In a more sophisticated implementation, we'd format the entire conversation
        if not messages:
            raise ValueError("No messages provided")
        
        last_message = messages[-1]
        return await self.generate(last_message.content)
    
    async def vision_query(self, prompt: str, image_path: str, **kwargs) -> LLMResponse:
        """
        Generate response for a vision query
        
        Args:
            prompt: The input prompt
            image_path: Path to the image file
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with the generated content
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        # Add user message to conversation history
        self.conversation_history.append(Message(
            role="user",
            content=f"[Image: {image_path}] {prompt}",
            timestamp=timestamp,
            metadata={'image_path': image_path}
        ))
        
        try:
            if self.llm_cli_client and (self.provider == "llm_cli" or self._should_use_llm_cli()):
                response = await self._vision_query_llm_cli(prompt, image_path, **kwargs)
            else:
                response = await self._vision_query_pydantic(prompt, image_path, **kwargs)
            
            # Add assistant message to conversation history
            self.conversation_history.append(Message(
                role="assistant",
                content=response.content,
                timestamp=datetime.now()
            ))
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            error_response = LLMResponse(
                content="",
                model=self.model,
                provider=self.provider,
                success=False,
                duration=duration,
                timestamp=timestamp,
                conversation_id=self.conversation_id,
                error_message=str(e)
            )
            
            self.monitor.log_error(f"Failed to process vision query for {self.model}: {e}", {
                'provider': self.provider,
                'model': self.model,
                'duration': duration,
                'conversation_id': self.conversation_id,
                'image_path': image_path,
                'error': str(e)
            })
            
            return error_response
    
    async def _vision_query_llm_cli(self, prompt: str, image_path: str, **kwargs) -> LLMResponse:
        """Process vision query using LLM CLI"""
        start_time = time.time()
        
        # Resolve model name for LLM CLI
        model_name = self.model
        if self.model_config:
            model_name = self.config.get_llm_cli_format(self.model) or self.model
        
        # Call LLM CLI for image processing
        response_data = await self.llm_cli_client.extract_from_image(
            image_path=image_path,
            prompt=prompt,
            model=model_name
        )
        
        duration = time.time() - start_time
        
        if response_data and response_data.get('success'):
            return LLMResponse(
                content=response_data['response'],
                model=response_data.get('resolved_model', self.model),
                provider="llm_cli",
                success=True,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                metadata={
                    'command': response_data.get('command'),
                    'image_path': image_path,
                    'llm_cli_timing': response_data.get('_timing', {})
                }
            )
        else:
            error_msg = response_data.get('error', 'Unknown LLM CLI error') if response_data else 'LLM CLI returned None'
            return LLMResponse(
                content="",
                model=self.model,
                provider="llm_cli",
                success=False,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                error_message=error_msg,
                metadata={'command': response_data.get('command') if response_data else None}
            )
    
    async def _vision_query_pydantic(self, prompt: str, image_path: str, **kwargs) -> LLMResponse:
        """Process vision query using PydanticAI"""
        start_time = time.time()
        
        if not self.pydantic_agent:
            raise RuntimeError("PydanticAI agent not initialized")
        
        # Check if image path exists
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Run vision query
        response_content = await run_vision_query(self.pydantic_agent, prompt, image_path=image_path)
        duration = time.time() - start_time
        
        if response_content is not None:
            return LLMResponse(
                content=str(response_content),
                model=self.model,
                provider=self.provider,
                success=True,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                metadata={'image_path': image_path}
            )
        else:
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider,
                success=False,
                duration=duration,
                timestamp=datetime.now(),
                conversation_id=self.conversation_id,
                error_message="PydanticAI vision query returned None",
                metadata={'image_path': image_path}
            )
    
    def switch_model(self, model: str, provider: str = None):
        """
        Switch to a different model
        
        Args:
            model: New model name
            provider: New provider (optional)
        """
        if provider:
            self.provider = provider
        
        self.model = model
        self.model_config = None
        self.llm_cli_client = None
        self.pydantic_agent = None
        
        # Re-resolve model configuration and initialize client
        self._resolve_model_config()
        self._initialize_client()
        
        self.monitor.log_info(f"Switched to model: {model}", {
            'provider': self.provider,
            'model': model,
            'conversation_id': self.conversation_id
        })
    
    def get_conversation_history(self) -> List[Message]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        self.conversation_id = f"conv_{int(time.time())}"
        
        self.monitor.log_info(f"Cleared conversation history for {self.model}", {
            'provider': self.provider,
            'model': self.model,
            'new_conversation_id': self.conversation_id
        })
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        info = {
            'provider': self.provider,
            'model': self.model,
            'system_prompt': self.system_prompt,
            'conversation_id': self.conversation_id,
            'message_count': len(self.conversation_history)
        }
        
        if self.model_config:
            info.update({
                'model_config': {
                    'name': self.model_config.name,
                    'provider': self.model_config.provider,
                    'model_id': self.model_config.model_id,
                    'aliases': self.model_config.aliases,
                    'capabilities': self.model_config.capabilities,
                    'free': self.model_config.free,
                    'enabled': self.model_config.enabled
                }
            })
        
        return info
    
    def is_available(self) -> bool:
        """Check if the client is available and properly configured"""
        try:
            if self.provider == "llm_cli":
                return self.llm_cli_client and self.llm_cli_client.is_available()
            else:
                return self.pydantic_agent is not None
        except Exception:
            return False


class LLMClientFactory:
    """Factory for creating unified LLM clients"""
    
    @staticmethod
    def create_client(provider: str, model: str, system_prompt: str = None) -> UnifiedLLMClient:
        """
        Create a unified LLM client
        
        Args:
            provider: Provider name
            model: Model name
            system_prompt: System prompt
            
        Returns:
            UnifiedLLMClient instance
        """
        return UnifiedLLMClient(provider, model, system_prompt)
    
    @staticmethod
    def create_llm_cli_client(model: str, system_prompt: str = None) -> UnifiedLLMClient:
        """
        Create a client specifically for LLM CLI
        
        Args:
            model: Model name
            system_prompt: System prompt
            
        Returns:
            UnifiedLLMClient instance configured for LLM CLI
        """
        return UnifiedLLMClient("llm_cli", model, system_prompt)
    
    @staticmethod
    def get_available_models(provider: str = None) -> List[str]:
        """
        Get available models from configuration
        
        Args:
            provider: Filter by provider
            
        Returns:
            List of available model names
        """
        config = get_unified_config()
        models = config.list_models(provider=provider, enabled_only=True)
        return [model.name for model in models]


# Backward compatibility wrapper
class LLMAgent:
    """
    Backward compatibility wrapper for existing agent interface
    
    This class maintains compatibility with the existing agent interface
    while using the new unified client internally.
    """
    
    def __init__(self, client: UnifiedLLMClient):
        self.client = client
    
    async def run(self, prompt: str) -> str:
        """Run a query and return the response content"""
        response = await self.client.generate(prompt)
        return response.content if response.success else ""
    
    async def run_vision(self, prompt: str, image_path: str) -> str:
        """Run a vision query and return the response content"""
        response = await self.client.vision_query(prompt, image_path)
        return response.content if response.success else ""


# Convenience functions for backward compatibility
def get_unified_llm_agent(model_provider: str, model_identifier: str, system_prompt: str = None) -> LLMAgent:
    """
    Create a unified LLM agent with backward compatibility
    
    Args:
        model_provider: Provider name
        model_identifier: Model name or identifier
        system_prompt: System prompt
        
    Returns:
        LLMAgent instance
    """
    client = UnifiedLLMClient(model_provider, model_identifier, system_prompt)
    return LLMAgent(client)


def get_evaluation_monitor() -> EvaluationMonitor:
    """Get the evaluation monitor instance"""
    return get_monitor()