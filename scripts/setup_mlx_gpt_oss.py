#!/usr/bin/env python3
"""
Setup script for MLX-LM with gpt-oss model
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path


class MLXSetup:
    """MLX-LM setup and management."""
    
    def __init__(self):
        self.model_name = "halley-ai/gpt-oss-20b-MLX-5bit-gs32"
        self.server_port = 8080
        self.server_process = None
    
    def check_mlx_installation(self) -> bool:
        """Check if MLX-LM is installed."""
        try:
            result = subprocess.run(
                ["python", "-c", "import mlx_lm"], 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def install_mlx(self):
        """Install or update MLX-LM."""
        print("📦 Installing/updating MLX-LM...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade", "mlx-lm"
            ], check=True)
            print("✅ MLX-LM installed/updated successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install/update MLX-LM: {e}")
            return False
        return True

    def update_mlx_if_needed(self):
        """Update MLX-LM if version is too old for gpt-oss."""
        try:
            import mlx_lm
            version = getattr(mlx_lm, '__version__', 'unknown')
            print(f"Current MLX-LM version: {version}")

            # gpt-oss support was added in 0.26.3
            if version == 'unknown':
                print("⚠️  Cannot determine MLX-LM version, updating...")
                return self.install_mlx()

            # Parse version
            try:
                version_parts = [int(x) for x in version.split('.')]
                if len(version_parts) >= 3:
                    major, minor, patch = version_parts[:3]
                    # Check if version is >= 0.26.3
                    if (major, minor, patch) >= (0, 26, 3):
                        print("✅ MLX-LM version supports gpt-oss")
                        return True
                    else:
                        print(f"⚠️  MLX-LM {version} is too old for gpt-oss (need >= 0.26.3)")
                        print("Updating MLX-LM...")
                        return self.install_mlx()
            except ValueError:
                print("⚠️  Cannot parse MLX-LM version, updating...")
                return self.install_mlx()

        except ImportError:
            print("❌ MLX-LM not installed")
            return self.install_mlx()

        return False
    
    def check_mlx_version(self):
        """Check MLX-LM version and gpt-oss support."""
        print("🔍 Checking MLX-LM version and gpt-oss support...")
        try:
            import mlx_lm
            version = getattr(mlx_lm, '__version__', 'unknown')
            print(f"MLX-LM version: {version}")

            # Check if gpt_oss model is available
            try:
                import mlx_lm.models.gpt_oss
                print("✅ gpt-oss model support found")
                return True
            except ImportError:
                print("❌ gpt-oss model not supported in this MLX-LM version")
                print("You may need to update MLX-LM or use a different model")
                return False
        except ImportError:
            print("❌ MLX-LM not installed")
            return False

    def download_model(self):
        """Download the gpt-oss model."""
        print(f"📥 Checking model: {self.model_name}")

        # First check if gpt-oss is supported
        if not self.check_mlx_version():
            print("⚠️  Skipping model download due to compatibility issues")
            return False

        print("This may take a while (model is ~12GB)...")

        try:
            # Use mlx_lm to download the model
            subprocess.run([
                "python", "-c",
                f"from mlx_lm import load; load('{self.model_name}')"
            ], check=True)
            print("✅ Model downloaded successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to download model: {e}")
            print("Note: This is expected if the model is not available or needs different setup")
            return False
        return True

    def test_mlx_direct(self):
        """Test MLX-LM direct generation."""
        print("🧪 Testing MLX-LM direct generation...")
        try:
            result = subprocess.run([
                "python", "-m", "mlx_lm.generate",
                "--model", self.model_name,
                "--prompt", "Hello, how are you?",
                "--max-tokens", "10"
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                print("✅ MLX-LM direct generation test successful")
                print(f"Output: {result.stdout.strip()[:100]}...")
                return True
            else:
                print(f"❌ MLX-LM direct generation failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ MLX-LM direct generation error: {e}")
            return False
    
    def start_server(self):
        """Start MLX-LM server."""
        print(f"🚀 Starting MLX-LM server on port {self.server_port}...")
        
        try:
            # Start the server in background
            self.server_process = subprocess.Popen([
                "python", "-m", "mlx_lm.server",
                "--model", self.model_name,
                "--port", str(self.server_port),
                "--host", "0.0.0.0"
            ])
            
            # Wait a bit for server to start
            time.sleep(5)
            
            # Check if server is running
            if self.check_server_health():
                print(f"✅ MLX-LM server started successfully on port {self.server_port}")
                return True
            else:
                print("❌ Server failed to start properly")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def check_server_health(self) -> bool:
        """Check if MLX server is healthy."""
        try:
            response = requests.get(
                f"http://localhost:{self.server_port}/health",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            # Try alternative health check
            try:
                response = requests.get(
                    f"http://localhost:{self.server_port}/v1/models",
                    timeout=10
                )
                return response.status_code == 200
            except Exception:
                return False
    
    def stop_server(self):
        """Stop MLX-LM server."""
        if self.server_process:
            print("🛑 Stopping MLX-LM server...")
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ MLX-LM server stopped")
    
    def setup_ollama_gpt_oss(self):
        """Setup gpt-oss model in Ollama."""
        print("🦙 Setting up gpt-oss in Ollama...")

        # Check if Ollama is running
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("❌ Ollama is not running. Please start Ollama first.")
                return False
        except FileNotFoundError:
            print("❌ Ollama is not installed. Please install Ollama first.")
            return False

        # Check if gpt-oss is already available
        if "gpt-oss" in result.stdout:
            print("✅ gpt-oss model already available in Ollama")
            return True

        # Try to pull gpt-oss model
        try:
            print("📥 Pulling gpt-oss model in Ollama...")
            print("This may take a while (model is large)...")
            result = subprocess.run([
                "ollama", "pull", "gpt-oss"
            ], check=True)
            print("✅ gpt-oss model pulled successfully in Ollama")
            return True
        except subprocess.CalledProcessError:
            print("⚠️  gpt-oss model not available in Ollama registry")
            print("You may need to wait for the download to complete or use a different model")
            return False

    def suggest_alternative_models(self):
        """Suggest alternative models for testing."""
        print("\n💡 Alternative models for speed testing:")
        print("For Ollama:")
        print("  - llama3.3:8b (good for testing)")
        print("  - gemma3:27b (large model)")
        print("  - phi4-reasoning (reasoning model)")

        print("\nFor MLX-LM:")
        print("  - mlx-community/Llama-3.2-3B-Instruct-4bit")
        print("  - mlx-community/Mistral-7B-Instruct-v0.3-4bit")
        print("  - mlx-community/gemma-2-9b-it-4bit")

        print("\nYou can modify the speed test script to use these models instead.")
    
    def run_test(self):
        """Run a quick test of both systems."""
        print("\n🧪 Running quick test...")
        
        test_prompt = "Hello, how are you?"
        
        # Test Ollama
        print("Testing Ollama...")
        try:
            result = subprocess.run([
                "curl", "-X", "POST", "http://localhost:11434/api/generate",
                "-H", "Content-Type: application/json",
                "-d", f'{{"model": "gpt-oss", "prompt": "{test_prompt}", "stream": false}}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Ollama test successful")
            else:
                print("❌ Ollama test failed")
        except Exception as e:
            print(f"❌ Ollama test error: {e}")
        
        # Test MLX
        print("Testing MLX-LM...")
        try:
            result = subprocess.run([
                "curl", "-X", "POST", f"http://localhost:{self.server_port}/v1/chat/completions",
                "-H", "Content-Type: application/json",
                "-d", f'{{"model": "{self.model_name}", "messages": [{{"role": "user", "content": "{test_prompt}"}}], "max_tokens": 50}}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ MLX-LM test successful")
            else:
                print("❌ MLX-LM test failed")
        except Exception as e:
            print(f"❌ MLX-LM test error: {e}")


def main():
    """Main setup function."""
    print("🔧 MLX-LM + gpt-oss Setup")
    print("=" * 40)
    
    setup = MLXSetup()
    
    # Check and install/update MLX-LM
    if not setup.check_mlx_installation():
        if not setup.install_mlx():
            return 1
    else:
        print("✅ MLX-LM already installed")
        # Check if update is needed for gpt-oss support
        if not setup.update_mlx_if_needed():
            print("❌ Failed to update MLX-LM")
            return 1
    
    # Check MLX-LM version and gpt-oss support
    print("\n🔍 Checking MLX-LM compatibility...")
    mlx_compatible = setup.check_mlx_version()

    # Setup Ollama first (more likely to work)
    print("\n🦙 Setting up Ollama...")
    ollama_success = setup.setup_ollama_gpt_oss()

    if mlx_compatible:
        # Download model
        print("\n📥 Checking/downloading gpt-oss model...")
        if not setup.download_model():
            print("⚠️  Model download failed, but continuing...")

        # Test MLX direct generation
        print("\n🧪 Testing MLX-LM direct generation...")
        setup.test_mlx_direct()

        # Try to start MLX server
        print("\n🚀 Trying to start MLX-LM server...")
        server_started = setup.start_server()

        if server_started:
            print(f"\n✅ Setup complete!")
            print(f"MLX-LM server running on: http://localhost:{setup.server_port}")
            print("Ollama should be running on: http://localhost:11434")
            print("\nYou can now run the speed test:")
            print("python scripts/speed_test_128k_tokens.py")

            # Run quick test
            setup.run_test()

            print("\nPress Ctrl+C to stop the MLX server...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                setup.stop_server()
        else:
            print("\n⚠️  MLX server failed to start, but you can still use direct generation")
            print("You can run the speed test with direct MLX generation:")
            print("python scripts/speed_test_128k_tokens.py")

            # Run quick test with direct method
            setup.run_test()
    else:
        print("\n⚠️  MLX-LM gpt-oss not supported in current version")
        setup.suggest_alternative_models()

        if ollama_success:
            print("\n✅ Ollama setup successful!")
            print("You can run speed tests with Ollama only:")
            print("python scripts/speed_test_128k_tokens.py --ollama-only")
        else:
            print("\n❌ Neither MLX-LM nor Ollama setup was successful")
            print("Please check the requirements and try again")
    
    return 0


if __name__ == "__main__":
    exit(main())
