#!/usr/bin/env python3
"""
Quick script to update MLX-LM to support gpt-oss
"""

import subprocess
import sys

def check_current_version():
    """Check current MLX-LM version."""
    try:
        import mlx_lm
        version = getattr(mlx_lm, '__version__', 'unknown')
        print(f"Current MLX-LM version: {version}")
        return version
    except ImportError:
        print("❌ MLX-LM not installed")
        return None

def update_mlx():
    """Update MLX-LM to latest version."""
    print("📦 Updating MLX-LM to latest version...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "mlx-lm"
        ], check=True)
        print("✅ MLX-LM updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update MLX-LM: {e}")
        return False

def verify_gpt_oss_support():
    """Verify that gpt-oss is now supported."""
    try:
        import mlx_lm.models.gpt_oss
        print("✅ gpt-oss model support confirmed")
        return True
    except ImportError:
        print("❌ gpt-oss model still not supported")
        return False

def main():
    """Main function."""
    print("🔧 MLX-LM Update for gpt-oss Support")
    print("=" * 40)
    
    # Check current version
    current_version = check_current_version()
    
    if current_version is None:
        print("Please install MLX-LM first: pip install mlx-lm")
        return 1
    
    # Check if gpt-oss is already supported
    try:
        import mlx_lm.models.gpt_oss
        print("✅ gpt-oss already supported in current version")
        print("No update needed!")
        return 0
    except ImportError:
        print("⚠️  gpt-oss not supported in current version")
        print("gpt-oss support was added in MLX-LM 0.26.3")
        print("Current latest version is 0.28.3")
    
    # Update MLX-LM
    if update_mlx():
        # Verify the update worked
        new_version = check_current_version()
        print(f"Updated from {current_version} to {new_version}")
        
        if verify_gpt_oss_support():
            print("\n🎉 Success! MLX-LM now supports gpt-oss")
            print("You can now run:")
            print("  python scripts/setup_mlx_gpt_oss.py")
            print("  python scripts/speed_test_128k_tokens.py")
            return 0
        else:
            print("\n❌ Update failed - gpt-oss still not supported")
            print("You may need to restart your Python environment")
            return 1
    else:
        print("\n❌ Failed to update MLX-LM")
        return 1

if __name__ == "__main__":
    exit(main())
