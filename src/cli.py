import argparse
import sys
from pathlib import Path
from src.agent.gemini_client import EasySEOAgent

def main():
    parser = argparse.ArgumentParser(
        description="easySEO: Automated YouTube Video Optimization CLI using Gemini/Ollama"
    )
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="Path or name of the folder under workspace/raw_inputs/ containing the assets"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Optional external reference URL to fetch and analyze"
    )
    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="Skip visual image assets analysis (multimodal processing) for faster text-only inference"
    )

    args = parser.parse_args()

    print(f"[*] Initializing SEO agent execution for input folder: {args.folder}")
    
    agent = EasySEOAgent()
    try:
        agent.run(folder_name=args.folder, reference_url=args.url, no_visual=args.no_visual)
        print("[+] Optimization task completed successfully!")
    except Exception as e:
        print(f"[-] Error executing agent: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
