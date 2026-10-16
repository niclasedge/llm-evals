"""LLM provider abstraction layer."""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass
import httpx
import structlog
from openai import AsyncOpenAI
from app.core.config import settings


logger = structlog.get_logger()


@dataclass
class LLMMessage:
    """LLM message."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProviderError(Exception):
    """LLM provider error."""
    pass


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key

    @abstractmethod
    async def generate_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider (works for OpenRouter, Ollama with OpenAI compatibility)."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        super().__init__(name, base_url, api_key)
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "dummy-key"
        )

    async def generate_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI-compatible API."""
        import time
        start_time = time.time()

        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                **kwargs
            )

            response_time = time.time() - start_time

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage=response.usage.model_dump() if response.usage else None,
                response_time=response_time,
                metadata={
                    "provider": self.name,
                    "finish_reason": response.choices[0].finish_reason
                }
            )

        except Exception as e:
            logger.error("LLM generation failed", provider=self.name, model=model, error=str(e))
            raise LLMProviderError(f"Generation failed: {str(e)}")

    async def stream_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a response using OpenAI-compatible API."""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            stream = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("LLM streaming failed", provider=self.name, model=model, error=str(e))
            raise LLMProviderError(f"Streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check provider health."""
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        try:
            models = await self.client.models.list()
            return [model.model_dump() for model in models.data]
        except Exception as e:
            logger.error("Failed to list models", provider=self.name, error=str(e))
            return []


class OllamaProvider(LLMProvider):
    """Ollama provider with direct API access."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__("ollama", base_url)

    async def generate_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Ollama API."""
        import time
        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                # Convert messages to Ollama format
                prompt = self._messages_to_prompt(messages)

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        **kwargs
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()

                response_time = time.time() - start_time

                return LLMResponse(
                    content=data.get("response", ""),
                    model=model,
                    response_time=response_time,
                    metadata={
                        "provider": "ollama",
                        "done": data.get("done", False)
                    }
                )

        except Exception as e:
            logger.error("Ollama generation failed", model=model, error=str(e))
            raise LLMProviderError(f"Ollama generation failed: {str(e)}")

    async def stream_response(
        self,
        messages: List[LLMMessage],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Ollama API."""
        try:
            async with httpx.AsyncClient() as client:
                prompt = self._messages_to_prompt(messages)

                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True,
                        **kwargs
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done"):
                                break

        except Exception as e:
            logger.error("Ollama streaming failed", model=model, error=str(e))
            raise LLMProviderError(f"Ollama streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check Ollama health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List Ollama models."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []

    def _messages_to_prompt(self, messages: List[LLMMessage]) -> str:
        """Convert messages to Ollama prompt format."""
        prompt_parts = []
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}")
            elif message.role == "user":
                prompt_parts.append(f"User: {message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"Assistant: {message.content}")

        return "\n\n".join(prompt_parts) + "\n\nAssistant:"


class LLMClientManager:
    """Manager for LLM providers."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all configured providers."""
        # OpenRouter
        if settings.openrouter_api_key:
            self.providers["openrouter"] = OpenAICompatibleProvider(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key
            )

        # OpenAI
        if settings.openai_api_key:
            self.providers["openai"] = OpenAICompatibleProvider(
                name="openai",
                base_url="https://api.openai.com/v1",
                api_key=settings.openai_api_key
            )

        # Ollama
        self.providers["ollama"] = OllamaProvider(settings.ollama_base_url)

    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get a provider by name."""
        return self.providers.get(provider_name)

    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all providers."""
        results = {}
        for name, provider in self.providers.items():
            results[name] = await provider.health_check()
        return results

    async def generate_response(
        self,
        provider_name: str,
        model: str,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Generate response using specified provider and model."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise LLMProviderError(f"Provider '{provider_name}' not found")

        return await provider.generate_response(messages, model, **kwargs)


# Global client manager
llm_client = LLMClientManager()