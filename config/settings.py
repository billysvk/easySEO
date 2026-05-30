import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
RAW_INPUTS_DIR = WORKSPACE_DIR / "raw_inputs"
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"

# Load .env file manually if it exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    print("[*] Loading environment variables from .env file...")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = "gemini-2.0-flash"
