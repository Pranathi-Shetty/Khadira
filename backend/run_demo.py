"""Run Khadira backend with the isolated simulation demo database."""
import os
import sys
from pathlib import Path
import uvicorn

# Ensure the backend directory is in python sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Force demo database URL
os.environ["DATABASE_URL"] = "sqlite:///./mill_demo.db"
os.environ["KHADIRA_DEMO"] = "1"

if __name__ == "__main__":
    print("=" * 64)
    print("  KHADIRA TEXTILE ERP - ISOLATED SIMULATION DEMO SERVER")
    print("=" * 64)
    print("  Database : backend/mill_demo.db")
    print("  Rolls    : 311 simulated fabric rolls across all QC stages")
    print("  Orders   : 24 sales orders exercising every lifecycle branch")
    print("  Normal DB: backend/mill.db is safe & untouched")
    print("  API Docs : http://localhost:8011/docs")
    print("=" * 64)
    uvicorn.run("app:app", host="127.0.0.1", port=8011, reload=True)
