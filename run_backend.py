import os
import sys
import uvicorn

if __name__ == "__main__":
    print("[*] Booting Atlas Local API Backend...")
    # Add virtual environment detection or assume it's run via the venv
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    sys.path.insert(0, backend_dir)
    
    # Run the FastAPI app via uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
