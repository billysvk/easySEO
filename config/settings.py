import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
RAW_INPUTS_DIR = WORKSPACE_DIR / "raw_inputs"
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"

# Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = "gemini-2.5-flash"
