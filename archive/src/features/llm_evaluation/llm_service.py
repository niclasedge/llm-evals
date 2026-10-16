# LLM Service for Evaluations
import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Ollama imports will be done conditionally
OllamaModel = None
OllamaProvider = None
from . import config

# Import unified LLM client for new integration
try:
    from ...core.llm_client import UnifiedLLMClient, LLMAgent, get_unified_llm_agent
    UNIFIED_CLIENT_AVAILABLE = True
except ImportError:
    UNIFIED_CLIENT_AVAILABLE = False

# The VERY IMPORTANT NOTE regarding file location can be removed as the file has been moved.

def should_use_unified_client(model_provider: str, model_identifier: str) -> bool:
    """
    Determine if the unified client should be used for a given model.
    
    Args:
        model_provider: Provider name
        model_identifier: Model identifier
        
    Returns:
        True if unified client should be used
    """
    # Always use unified client for LLM CLI
    if model_provider == "llm_cli":
        return True
    
    # Check if model is available in unified config
    if UNIFIED_CLIENT_AVAILABLE:
        try:
            from ...core.llm_unified_config import get_unified_config
            config = get_unified_config()
            return config.resolve_model_name(model_identifier) is not None
        except Exception:
            return False
    
    return False

def load_image_for_model(image_path: str) -> Optional[Dict]:
    """
    Load and encode image for model input.
    
    Args:
        image_path (str): Path to the image file.
        
    Returns:
        dict: Image data in format suitable for vision models, or None if error.
    """
    try:
        image_file = Path(image_path)
        if not image_file.exists():
            print(f"Error: Image file not found: {image_path}")
            return None
            
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            print(f"Error: Invalid image type: {mime_type}")
            return None
            
        # Read and encode image
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            
        # Encode to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        return {
            'type': 'image_url',
            'image_url': {
                'url': f"data:{mime_type};base64,{base64_image}"
            }
        }
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None

def get_vision_agent(model_provider: str, model_identifier: str, system_prompt: str = None):
    """
    Create agent specifically for vision models.
    
    Args:
        model_provider (str): 'ollama' or 'openrouter'.
        model_identifier (str): The specific model name or ID.
        system_prompt (str, optional): The system prompt for the agent.
                                     Defaults to config.DEFAULT_VISION_SYSTEM_PROMPT.
                                     
    Returns:
        Agent: An instance of pydantic_ai.Agent, or None if initialization fails.
    """
    if system_prompt is None:
        system_prompt = config.DEFAULT_VISION_SYSTEM_PROMPT
        
    return get_llm_agent(model_provider, model_identifier, system_prompt)

