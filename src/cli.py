import argparse
import asyncio
import sys

# Importing settings hardens stdout/stderr to UTF-8 (errors="replace") at import
# time, before any non-ASCII log line can crash the run on Windows consoles.
import config.settings  # noqa: F401
from src.agent.gemini_client import EasySEOAgent

_BANNER = r"""
============================================================
   easySEO  VIRAL ENGINE  v2.0
   URL in  ->  full viral optimization package out
============================================================
"""


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
        "--model",
        type=str,
        help="Override the Gemini model for this run (e.g. gemini-2.5-pro)",
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

    folder_name, _ = EasySEOAgent.resolve_target(target)
    print(f"[*] Initializing Viral Engine for: {folder_name}")

    agent = EasySEOAgent()
    try:
        asyncio.run(
            agent.run(
                folder_name=folder_name,
                reference_url=args.url,
                no_visual=args.no_visual,
                model_override=args.model,
                dry_run=args.dry_run,
            )
        )
        print("[+] Optimization task completed successfully!")
    except Exception as e:
        print(f"[-] Error executing agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
