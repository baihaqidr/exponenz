import os
import sys
import webbrowser
import threading
import time

# Set UTF-8 encoding untuk Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Tambahkan path root agar import src berfungsi
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api_server import run_server

def open_browser(port=5000):
    # Hanya buka browser otomatis jika dijalankan di komputer lokal (bukan di Cloud/VPS)
    if not os.environ.get("PORT") and not os.environ.get("KOYEB_APP_NAME") and not os.environ.get("RENDER"):
        try:
            time.sleep(1.2)
            url = f"http://localhost:{port}"
            print(f"[*] Membuka Web Dashboard di browser Anda: {url}")
            webbrowser.open(url)
        except Exception:
            pass

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()
    run_server(PORT)

