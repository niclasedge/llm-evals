"""
Request adapter for Go service integration.
Handles request format adaptation between Python and Go service.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class RequestAdapter:
    """Adapter for converting Python requests to Go service format."""
    
    @staticmethod
    def adapt_generate_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Python generate request for Go service.
        
        Args:
            data: Python request data
            
        Returns:
            Go service compatible request data
        """
        # Ensure exact format compatibility with Ollama API
        adapted = {
            "model": data.get("model"),
            "prompt": data.get("prompt"),
            "stream": data.get("stream", False),
            "raw": data.get("raw", False)
        }
        
        # Add optional fields if present
        if "system" in data:
            adapted["system"] = data["system"]
        
        if "template" in data:
            adapted["template"] = data["template"]
        
        if "context" in data:
            adapted["context"] = data["context"]
        
        if "options" in data:
            adapted["options"] = data["options"]
        
        # Handle any additional kwargs
        for key, value in data.items():
            if key not in adapted and not key.startswith('_'):
                adapted[key] = value
        
        return adapted
    
    @staticmethod
    def adapt_chat_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Python chat request for Go service.
        
        Args:
            data: Python request data
            
        Returns:
            Go service compatible request data
        """
        adapted = {
            "model": data.get("model"),
            "messages": data.get("messages", []),
            "stream": data.get("stream", False)
        }
        
        # Add optional fields if present
        if "options" in data:
            adapted["options"] = data["options"]
        
        # Handle any additional kwargs
        for key, value in data.items():
            if key not in adapted and not key.startswith('_'):
                adapted[key] = value
        
        return adapted
    
    @staticmethod
    def adapt_pull_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Python pull request for Go service.
        
        Args:
            data: Python request data
            
        Returns:
            Go service compatible request data
        """
        return {
            "name": data.get("name") or data.get("model"),
            "insecure": data.get("insecure", False)
        }
    
    @staticmethod
    def adapt_show_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Python show request for Go service.
        
        Args:
            data: Python request data
            
        Returns:
            Go service compatible request data
        """
        return {
            "name": data.get("name") or data.get("model")
        }
    
    @staticmethod
    def adapt_models_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt Python models list request for Go service.
        
        Args:
            data: Python request data
            
        Returns:
            Go service compatible request data
        """
        # Models endpoint typically doesn't need parameters
        return {}
    
    @staticmethod
    def validate_request_data(data: Dict[str, Any], request_type: str) -> bool:
        """
        Validate request data for specific request type.
        
        Args:
            data: Request data to validate
            request_type: Type of request (generate, chat, pull, show, models)
            
        Returns:
            True if request data is valid
        """
        if request_type == "generate":
            return bool(data.get("model") and data.get("prompt"))
        
        elif request_type == "chat":
            return bool(data.get("model") and data.get("messages"))
        
        elif request_type == "pull":
            return bool(data.get("name") or data.get("model"))
        
        elif request_type == "show":
            return bool(data.get("name") or data.get("model"))
        
        elif request_type == "models":
            return True  # Models endpoint doesn't require specific parameters
        
        return False
    
    @staticmethod
    def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize request data by removing internal fields and None values.
        
        Args:
            data: Request data to sanitize
            
        Returns:
            Sanitized request data
        """
        sanitized = {}
        
        for key, value in data.items():
            # Skip internal fields that start with underscore
            if key.startswith('_'):
                continue
            
            # Skip None values
            if value is None:
                continue
            
            # Keep valid values
            sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def add_request_metadata(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add metadata to request data.
        
        Args:
            data: Original request data
            metadata: Metadata to add
            
        Returns:
            Request data with metadata
        """
        enhanced = data.copy()
        
        # Add metadata with underscore prefix to avoid conflicts
        for key, value in metadata.items():
            enhanced[f"_{key}"] = value
        
        return enhanced


class RequestValidator:
    """Validator for request data."""
    
    REQUIRED_FIELDS = {
        "generate": ["model", "prompt"],
        "chat": ["model", "messages"],
        "pull": ["name"],
        "show": ["name"],
        "models": []
    }
    
    OPTIONAL_FIELDS = {
        "generate": ["system", "template", "context", "options", "stream", "raw"],
        "chat": ["options", "stream"],
        "pull": ["insecure"],
        "show": [],
        "models": []
    }
    
    @classmethod
    def validate_request(cls, data: Dict[str, Any], request_type: str) -> tuple[bool, List[str]]:
        """
        Validate request data comprehensively.
        
        Args:
            data: Request data to validate
            request_type: Type of request
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if request type is supported
        if request_type not in cls.REQUIRED_FIELDS:
            errors.append(f"Unsupported request type: {request_type}")
            return False, errors
        
        # Check required fields
        required_fields = cls.REQUIRED_FIELDS[request_type]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate specific field types
        if request_type == "chat" and "messages" in data:
            if not isinstance(data["messages"], list):
                errors.append("Messages must be a list")
            else:
                for i, msg in enumerate(data["messages"]):
                    if not isinstance(msg, dict):
                        errors.append(f"Message {i} must be a dictionary")
                    elif "role" not in msg or "content" not in msg:
                        errors.append(f"Message {i} must have 'role' and 'content' fields")
        
        return len(errors) == 0, errors


# Test function for request adapter
def test_request_adapter():
    """Test the request adapter functionality."""
    adapter = RequestAdapter()
    
    print("Testing request adapter...")
    
    # Test generate request
    generate_data = {
        "model": "llama3",
        "prompt": "What is the capital of France?",
        "system": "You are a helpful assistant.",
        "stream": False,
        "options": {"temperature": 0.7}
    }
    
    adapted_generate = adapter.adapt_generate_request(generate_data)
    print(f"Adapted generate request: {adapted_generate}")
    
    # Test chat request
    chat_data = {
        "model": "llama3",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "stream": False
    }
    
    adapted_chat = adapter.adapt_chat_request(chat_data)
    print(f"Adapted chat request: {adapted_chat}")
    
    # Test validation
    validator = RequestValidator()
    is_valid, errors = validator.validate_request(generate_data, "generate")
    print(f"Generate request validation: {'✓' if is_valid else '✗'}")
    if not is_valid:
        print(f"Errors: {errors}")
    
    is_valid, errors = validator.validate_request(chat_data, "chat")
    print(f"Chat request validation: {'✓' if is_valid else '✗'}")
    if not is_valid:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    test_request_adapter()