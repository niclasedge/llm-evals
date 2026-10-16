"""
Client factory for LLM evaluation testing.
Provides centralized client creation and configuration management.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from enum import Enum

from .ollama_client import OllamaClient
from ..config import (
    ENABLE_OLLAMA, ENABLE_GO_SERVICE, ENABLE_OPENROUTER,
    OLLAMA_BASE_URL, GO_SERVICE_URL, OPENROUTER_API_KEY
)

logger = logging.getLogger(__name__)


class ClientType(Enum):
    """Enumeration of supported client types."""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    MOCK = "mock"


class ClientFactory:
    """Factory for creating LLM evaluation clients."""
    
    def __init__(self):
        self._clients = {}
        self._default_configs = {
            ClientType.OLLAMA: {
                "base_url": OLLAMA_BASE_URL,
                "use_go_service": ENABLE_GO_SERVICE,
                "enabled": ENABLE_OLLAMA
            },
            ClientType.OPENROUTER: {
                "api_key": OPENROUTER_API_KEY,
                "enabled": ENABLE_OPENROUTER
            },
            ClientType.MOCK: {
                "enabled": True
            }
        }
    
    def create_client(self, client_type: Union[ClientType, str], 
                     config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Create a client instance of the specified type.
        
        Args:
            client_type: Type of client to create
            config: Optional configuration overrides
            
        Returns:
            Configured client instance
            
        Raises:
            ValueError: If client type is not supported or configuration is invalid
        """
        if isinstance(client_type, str):
            try:
                client_type = ClientType(client_type)
            except ValueError:
                raise ValueError(f"Unsupported client type: {client_type}")
        
        # Get default configuration
        default_config = self._default_configs.get(client_type, {})
        
        # Merge with provided configuration
        final_config = default_config.copy()
        if config:
            final_config.update(config)
        
        # Check if client type is enabled
        if not final_config.get("enabled", True):
            raise ValueError(f"Client type {client_type.value} is not enabled")
        
        # Create client based on type
        if client_type == ClientType.OLLAMA:
            return self._create_ollama_client(final_config)
        elif client_type == ClientType.OPENROUTER:
            return self._create_openrouter_client(final_config)
        elif client_type == ClientType.MOCK:
            return self._create_mock_client(final_config)
        else:
            raise ValueError(f"Unsupported client type: {client_type}")
    
    def _create_ollama_client(self, config: Dict[str, Any]) -> OllamaClient:
        """Create Ollama client with configuration."""
        return OllamaClient(
            base_url=config.get("base_url", OLLAMA_BASE_URL),
            use_go_service=config.get("use_go_service", ENABLE_GO_SERVICE)
        )
    
    def _create_openrouter_client(self, config: Dict[str, Any]) -> Any:
        """Create OpenRouter client with configuration."""
        # Import here to avoid circular imports
        try:
            from .openrouter_client import OpenRouterClient
            return OpenRouterClient(
                api_key=config.get("api_key", OPENROUTER_API_KEY)
            )
        except ImportError:
            logger.warning("OpenRouter client not available, using mock client")
            return self._create_mock_client(config)
    
    def _create_mock_client(self, config: Dict[str, Any]) -> Any:
        """Create mock client for testing."""
        from .mock_client import MockClient
        return MockClient(**config)
    
    def get_available_clients(self) -> Dict[ClientType, bool]:
        """
        Get availability status of all client types.
        
        Returns:
            Dictionary mapping client types to availability status
        """
        availability = {}
        
        for client_type in ClientType:
            config = self._default_configs.get(client_type, {})
            enabled = config.get("enabled", True)
            
            # Additional checks for specific client types
            if client_type == ClientType.OLLAMA:
                # Check if Ollama is properly configured
                availability[client_type] = enabled and bool(config.get("base_url"))
            elif client_type == ClientType.OPENROUTER:
                # Check if API key is available
                availability[client_type] = enabled and bool(config.get("api_key"))
            else:
                availability[client_type] = enabled
        
        return availability
    
    def create_default_client(self, prefer_go_service: bool = None) -> Any:
        """
        Create a default client based on available configuration.
        
        Args:
            prefer_go_service: Whether to prefer Go service for Ollama
            
        Returns:
            Default client instance
        """
        availability = self.get_available_clients()
        
        # Prefer Ollama if available
        if availability.get(ClientType.OLLAMA):
            config = {}
            if prefer_go_service is not None:
                config["use_go_service"] = prefer_go_service
            return self.create_client(ClientType.OLLAMA, config)
        
        # Fallback to OpenRouter
        if availability.get(ClientType.OPENROUTER):
            return self.create_client(ClientType.OPENROUTER)
        
        # Last resort: mock client
        return self.create_client(ClientType.MOCK)
    
    def validate_configuration(self, client_type: Union[ClientType, str]) -> tuple[bool, str]:
        """
        Validate configuration for a specific client type.
        
        Args:
            client_type: Client type to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if isinstance(client_type, str):
            try:
                client_type = ClientType(client_type)
            except ValueError:
                return False, f"Unknown client type: {client_type}"
        
        config = self._default_configs.get(client_type, {})
        
        if not config.get("enabled", True):
            return False, f"Client type {client_type.value} is not enabled"
        
        if client_type == ClientType.OLLAMA:
            if not config.get("base_url"):
                return False, "Ollama base URL is not configured"
            
            if config.get("use_go_service") and not GO_SERVICE_URL:
                return False, "Go service URL is not configured"
        
        elif client_type == ClientType.OPENROUTER:
            if not config.get("api_key"):
                return False, "OpenRouter API key is not configured"
        
        return True, ""
    
    def get_client_info(self, client_type: Union[ClientType, str]) -> Dict[str, Any]:
        """
        Get information about a specific client type.
        
        Args:
            client_type: Client type to get info for
            
        Returns:
            Dictionary with client information
        """
        if isinstance(client_type, str):
            try:
                client_type = ClientType(client_type)
            except ValueError:
                return {"error": f"Unknown client type: {client_type}"}
        
        config = self._default_configs.get(client_type, {})
        is_valid, error = self.validate_configuration(client_type)
        
        info = {
            "type": client_type.value,
            "enabled": config.get("enabled", True),
            "valid": is_valid,
            "config": config.copy()
        }
        
        if not is_valid:
            info["error"] = error
        
        # Remove sensitive information
        if "api_key" in info["config"]:
            info["config"]["api_key"] = "***" if info["config"]["api_key"] else None
        
        return info


# Global factory instance
_factory = ClientFactory()


def create_client(client_type: Union[ClientType, str], 
                 config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Convenience function to create a client using the global factory.
    
    Args:
        client_type: Type of client to create
        config: Optional configuration overrides
        
    Returns:
        Configured client instance
    """
    return _factory.create_client(client_type, config)


