"""
Go service integration module for LLM evaluation.
Provides bridge between Python evaluation framework and Go service.
"""

from .go_service_client import GoServiceClient
from .service_discovery import GoServiceDiscovery
from .request_adapter import RequestAdapter
from .response_mapper import ResponseMapper
from .fallback_manager import FallbackManager

__all__ = [
    'GoServiceClient',
    'GoServiceDiscovery',
    'RequestAdapter',
    'ResponseMapper',
    'FallbackManager'
]