#!/usr/bin/env python3
"""
Test script to verify gpt-oss setup and functionality
"""

import subprocess
import sys
import os
from pathlib import Path

def test_mlx_installation():
    """Test if MLX-LM is properly installed."""
    print("🔍 Testing MLX-LM installation...")
    try:
        import mlx_lm
        print(f"✅ MLX-LM installed: {mlx_lm.__version__}")
        return True
    except ImportError:
        print("❌ MLX-LM not installed")
        return False

def test_gpt_oss_model_support():
    """Test if gpt-oss model is supported in MLX-LM."""
    print("🔍 Testing gpt-oss model support...")
    try:
        # Check if gpt_oss.py exists in MLX-LM models
        import mlx_lm.models.gpt_oss
        print("✅ gpt-oss model support found in MLX-LM")
        return True
    except ImportError:
        print("❌ gpt-oss model not supported in MLX-LM")
        return False

def test_model_loading():
    """Test loading a gpt-oss model."""
    print("🔍 Testing model loading...")
    model_name = "halley-ai/gpt-oss-20b-MLX-5bit-gs32"
    
    try:
        from mlx_lm import load
        print(f"Attempting to load: {model_name}")
        model, tokenizer = load(model_name)
        print("✅ Model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        print("Note: This is expected if the model is not downloaded yet")
        return False

def test_ollama_availability():
    """Test if Ollama is available."""
    print("🔍 Testing Ollama availability...")
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Ollama is running")
            print("Available models:")
            for line in result.stdout.split('\n')[:5]:  # Show first 5 lines
                if line.strip():
                    print(f"  {line}")
            return True
        else:
            print("❌ Ollama command failed")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Ollama command timed out")
        return False

def test_token_counting():
    """Test token counting functionality."""
    print("🔍 Testing token counting...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from speed_test_128k_tokens import TokenCounter
        
        test_text = "This is a test sentence for token counting."
        token_count = TokenCounter.count_tokens(test_text)
        print(f"✅ Token counting works: '{test_text}' = {token_count} tokens")
        return True
    except Exception as e:
        print(f"❌ Token counting failed: {e}")
        return False

def test_content_generation():
    """Test 128k content generation."""
    print("🔍 Testing 128k content generation...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from speed_test_128k_tokens import TokenCounter
        
        # Test with a small file first
        test_content = "This is test content. " * 100  # ~400 tokens
        
        # Simulate the generation process
        base_tokens = TokenCounter.count_tokens(test_content)
        target_tokens = 1000  # Small target for testing
        repetitions = max(1, target_tokens // base_tokens + 1)
        
        content_parts = []
        for i in range(repetitions):
            content_parts.append(f"\n\n--- ITERATION {i+1} ---\n\n")
            content_parts.append(test_content)
            
            current_content = ''.join(content_parts)
            if TokenCounter.count_tokens(current_content) >= target_tokens:
                break
        
        final_content = ''.join(content_parts)
        actual_tokens = TokenCounter.count_tokens(final_content)
        
        print(f"✅ Content generation works: Generated {actual_tokens} tokens (target: {target_tokens})")
        return True
    except Exception as e:
        print(f"❌ Content generation failed: {e}")
        return False

def test_archive_file():
    """Test if the Simon Willison archive file exists."""
    print("🔍 Testing archive file availability...")
    archive_file = Path("archive/simonwilison-llm-latest-30.md")
    
    if archive_file.exists():
        size = archive_file.stat().st_size
        print(f"✅ Archive file found: {archive_file} ({size} bytes)")
        
        # Test reading the file
        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sys.path.insert(0, str(Path(__file__).parent))
            from speed_test_128k_tokens import TokenCounter
            tokens = TokenCounter.count_tokens(content)
            print(f"✅ Archive file readable: ~{tokens} tokens")
            return True
        except Exception as e:
            print(f"❌ Failed to read archive file: {e}")
            return False
    else:
        print(f"❌ Archive file not found: {archive_file}")
        return False

def main():
    """Run all tests."""
    print("🧪 GPT-OSS Setup Test Suite")
    print("=" * 50)
    
    tests = [
        ("MLX-LM Installation", test_mlx_installation),
        ("GPT-OSS Model Support", test_gpt_oss_model_support),
        ("Ollama Availability", test_ollama_availability),
        ("Token Counting", test_token_counting),
        ("Content Generation", test_content_generation),
        ("Archive File", test_archive_file),
        ("Model Loading", test_model_loading),  # This one last as it may take time
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! You're ready to run speed tests.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\nNext steps:")
        if not results.get("MLX-LM Installation", False):
            print("- Install MLX-LM: pip install mlx-lm")
        if not results.get("Ollama Availability", False):
            print("- Install and start Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
        if not results.get("Archive File", False):
            print("- Ensure archive/simonwilison-llm-latest-30.md exists")
        return 1

if __name__ == "__main__":
    exit(main())