def get_default_client(prefer_go_service: bool = None) -> Any:
    """
    Convenience function to get a default client.
    
    Args:
        prefer_go_service: Whether to prefer Go service for Ollama
        
    Returns:
        Default client instance
    """
    return _factory.create_default_client(prefer_go_service)


def get_available_clients() -> Dict[ClientType, bool]:
    """
    Convenience function to get available clients.
    
    Returns:
        Dictionary mapping client types to availability status
    """
    return _factory.get_available_clients()


def validate_client_config(client_type: Union[ClientType, str]) -> tuple[bool, str]:
    """
    Convenience function to validate client configuration.
    
    Args:
        client_type: Client type to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    return _factory.validate_configuration(client_type)


# Test function
def test_client_factory():
    """Test the client factory functionality."""
    print("Testing client factory...")
    
    factory = ClientFactory()
    
    # Test availability
    availability = factory.get_available_clients()
    print(f"Available clients: {availability}")
    
    # Test validation
    for client_type in ClientType:
        is_valid, error = factory.validate_configuration(client_type)
        print(f"{client_type.value}: {'✓' if is_valid else '✗'} {error}")
    
    # Test client creation
    try:
        client = factory.create_default_client()
        print(f"Default client created: {type(client).__name__}")
    except Exception as e:
        print(f"Failed to create default client: {e}")
    
    # Test client info
    for client_type in ClientType:
        info = factory.get_client_info(client_type)
        print(f"{client_type.value} info: {info}")


if __name__ == "__main__":
    test_client_factory()