# easySEO 🚀

`easySEO` is a next-generation, production-grade **multimodal AI YouTube SEO Consultant & Retention Architect** built in Python. Designed to run seamlessly as a lightweight CLI tool, it processes raw video assets—such as spoken SRT transcripts, current metadata drafts, YouTube Studio analytics screenshots, retention charts, and reference competitor URLs—to generate high-conversion, algorithm-optimized YouTube packaging proposals for 2026 standards.

---

## 📂 Project Architecture

The codebase strictly follows a highly modular, decoupled architecture, separating orchestration logic from individual functional skills:

```text
easy_seo/
│
├── .venv/                      # Managed via 'uv'
├── pyproject.toml              # Dependencies & Python configuration
├── uv.lock                     # Strict lockfile
├── README.md                   # Complete documentation
├── .gemini.md                  # System prompts & SEO proposal blueprints
│
├── config/
│   └── settings.py             # Configuration for paths and Gemini API models
│
├── src/
│   ├── __init__.py
│   ├── cli.py                  # CLI argument parser and entry point
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   └── gemini_client.py    # Main Orchestrator compiling multimodal inputs
│   │
│   └── skills/                 # Isolated single-purpose capabilities (Tools)
│       ├── __init__.py
│       ├── image_processor.py  # Loads screenshots and converts them to API Multimodal Parts
│       ├── srt_parser.py       # Cleans SRT subtitle headers for speech transcript extraction
│       ├── url_analyzer.py     # Scrapes external articles or competitor content using HTTPX/BS4
│       ├── info_reader.py      # Ingests current titles/descriptions from info.txt
│       ├── file_writer.py      # Formats and saves the final SEO_PROPOSAL.md
│       └── thumbnail_strategist.py # Generates overlay layout strategies and detailed AI generator prompts
│
└── workspace/
    ├── raw_inputs/             # Folder for placing raw video assets (directories per video)
    └── outputs/                # Formatted markdown output target folder
```

---

## ⚡ Core Skills & Capabilities

### 1. Multimodal Stat Analysis (`ImageProcessor`)
Unlike traditional text-only tools, `easySEO` reads actual binary image assets (screenshots of **YouTube Studio Analytics** and **Audience Retention Curves**). It loads these files and automatically maps them to **Gemini API Multimodal Parts**, allowing the AI to physically analyze spikes, flatlines, or sudden intro drop-offs.

### 2. Video Transcript Understanding (`SRTParser`)
It ingests standard `.srt` subtitle files, sanitizes timing headers, and outputs clean speech text. The AI uses this data to map the video's actual semantic value, extract timestamps, and align titles/descriptions with spoken keywords for semantic indexing.

### 3. URL Competitor Scraping (`URLAnalyzer`)
Accepts an optional URL argument. It leverages `httpx` and `beautifulsoup4` to scrape competitor titles, tags, and articles, cross-referencing industry standards directly to enhance descriptions.

### 4. Creative Visual Director (`ThumbnailStrategist`)
Instead of wasting compute attempting to render inaccurate images, this skill acts as a Creative Director. It defines the optimal layout composition (Rule of Thirds, focus subjects, color contrast) and provides **2 ready-to-use Midjourney/DALL-E prompts** to render high-CTR background images, complete with exact copy overlay recommendations.

---

## ⚙️ Installation & Environment Setup

This project uses [uv](https://github.com/astral-sh/uv), an extremely fast Python package installer and resolver.

### 1. Clone the Repository
```bash
git clone https://github.com/billysvk/easySEO.git
cd easySEO/easy_seo
```

### 2. Sync the Environment
Run the following command to automatically create a virtual environment and install all locked dependencies (`google-genai`, `pillow`, `httpx`, `beautifulsoup4`):
```bash
uv sync
```

### 3. Configure Gemini API Key
Export your official Gemini API Key to your environment variables:
```bash
# On Windows PowerShell
$env:GEMINI_API_KEY="your-api-key-here"

# On Linux/macOS
export GEMINI_API_KEY="your-api-key-here"
```

---

## 🚀 How to Run the Tool

### 1. Prepare Video Assets
Create a folder inside `workspace/raw_inputs/` (e.g., `my_vlog/`) and place the files:
- **`info.txt`**: Contains your tentative title and draft description.
- **`subtitles.srt`**: The raw SRT subtitle file of your video speech.
- **`stats_chart.png`** (Optional): A screenshot of your retention curve or YouTube Studio stats.

### 2. Execute CLI
Run the execution command:
```bash
# Basic run
uv run python -m src.cli --folder my_vlog

# Run with an external reference URL for competitor mapping
uv run python -m src.cli --folder my_vlog --url "https://competitor-article.com/video-topic"
```

### 3. Retrieve Proposal
The optimized package will be written directly inside:
`workspace/outputs/my_vlog_SEO_PROPOSAL.md`