def get_llm_agent(model_provider: str, model_identifier: str, system_prompt: str = None):
    """
    Initializes and returns a PydanticAI Agent for the given provider and model.
    Now with unified client integration support.

    Args:
        model_provider (str): 'ollama', 'openrouter', or 'llm_cli'.
        model_identifier (str): The specific model name or ID.
        system_prompt (str, optional): The system prompt for the agent. 
                                     Defaults to config.DEFAULT_SYSTEM_PROMPT.

    Returns:
        Agent: An instance of pydantic_ai.Agent, or None if initialization fails.
    """
    if system_prompt is None:
        system_prompt = config.DEFAULT_SYSTEM_PROMPT

    # Try unified client first for better integration
    if UNIFIED_CLIENT_AVAILABLE and should_use_unified_client(model_provider, model_identifier):
        try:
            return get_unified_llm_agent(model_provider, model_identifier, system_prompt)
        except Exception as e:
            print(f"Failed to create unified client for {model_provider}/{model_identifier}: {e}")
            # Fall back to legacy implementation
    
    # Legacy implementation for backward compatibility
    llm_instance = None
    
    if model_provider == "ollama":
        if not config.ENABLE_OLLAMA:
            print(f"Ollama is disabled in config. Skipping model: {model_identifier}")
            return None
        
        global OllamaModel, OllamaProvider # Allow modification of global placeholders
        if OllamaModel is None or OllamaProvider is None:
            try:
                from pydantic_ai.models.ollama import OllamaModel as _OllamaModel
                from pydantic_ai.providers.ollama import OllamaProvider as _OllamaProvider
                OllamaModel = _OllamaModel
                OllamaProvider = _OllamaProvider
            except ImportError:
                print("Error: Ollama components for pydantic-ai not found. Please ensure 'pydantic-ai[ollama]' is installed if you want to use Ollama.", file=sys.stderr)
                return None
        try:
            ollama_provider_instance = OllamaProvider(base_url=config.OLLAMA_BASE_URL)
            llm_instance = OllamaModel(
                model=model_identifier,
                provider=ollama_provider_instance
            )
            print(f"Initialized Ollama agent for model: {model_identifier} with provider at {config.OLLAMA_BASE_URL}")
        except Exception as e:
            print(f"Error initializing Ollama model {model_identifier}: {e}", file=sys.stderr)
            return None

    elif model_provider == "openrouter":
        if not config.ENABLE_OPENROUTER:
            print(f"OpenRouter is disabled in config. Skipping model: {model_identifier}")
            return None
        if not config.OPENROUTER_API_KEY:
            print(f"OpenRouter API key not found for model: {model_identifier}. Skipping.", file=sys.stderr)
            return None
        try:
            openrouter_provider_instance = OpenAIProvider(
                api_key=config.OPENROUTER_API_KEY,
                base_url=config.OPENROUTER_BASE_URL
            )
            llm_instance = OpenAIModel(
                model_name=model_identifier, # For OpenRouter, this is the full model string like 'mistralai/mistral-7b-instruct'
                provider=openrouter_provider_instance
            )
            print(f"Initialized OpenRouter agent for model: {model_identifier}")
        except Exception as e:
            print(f"Error initializing OpenRouter model {model_identifier}: {e}", file=sys.stderr)
            return None
    elif model_provider == "llm_cli":
        # Use unified client for LLM CLI
        if UNIFIED_CLIENT_AVAILABLE:
            try:
                return get_unified_llm_agent(model_provider, model_identifier, system_prompt)
            except Exception as e:
                print(f"Error initializing LLM CLI model {model_identifier}: {e}", file=sys.stderr)
                return None
        else:
            print(f"Unified client not available for LLM CLI model: {model_identifier}", file=sys.stderr)
            return None
    else:
        print(f"Unsupported model provider: {model_provider}", file=sys.stderr)
        return None

    if llm_instance:
        return Agent(llm_instance, instructions=system_prompt)
    return None

async def run_vision_query(agent: Agent, query: str, image_path: str = None, image_data: Dict = None):
    """
    Run query with optional image input for vision models.
    
    Args:
        agent (Agent): The initialized PydanticAI Agent.
        query (str): The query string.
        image_path (str, optional): Path to image file.
        image_data (dict, optional): Pre-loaded image data.
        
    Returns:
        str: The response from the LLM, or None if an error occurs.
    """
    if not agent:
        print("Cannot run vision query: Agent is not initialized.", file=sys.stderr)
        return None
        
    # Load image if path provided
    if image_path and not image_data:
        image_data = load_image_for_model(image_path)
        if not image_data:
            print(f"Failed to load image: {image_path}")
            return None
    
    # Get model display name
    model_display_name = "Unknown Model"
    if hasattr(agent, 'model') and agent.model:
        llm_instance = agent.model
        temp_name = None
        if hasattr(llm_instance, '_model_name'):
            val = getattr(llm_instance, '_model_name', None)
            if isinstance(val, str) and val:
                temp_name = val
        if not temp_name and hasattr(llm_instance, 'model_name'):
            val = getattr(llm_instance, 'model_name', None)
            if isinstance(val, str) and val:
                temp_name = val
        if not temp_name and hasattr(llm_instance, 'model'):
            val = getattr(llm_instance, 'model', None)
            if isinstance(val, str) and val:
                temp_name = val
        if temp_name:
            model_display_name = temp_name
    
    try:
        print(f"Running vision query: '{query[:50]}...' on agent: {model_display_name}")
        
        # Format query for vision models
        if image_data:
            # Create multimodal input
            user_message = [
                {"type": "text", "text": query},
                image_data
            ]
            response = await agent.run(user_message)
        else:
            # Fallback to text-only query
            response = await agent.run(query)
            
        return response
    except Exception as e:
        print(f"Error running vision query on agent {model_display_name}: {e}", file=sys.stderr)
        return None

