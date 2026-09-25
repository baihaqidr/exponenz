import os
import sys

# Set root path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Handle ZeroGPU decorator if space has ZeroGPU enabled
try:
    import spaces
    @spaces.GPU(duration=5)
    def init_spaces():
        print("[*] Initialized on Hugging Face ZeroGPU environment.")
        return True
    init_spaces()
except Exception as e:
    print(f"[*] Standard CPU mode: {e}")

from src.api_server import run_server

if __name__ == "__main__":
    # Hugging Face Spaces uses port 7860 by default
    port = int(os.environ.get("PORT", 7860))
    print(f"[*] Starting Exponenz Web Dashboard on port {port}...")
    run_server(port)

