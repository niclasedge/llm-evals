#!/usr/bin/env python3
"""
Stop MLX server processes
"""

import subprocess
import sys

def stop_mlx_servers():
    """Stop all MLX server processes."""
    print("🛑 Stopping MLX server processes...")
    
    try:
        # Find MLX server processes
        result = subprocess.run([
            "pgrep", "-f", "mlx_lm.server"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Killing MLX server process {pid}")
                    subprocess.run(["kill", pid])
            print("✅ MLX server processes stopped")
        else:
            print("ℹ️  No MLX server processes found")
            
    except Exception as e:
        print(f"❌ Error stopping MLX servers: {e}")

def main():
    stop_mlx_servers()

if __name__ == "__main__":
    main()