async def run_query(agent: Agent, query: str):
    """
    Runs a query against the provided PydanticAI Agent.

    Args:
        agent (Agent): The initialized PydanticAI Agent.
        query (str): The query string.

    Returns:
        str: The response from the LLM, or None if an error occurs.
    """
    if not agent:
        print("Cannot run query: Agent is not initialized.", file=sys.stderr)
        return None

    model_display_name = "Unknown Model"
    if hasattr(agent, 'model') and agent.model:
        llm_instance = agent.model # In pydantic-ai 0.1.x, the llm_instance is agent.model
        # print(f"DEBUG run_query: llm_instance type: {type(llm_instance)}") # Optional: for deeper debugging
        temp_name = None
        # Try to get model name: _model_name (common for OpenAIModel based), then model_name (property), then model (common for Ollama)
        if hasattr(llm_instance, '_model_name'):
            val = getattr(llm_instance, '_model_name', None)
            if isinstance(val, str) and val:
                temp_name = val
        if not temp_name and hasattr(llm_instance, 'model_name'):
            val = getattr(llm_instance, 'model_name', None)
            if isinstance(val, str) and val:
                temp_name = val
        if not temp_name and hasattr(llm_instance, 'model'): # This is the direct attribute for OllamaModel
            val = getattr(llm_instance, 'model', None)
            if isinstance(val, str) and val:
                temp_name = val

        if temp_name:
            model_display_name = temp_name
        # else: print(f"DEBUG run_query: Could not extract model name from llm_instance, using default: {model_display_name}")
    # else: print("DEBUG run_query: agent.model is missing or None")
            
    try:
        print(f"Running query: '{query[:50]}...' on agent: {model_display_name}")
        response = await agent.run(query)
        return response
    except Exception as e:
        print(f"Error running query on agent {model_display_name}: {e}", file=sys.stderr)
        return None

async def main_test():
    # Basic test for the service module (will run if script is executed directly)
    print("Testing llm_service.py...")

    # Test Ollama (if enabled and model exists)
    if config.ENABLE_OLLAMA and config.OLLAMA_MODELS_TO_TEST:
        ollama_model_to_test = config.OLLAMA_MODELS_TO_TEST[0]
        print(f"\n--- Testing Ollama with model: {ollama_model_to_test} ---")
        ollama_agent = get_llm_agent("ollama", ollama_model_to_test, "Be a pirate.")
        if ollama_agent:
            response = await run_query(ollama_agent, "Ahoy! What be the weather today?")
            print(f"Ollama ({ollama_model_to_test}) Response: {response}")
        else:
            print(f"Could not create Ollama agent for {ollama_model_to_test}.")
    else:
        print("\nSkipping Ollama test (disabled or no models configured).")

    # Test OpenRouter (if enabled, API key set, and model exists)
    if config.ENABLE_OPENROUTER and config.OPENROUTER_MODELS_TO_TEST and config.OPENROUTER_API_KEY:
        openrouter_model_to_test = config.OPENROUTER_MODELS_TO_TEST[0]
        print(f"\n--- Testing OpenRouter with model: {openrouter_model_to_test} ---")
        openrouter_agent = get_llm_agent("openrouter", openrouter_model_to_test, "Speak like Yoda, you must.")
        if openrouter_agent:
            response = await run_query(openrouter_agent, "The capital of France, what is it?")
            print(f"OpenRouter ({openrouter_model_to_test}) Response: {response}")
        else:
            print(f"Could not create OpenRouter agent for {openrouter_model_to_test}.")
    else:
        print("\nSkipping OpenRouter test (disabled, no API key, or no models configured).")

    print("\nllm_service.py test finished.")

if __name__ == '__main__':
    asyncio.run(main_test())
