"""
Response mapper for Go service integration.
Handles response format mapping between Go service and Python expectations.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseMapper:
    """Mapper for converting Go service responses to Python format."""
    
    @staticmethod
    def map_generate_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Go service generate response to Python format.
        
        Args:
            response: Go service response
            
        Returns:
            Python-compatible response
        """
        # Ensure compatibility with existing Python code expectations
        mapped = {
            "model": response.get("model"),
            "response": response.get("response"),
            "done": response.get("done", True),
            "context": response.get("context", []),
            "total_duration": response.get("total_duration", 0),
            "load_duration": response.get("load_duration", 0),
            "prompt_eval_count": response.get("prompt_eval_count", 0),
            "prompt_eval_duration": response.get("prompt_eval_duration", 0),
            "eval_count": response.get("eval_count", 0),
            "eval_duration": response.get("eval_duration", 0),
        }
        
        # Preserve timing information if present
        if "_timing" in response:
            mapped["_timing"] = response["_timing"]
        
        # Add any additional fields that don't conflict
        for key, value in response.items():
            if key not in mapped and not key.startswith('_'):
                mapped[key] = value
        
        return mapped
    
    @staticmethod
    def map_chat_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Go service chat response to Python format.
        
        Args:
            response: Go service response
            
        Returns:
            Python-compatible response
        """
        mapped = {
            "model": response.get("model"),
            "message": response.get("message", {}),
            "done": response.get("done", True),
            "total_duration": response.get("total_duration", 0),
            "load_duration": response.get("load_duration", 0),
            "prompt_eval_count": response.get("prompt_eval_count", 0),
            "prompt_eval_duration": response.get("prompt_eval_duration", 0),
            "eval_count": response.get("eval_count", 0),
            "eval_duration": response.get("eval_duration", 0),
        }
        
        # Preserve timing information if present
        if "_timing" in response:
            mapped["_timing"] = response["_timing"]
        
        # Add any additional fields that don't conflict
        for key, value in response.items():
            if key not in mapped and not key.startswith('_'):
                mapped[key] = value
        
        return mapped
    
    @staticmethod
    def map_models_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Go service models response to Python format.
        
        Args:
            response: Go service response
            
        Returns:
            List of model information dictionaries
        """
        models = response.get("models", [])
        
        mapped_models = []
        for model in models:
            mapped_model = {
                "name": model.get("name"),
                "size": model.get("size", 0),
                "digest": model.get("digest"),
                "details": model.get("details", {}),
                "modified_at": model.get("modified_at"),
                "expires_at": model.get("expires_at"),
                "size_vram": model.get("size_vram", 0),
            }
            mapped_models.append(mapped_model)
        
        return mapped_models
    
    @staticmethod
    def map_show_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Go service show response to Python format.
        
        Args:
            response: Go service response
            
        Returns:
            Python-compatible response
        """
        mapped = {
            "license": response.get("license"),
            "modelfile": response.get("modelfile"),
            "parameters": response.get("parameters"),
            "template": response.get("template"),
            "details": response.get("details", {}),
            "model_info": response.get("model_info", {}),
        }
        
        # Add any additional fields that don't conflict
        for key, value in response.items():
            if key not in mapped and not key.startswith('_'):
                mapped[key] = value
        
        return mapped
    
    @staticmethod
    def map_pull_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Go service pull response to Python format.
        
        Args:
            response: Go service response
            
        Returns:
            Python-compatible response
        """
        mapped = {
            "status": response.get("status"),
            "digest": response.get("digest"),
            "total": response.get("total", 0),
            "completed": response.get("completed", 0),
        }
        
        # Add any additional fields that don't conflict
        for key, value in response.items():
            if key not in mapped and not key.startswith('_'):
                mapped[key] = value
        
        return mapped
    
    @staticmethod
    def map_error_response(response: Dict[str, Any], original_error: Exception = None) -> Dict[str, Any]:
        """
        Map error response to consistent Python format.
        
        Args:
            response: Go service error response
            original_error: Original exception if available
            
        Returns:
            Standardized error response
        """
        error_info = {
            "error": True,
            "message": response.get("error", "Unknown error"),
            "code": response.get("code", "UNKNOWN"),
            "details": response.get("details", {}),
            "via_go_service": True,
        }
        
        if original_error:
            error_info["original_error"] = str(original_error)
            error_info["error_type"] = type(original_error).__name__
        
        return error_info
    
    @staticmethod
    def add_service_metadata(response: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add service metadata to response.
        
        Args:
            response: Original response
            metadata: Metadata to add
            
        Returns:
            Response with metadata
        """
        enhanced = response.copy()
        
        # Add metadata with underscore prefix to avoid conflicts
        for key, value in metadata.items():
            enhanced[f"_{key}"] = value
        
        return enhanced
    
    @staticmethod
    def normalize_response_format(response: Dict[str, Any], response_type: str) -> Dict[str, Any]:
        """
        Normalize response format based on response type.
        
        Args:
            response: Response to normalize
            response_type: Type of response (generate, chat, models, show, pull)
            
        Returns:
            Normalized response
        """
        if response_type == "generate":
            return ResponseMapper.map_generate_response(response)
        elif response_type == "chat":
            return ResponseMapper.map_chat_response(response)
        elif response_type == "models":
            return ResponseMapper.map_models_response(response)
        elif response_type == "show":
            return ResponseMapper.map_show_response(response)
        elif response_type == "pull":
            return ResponseMapper.map_pull_response(response)
        else:
            logger.warning(f"Unknown response type: {response_type}")
            return response


class ResponseValidator:
    """Validator for response data."""
    
    REQUIRED_FIELDS = {
        "generate": ["model", "response"],
        "chat": ["model", "message"],
        "models": [],  # Models response is a list
        "show": ["modelfile"],
        "pull": ["status"]
    }
    
    @classmethod
    def validate_response(cls, response: Any, response_type: str) -> tuple[bool, List[str]]:
        """
        Validate response data comprehensively.
        
        Args:
            response: Response data to validate
            response_type: Type of response
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if response type is supported
        if response_type not in cls.REQUIRED_FIELDS:
            errors.append(f"Unsupported response type: {response_type}")
            return False, errors
        
        # Special handling for models response (list)
        if response_type == "models":
            if not isinstance(response, list):
                errors.append("Models response must be a list")
            return len(errors) == 0, errors
        
        # Check if response is a dictionary
        if not isinstance(response, dict):
            errors.append("Response must be a dictionary")
            return False, errors
        
        # Check required fields
        required_fields = cls.REQUIRED_FIELDS[response_type]
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
        
        # Validate specific field types
        if response_type == "chat" and "message" in response:
            message = response["message"]
            if not isinstance(message, dict):
                errors.append("Message must be a dictionary")
            elif "content" not in message:
                errors.append("Message must have 'content' field")
        
        return len(errors) == 0, errors


# Test function for response mapper
def test_response_mapper():
    """Test the response mapper functionality."""
    mapper = ResponseMapper()
    
    print("Testing response mapper...")
    
    # Test generate response
    generate_response = {
        "model": "llama3",
        "response": "Paris is the capital of France.",
        "done": True,
        "total_duration": 1000000,
        "eval_count": 10,
        "_timing": {
            "response_time": 1.5,
            "via_go_service": True
        }
    }
    
    mapped_generate = mapper.map_generate_response(generate_response)
    print(f"Mapped generate response: {mapped_generate}")
    
    # Test chat response
    chat_response = {
        "model": "llama3",
        "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?"
        },
        "done": True,
        "total_duration": 800000,
        "_timing": {
            "response_time": 0.8,
            "via_go_service": True
        }
    }
    
    mapped_chat = mapper.map_chat_response(chat_response)
    print(f"Mapped chat response: {mapped_chat}")
    
    # Test models response
    models_response = {
        "models": [
            {
                "name": "llama3",
                "size": 4000000000,
                "digest": "abc123",
                "details": {}
            }
        ]
    }
    
    mapped_models = mapper.map_models_response(models_response)
    print(f"Mapped models response: {mapped_models}")
    
    # Test validation
    validator = ResponseValidator()
    is_valid, errors = validator.validate_response(mapped_generate, "generate")
    print(f"Generate response validation: {'✓' if is_valid else '✗'}")
    if not is_valid:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    test_response_mapper()