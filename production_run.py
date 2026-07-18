import os
import sys
from pathlib import Path

# Add dependency paths (must match manage.py setup)
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / 'TPM Portal'))
sys.path.append(str(BASE_DIR / 'CMC Portal'))
sys.path.append(str(BASE_DIR / 'Delays Portal'))
sys.path.append(str(BASE_DIR / 'EFMEA'))

try:
    from waitress import serve
except ImportError:
    print("[INFO] Installing waitress library for production serving...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "waitress"])
    from waitress import serve

from main_portal.wsgi import application

if __name__ == '__main__':
    port = 4321
    print(f"===================================================")
    print(f"[START] Starting Production WSGI Web Server")
    print(f"Server Address: http://0.0.0.0:{port}/ (Bind all interfaces)")
    print(f"Press Ctrl+C to stop the server.")
    print(f"===================================================")
    
    # Run the Waitress production server with 16 worker threads for high concurrency
    serve(application, host='0.0.0.0', port=port, threads=16)
