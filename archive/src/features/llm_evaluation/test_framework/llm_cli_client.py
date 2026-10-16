"""
LLM CLI client wrapper for Simon Willison's LLM tool.
Provides Python interface to LLM CLI commands for standardized testing.
Enhanced with unified configuration system support.
"""

import asyncio
import json
import subprocess
import time
from typing import List, Dict, Optional, Any
import shlex

# Import unified configuration system
try:
    from src.core.llm_unified_config import get_unified_config
    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    UNIFIED_CONFIG_AVAILABLE = False


class LLMCLIClient:
    """
    Client for interacting with Simon Willison's LLM CLI tool.
    Enhanced with unified configuration system support.
    """
    
    def __init__(self, llm_command: str = "llm"):
        self.command_base = llm_command
        self.unified_config = get_unified_config() if UNIFIED_CONFIG_AVAILABLE else None
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if LLM CLI tool is available."""
        try:
            result = subprocess.run([self.command_base, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def is_available(self) -> bool:
        """Check if LLM CLI tool is available."""
        return self._check_availability()
    
    def resolve_model_name(self, model_name: str) -> str:
        """
        Resolve model name using unified configuration system.
        
        Args:
            model_name: Model name, alias, or LLM CLI format
            
        Returns:
            Resolved model name for LLM CLI
        """
        if not self.unified_config:
            return model_name
        
        # Try to resolve using unified config
        model_config = self.unified_config.resolve_model_name(model_name)
        if model_config:
            # For LLM CLI, we can use the provider:model_id format
            # or just the model_id depending on the provider
            if model_config.provider == "openrouter":
                return f"openrouter:{model_config.model_id}"
            elif model_config.provider == "openai":
                return f"openai:{model_config.model_id}"
            elif model_config.provider == "ollama":
                return model_config.model_id
            else:
                return model_config.model_id
        
        # If not found in unified config, return original name
        return model_name
    
    def get_available_models_from_config(self, provider: str = None, capability: str = None) -> List[str]:
        """
        Get available models from unified configuration.
        
        Args:
            provider: Filter by provider (openrouter, ollama, etc.)
            capability: Filter by capability (text, vision, code, etc.)
            
        Returns:
            List of model names available in unified config
        """
        if not self.unified_config:
            return []
        
        models = self.unified_config.list_models(
            provider=provider,
            capability=capability,
            enabled_only=True
        )
        return [model.name for model in models]
    
    def get_model_aliases(self, model_name: str) -> List[str]:
        """
        Get aliases for a model from unified configuration.
        
        Args:
            model_name: Model name
            
        Returns:
            List of aliases for the model
        """
        if not self.unified_config:
            return []
        
        model_config = self.unified_config.resolve_model_name(model_name)
        if model_config:
            return model_config.aliases
        
        return []
    
    async def run_prompt(self, prompt: str, model: Optional[str] = None, 
                        system_prompt: Optional[str] = None, 
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Execute LLM CLI command with prompt.
        Model names are resolved using unified configuration system.
        """
        try:
            cmd = [self.command_base]
            
            # Resolve model name using unified config
            resolved_model = None
            if model:
                resolved_model = self.resolve_model_name(model)
                cmd.extend(["-m", resolved_model])
            
            # Add system prompt if specified
            if system_prompt:
                cmd.extend(["-s", system_prompt])
            
            # Add temperature if specified
            if temperature is not None:
                cmd.extend(["-o", "temperature", str(temperature)])
            
            # Add max tokens if specified
            if max_tokens is not None:
                cmd.extend(["-o", "max_tokens", str(max_tokens)])
            
            # Add the prompt
            cmd.append(prompt)
            
            start_time = time.time()
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            end_time = time.time()
            
            if process.returncode == 0:
                return {
                    'response': stdout.strip(),
                    'model': resolved_model or model or 'default',
                    'original_model': model,
                    'resolved_model': resolved_model,
                    'command': ' '.join(shlex.quote(arg) for arg in cmd),
                    '_timing': {
                        'response_time': end_time - start_time,
                        'timestamp': start_time
                    },
                    'success': True
                }
            else:
                print(f"LLM CLI error: {stderr}")
                return {
                    'error': stderr.strip(),
                    'command': ' '.join(shlex.quote(arg) for arg in cmd),
                    '_timing': {
                        'response_time': end_time - start_time,
                        'timestamp': start_time
                    },
                    'success': False
                }
        except Exception as e:
            print(f"Error running LLM CLI: {e}")
            return None
    
    async def list_models(self) -> List[str]:
        """List available models via LLM CLI."""
        try:
            cmd = [self.command_base, "models", "list"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            
            if process.returncode == 0:
                # Parse the output to extract model names
                models = []
                for line in stdout.strip().split('\n'):
                    if line.strip() and ':' in line:
                        # Extract model name from format "Provider Type: model_name (aliases: ...)"
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            model_part = parts[1].strip()
                            # Extract just the model name before any aliases
                            if '(' in model_part:
                                model_name = model_part.split('(')[0].strip()
                            else:
                                model_name = model_part.strip()
                            if model_name:
                                models.append(model_name)
                return models
            else:
                print(f"Error listing models: {stderr}")
                return []
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    async def install_plugin(self, plugin_name: str) -> bool:
        """Install LLM CLI plugin."""
        try:
            cmd = [self.command_base, "install", plugin_name]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            
            if process.returncode == 0:
                print(f"Successfully installed plugin: {plugin_name}")
                return True
            else:
                print(f"Error installing plugin {plugin_name}: {stderr}")
                return False
        except Exception as e:
            print(f"Error installing plugin: {e}")
            return False
    
    async def chat(self, model: Optional[str] = None, 
                  system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Start interactive chat session (returns command for manual execution).
        Model names are resolved using unified configuration system.
        """
        cmd = [self.command_base, "chat"]
        
        # Resolve model name using unified config
        if model:
            resolved_model = self.resolve_model_name(model)
            cmd.extend(["-m", resolved_model])
        
        if system_prompt:
            cmd.extend(["-s", system_prompt])
        
        return ' '.join(shlex.quote(arg) for arg in cmd)
    
    async def extract_from_image(self, image_path: str, prompt: str = "extract text",
                                model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract information from image using LLM CLI.
        Model names are resolved using unified configuration system.
        """
        try:
            cmd = [self.command_base, prompt, "-a", image_path]
            
            # Resolve model name using unified config
            resolved_model = None
            if model:
                resolved_model = self.resolve_model_name(model)
                cmd.extend(["-m", resolved_model])
            
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            end_time = time.time()
            
            if process.returncode == 0:
                return {
                    'response': stdout.strip(),
                    'model': resolved_model or model or 'default',
                    'original_model': model,
                    'resolved_model': resolved_model,
                    'image_path': image_path,
                    'command': ' '.join(shlex.quote(arg) for arg in cmd),
                    '_timing': {
                        'response_time': end_time - start_time,
                        'timestamp': start_time
                    },
                    'success': True
                }
            else:
                print(f"Error extracting from image: {stderr}")
                return {
                    'error': stderr.strip(),
                    'command': ' '.join(shlex.quote(arg) for arg in cmd),
                    '_timing': {
                        'response_time': end_time - start_time,
                        'timestamp': start_time
                    },
                    'success': False
                }
        except Exception as e:
            print(f"Error extracting from image: {e}")
            return None
    
    async def embed_text(self, text: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate embeddings for text using LLM CLI.
        Model names are resolved using unified configuration system.
        """
        try:
            cmd = [self.command_base, "embed", text]
            
            # Resolve model name using unified config
            resolved_model = None
            if model:
                resolved_model = self.resolve_model_name(model)
                cmd.extend(["-m", resolved_model])
            
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            end_time = time.time()
            
            if process.returncode == 0:
                try:
                    # Try to parse as JSON if it's embedding data
                    embedding_data = json.loads(stdout.strip())
                    return {
                        'embedding': embedding_data,
                        'model': resolved_model or model or 'default',
                        'original_model': model,
                        'resolved_model': resolved_model,
                        'text': text,
                        '_timing': {
                            'response_time': end_time - start_time,
                            'timestamp': start_time
                        },
                        'success': True
                    }
                except json.JSONDecodeError:
                    return {
                        'response': stdout.strip(),
                        'model': resolved_model or model or 'default',
                        'original_model': model,
                        'resolved_model': resolved_model,
                        'text': text,
                        '_timing': {
                            'response_time': end_time - start_time,
                            'timestamp': start_time
                        },
                        'success': True
                    }
            else:
                print(f"Error generating embedding: {stderr}")
                return {
                    'error': stderr.strip(),
                    '_timing': {
                        'response_time': end_time - start_time,
                        'timestamp': start_time
                    },
                    'success': False
                }
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    async def logs(self, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get recent conversation logs."""
        try:
            cmd = [self.command_base, "logs", "-n", str(limit)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Decode bytes to string
            if stdout:
                stdout = stdout.decode('utf-8')
            if stderr:
                stderr = stderr.decode('utf-8')
            
            if process.returncode == 0:
                # Parse log output
                logs = []
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            log_data = json.loads(line)
                            logs.append(log_data)
                        except json.JSONDecodeError:
                            # If not JSON, store as text
                            logs.append({'text': line.strip()})
                return logs
            else:
                print(f"Error getting logs: {stderr}")
                return None
        except Exception as e:
            print(f"Error getting logs: {e}")
            return None


# Example usage and test function
async def test_llm_cli_client():
    """Test the LLM CLI client functionality with unified configuration."""
    client = LLMCLIClient()
    
    print("Testing LLM CLI client with unified configuration...")
    
    # Check availability
    is_available = client.is_available()
    print(f"LLM CLI availability: {'✓' if is_available else '✗'}")
    
    if not is_available:
        print("LLM CLI is not available. Please install it with: pip install llm")
        return
    
    # Check unified config availability
    print(f"Unified config availability: {'✓' if UNIFIED_CONFIG_AVAILABLE else '✗'}")
    
    if UNIFIED_CONFIG_AVAILABLE:
        # Test unified config features
        config_models = client.get_available_models_from_config()
        print(f"Models from unified config: {config_models}")
        
        # Test alias resolution
        for alias in ["llama3", "gemma1b", "llama3-vision"]:
            aliases = client.get_model_aliases(alias)
            resolved = client.resolve_model_name(alias)
            print(f"Alias '{alias}' -> resolved: '{resolved}', all aliases: {aliases}")
    
    # List models from LLM CLI
    models = await client.list_models()
    print(f"Available models from LLM CLI: {models}")
    
    # Test basic prompt
    response = await client.run_prompt(
        "What is the capital of France?",
        system_prompt="You are a helpful assistant."
    )
    
    if response and response.get('success'):
        print(f"Prompt response: {response['response']}")
        print(f"Response time: {response['_timing']['response_time']:.2f}s")
    elif response:
        print(f"Error: {response.get('error', 'Unknown error')}")
    
    # Test with unified config alias if available
    if UNIFIED_CONFIG_AVAILABLE:
        print("Testing with unified config alias 'llama3'...")
        alias_response = await client.run_prompt(
            "Tell me a joke",
            model="llama3"
        )
        
        if alias_response and alias_response.get('success'):
            print(f"Alias response: {alias_response['response']}")
            print(f"Original model: {alias_response.get('original_model')}")
            print(f"Resolved model: {alias_response.get('resolved_model')}")
    
    # Test with specific model if available
    if models:
        test_model = models[0]
        print(f"Testing with model: {test_model}")
        
        model_response = await client.run_prompt(
            "Tell me a joke",
            model=test_model
        )
        
        if model_response and model_response.get('success'):
            print(f"Model response: {model_response['response']}")
    
    # Get recent logs
    logs = await client.logs(limit=5)
    if logs:
        print(f"Recent logs: {len(logs)} entries")


if __name__ == "__main__":
    asyncio.run(test_llm_cli_client())