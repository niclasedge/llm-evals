import os
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import base64

from . import config


class ImageGenerationService:
    def __init__(self):
        self.output_dir = Path(config.IMAGE_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        
    async def generate_image(self, provider: str, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image and return metadata"""
        try:
            if provider == "openai":
                return await self._generate_openai_image(model, prompt, **kwargs)
            elif provider == "stability":
                return await self._generate_stability_image(model, prompt, **kwargs)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_openai_image(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image using OpenAI DALL-E API"""
        if not config.DALLE_API_KEY:
            raise ValueError("OpenAI API key not set")
        
        headers = {
            "Authorization": f"Bearer {config.DALLE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare request data
        size = kwargs.get("size", config.DEFAULT_IMAGE_SIZE)
        quality = kwargs.get("quality", config.DEFAULT_IMAGE_QUALITY)
        
        data = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "response_format": "b64_json"
        }
        
        # Remove quality parameter for dall-e-2 as it doesn't support it
        if model == "dall-e-2":
            data.pop("quality", None)
            # dall-e-2 only supports specific sizes
            if size not in ["256x256", "512x512", "1024x1024"]:
                data["size"] = "1024x1024"
        
        start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=config.IMAGE_GENERATION_TIMEOUT)
            ) as response:
                response_json = await response.json()
                
                if response.status != 200:
                    raise Exception(f"OpenAI API error: {response_json}")
                
                # Extract image data
                image_data = response_json["data"][0]
                b64_image = image_data["b64_json"]
                revised_prompt = image_data.get("revised_prompt", prompt)
                
                # Decode and save image
                image_bytes = base64.b64decode(b64_image)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{model}_{timestamp}.png"
                filepath = self.save_image(image_bytes, filename, "openai")
                
                end_time = datetime.now()
                generation_time = (end_time - start_time).total_seconds()
                
                return {
                    "success": True,
                    "provider": "openai",
                    "model": model,
                    "prompt": prompt,
                    "revised_prompt": revised_prompt,
                    "filepath": str(filepath),
                    "filename": filename,
                    "size": size,
                    "quality": quality,
                    "generation_time": generation_time,
                    "timestamp": start_time.isoformat(),
                    "api_response": response_json
                }
    
    async def _generate_stability_image(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image using Stability AI API"""
        if not config.STABILITY_API_KEY:
            raise ValueError("Stability AI API key not set")
        
        # Placeholder for Stability AI implementation
        # This would need to be implemented based on Stability AI's API documentation
        raise NotImplementedError("Stability AI integration not yet implemented")
    
    def save_image(self, image_data: bytes, filename: str, provider: str) -> Path:
        """Save image to filesystem"""
        provider_dir = self.output_dir / provider
        provider_dir.mkdir(exist_ok=True)
        
        filepath = provider_dir / filename
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return filepath
    
    def get_image_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from generation result"""
        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "prompt": result.get("prompt"),
                "timestamp": result.get("timestamp")
            }
        
        return {
            "success": True,
            "provider": result.get("provider"),
            "model": result.get("model"),
            "prompt": result.get("prompt"),
            "revised_prompt": result.get("revised_prompt"),
            "filepath": result.get("filepath"),
            "filename": result.get("filename"),
            "size": result.get("size"),
            "quality": result.get("quality"),
            "generation_time": result.get("generation_time"),
            "timestamp": result.get("timestamp")
        }
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers based on configuration"""
        providers = []
        
        if config.ENABLE_DALLE and config.DALLE_API_KEY:
            providers.append("openai")
        
        if config.ENABLE_STABILITY_AI and config.STABILITY_API_KEY:
            providers.append("stability")
        
        return providers
    
    def get_models_for_provider(self, provider: str) -> List[str]:
        """Get available models for a specific provider"""
        if provider == "openai":
            return config.DALLE_MODELS_TO_TEST if config.ENABLE_DALLE else []
        elif provider == "stability":
            return config.STABILITY_MODELS_TO_TEST if config.ENABLE_STABILITY_AI else []
        else:
            return []