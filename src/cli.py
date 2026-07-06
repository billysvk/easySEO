import argparse
import asyncio
import shutil
import subprocess
import sys
import time

import httpx

# Importing settings hardens stdout/stderr to UTF-8 (errors="replace") at import
# time, before any non-ASCII log line can crash the run on Windows consoles.
from config.settings import (
    AI_PROVIDER,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    DEFAULT_MODEL,
)
from src.agent.gemini_client import EasySEOAgent

_BANNER = r"""
============================================================
   easySEO  VIRAL ENGINE  v2.0
   URL in  ->  full viral optimization package out
============================================================
"""

# Models that can't generate text proposals — hidden from the picker.
_NON_CHAT_MARKERS = ("embed",)


def _list_ollama_models() -> list:
    """Returns installed Ollama model names, or [] if the server is down."""
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3.0)
        response.raise_for_status()
        models = [m.get("name", "") for m in response.json().get("models", [])]
        return [m for m in models if m and not any(x in m for x in _NON_CHAT_MARKERS)]
    except Exception:
        return []


def _ensure_ollama_running() -> list:
    """Lists Ollama models, auto-starting the server if needed."""
    models = _list_ollama_models()
    if models:
        return models
    print("[*] Ollama server is not responding. Attempting to start it...")
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except Exception as e:
        print(f"[!] Could not auto-start Ollama: {e}")
        return []
    for _ in range(10):
        time.sleep(1)
        models = _list_ollama_models()
        if models:
            print("[+] Ollama server started.")
            return models
    return []


def _ask(prompt: str, default: str) -> str:
    """input() with a default on empty answer / non-interactive stdin."""
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return answer or default


def interactive_setup(args) -> tuple:
    """Startup menu: choose what runs this session.
    Returns (provider, model, dry_run). Skipped when flags already decide."""
    if args.provider or args.dry_run or args.model or not sys.stdin.isatty():
        return args.provider, args.model, args.dry_run

    print("Τι θέλεις να τρέξει;")
    default_choice = {"ollama": "1", "claude": "2"}.get(AI_PROVIDER, "3")
    claude_ready = bool(ANTHROPIC_API_KEY) or bool(shutil.which("claude"))
    claude_note = (
        "μέσω API key" if ANTHROPIC_API_KEY
        else "μέσω Claude Code CLI / συνδρομής σου" if claude_ready
        else "ΔΕΝ βρέθηκε ούτε ANTHROPIC_API_KEY ούτε claude CLI"
    )
    gemini_note = "έτοιμο" if GEMINI_API_KEY else "ΛΕΙΠΕΙ το GEMINI_API_KEY στο .env"
    print(f"  [1] Ollama  — τοπικό AI, δωρεάν, χωρίς internet για το LLM")
    print(f"  [2] Claude  — κορυφαία ποιότητα ({claude_note})")
    print(f"  [3] Gemini  — cloud AI ({gemini_note})")
    print(f"  [4] Dry-run — μόνο συλλογή δεδομένων, χωρίς AI (γράφει το INTELLIGENCE_PROMPT.md)")
    choice = _ask(f"Επιλογή [{default_choice}]: ", default_choice)

    if choice == "4":
        return None, None, True

    if choice == "2":
        if not claude_ready:
            print("[!] Δεν βρέθηκε πρόσβαση σε Claude — συνεχίζω, αλλά το LLM call θα αποτύχει.")
        if ANTHROPIC_API_KEY:
            model = _ask(f"Μοντέλο Claude [{CLAUDE_MODEL}]: ", CLAUDE_MODEL)
        else:
            # CLI path: empty = the user's default Claude Code model.
            model = _ask("Μοντέλο Claude [Enter = το default μοντέλο σου στο Claude Code]: ", "")
            model = model or None
        return "claude", model, False

    if choice == "3":
        if not GEMINI_API_KEY:
            print("[!] Δεν υπάρχει GEMINI_API_KEY στο .env — συνεχίζω, αλλά το LLM call θα αποτύχει.")
        model = _ask(f"Μοντέλο Gemini [{DEFAULT_MODEL}]: ", DEFAULT_MODEL)
        return "gemini", model, False

    # --- Ollama ---
    models = _ensure_ollama_running()
    if not models:
        print("[!] Το Ollama δεν είναι διαθέσιμο. Πέφτω σε dry-run (μόνο συλλογή δεδομένων).")
        return None, None, True

    default_model = OLLAMA_MODEL if OLLAMA_MODEL in models else models[0]
    print("Διαθέσιμα τοπικά μοντέλα:")
    for i, name in enumerate(models, 1):
        marker = "  <- default" if name == default_model else ""
        print(f"  [{i}] {name}{marker}")
    raw = _ask(f"Μοντέλο [Enter = {default_model}]: ", default_model)
    if raw.isdigit() and 1 <= int(raw) <= len(models):
        model = models[int(raw) - 1]
    elif raw in models:
        model = raw
    else:
        model = default_model
    return "ollama", model, False


def main():
    parser = argparse.ArgumentParser(
        description=(
            "easySEO Viral Engine: paste a YouTube URL (or a workspace folder name) "
            "and get a complete viral optimization package - titles, description, "
            "tags, thumbnails, Shorts plan, launch checklist and revival strategy."
        )
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=str,
        help="A YouTube video URL (recommended) or a folder name under workspace/raw_inputs/",
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="(Legacy) folder under workspace/raw_inputs/ containing the assets",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Optional external reference URL (blog/article/competitor page) to analyze",
    )
    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="Skip visual image analysis (multimodal) for faster text-only inference",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["gemini", "ollama", "claude"],
        help="AI provider for this run (skips the interactive menu)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model override for this run (Gemini or Ollama model name; skips the menu)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Gather ALL intelligence and save the full prompt without calling the LLM (no API key needed)",
    )

    args = parser.parse_args()

    target = args.target or args.folder
    if not target:
        parser.error("Provide a YouTube URL (positional) or --folder <name>.")

    print(_BANNER)

    provider, model, dry_run = interactive_setup(args)

    folder_name, _ = EasySEOAgent.resolve_target(target)
    print(f"[*] Initializing Viral Engine for: {folder_name}")

    agent = EasySEOAgent()
    try:
        asyncio.run(
            agent.run(
                folder_name=folder_name,
                reference_url=args.url,
                no_visual=args.no_visual,
                model_override=model,
                dry_run=dry_run,
                provider=provider,
            )
        )
        print("[+] Optimization task completed successfully!")
    except Exception as e:
        print(f"[-] Error executing agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
