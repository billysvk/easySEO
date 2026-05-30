import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Console encoding hardening
# ---------------------------------------------------------------------------
# Windows consoles default to a legacy code page (cp1252 / "charmap") that
# cannot encode Greek text or emoji and raises UnicodeEncodeError mid-run.
# Reconfigure as early as possible (at import time) with errors="replace" so a
# stray non-ASCII character in a log line can never crash the pipeline.
def _harden_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_harden_console_encoding()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
RAW_INPUTS_DIR = WORKSPACE_DIR / "raw_inputs"
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"

# Single source of truth for the SEO expert persona & output blueprint.
SYSTEM_PROMPT_PATH = BASE_DIR / ".gemini.md"

# ---------------------------------------------------------------------------
# Load .env file manually if it exists
# ---------------------------------------------------------------------------
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
                # setdefault: an explicitly-exported environment variable wins
                # over the .env file (standard dotenv behavior), so CLI/session
                # overrides like `OLLAMA_MODEL=... uv run ...` actually take effect.
                os.environ.setdefault(key.strip(), val.strip())

# ---------------------------------------------------------------------------
# Provider Settings
# ---------------------------------------------------------------------------
# AI_PROVIDER can be "gemini" or "ollama"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

# Generation tuning (shared by both providers). SEO copywriting benefits from a
# little creativity, so we default slightly above the deterministic baseline.
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# ---------------------------------------------------------------------------
# Gemini Settings
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Overridable so users can upgrade to a stronger model (e.g. gemini-2.5-pro)
# without touching code. Default kept on the fast/cheap tier.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Ollama Settings
# ---------------------------------------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
# Local models default to a small context window (~4k). With a full system
# instruction + transcript + timeline the prompt easily overflows that, and the
# model silently never sees the tail of the input. Set this explicitly.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
