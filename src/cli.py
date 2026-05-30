import argparse
import sys
# Importing settings hardens stdout/stderr to UTF-8 (errors="replace") at import
# time, before any non-ASCII log line can crash the run on Windows consoles.
import config.settings  # noqa: F401
from src.agent.gemini_client import EasySEOAgent


def main():
    parser = argparse.ArgumentParser(
        description="easySEO: Automated YouTube Video Optimization CLI using Gemini/Ollama"
    )
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="Path or name of the folder under workspace/raw_inputs/ containing the assets",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Optional external reference URL to fetch and analyze",
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

    args = parser.parse_args()

    print(f"[*] Initializing SEO agent execution for input folder: {args.folder}")

    agent = EasySEOAgent()
    try:
        agent.run(
            folder_name=args.folder,
            reference_url=args.url,
            no_visual=args.no_visual,
            model_override=args.model,
        )
        print("[+] Optimization task completed successfully!")
    except Exception as e:
        print(f"[-] Error executing agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
