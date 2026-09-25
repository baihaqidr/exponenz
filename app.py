import os
import sys

# Set root path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api_server import run_server

if __name__ == "__main__":
    # Hugging Face Spaces uses port 7860 by default
    port = int(os.environ.get("PORT", 7860))
    print(f"[*] Starting Exponenz Web Dashboard on port {port}...")
    run_server(port)
