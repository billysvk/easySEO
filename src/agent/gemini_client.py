import os
import re
import httpx
from google import genai
from google.genai import types
from config.settings import (
    DEFAULT_MODEL,
    GEMINI_API_KEY,
    AI_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    LLM_TEMPERATURE,
    RAW_INPUTS_DIR,
)
from src.skills.image_processor import ImageProcessor
from src.skills.srt_parser import SRTParser
from src.skills.url_analyzer import URLAnalyzer
from src.skills.info_reader import InfoReader
from src.skills.file_writer import FileWriter
from src.skills.thumbnail_strategist import ThumbnailStrategist
from src.skills.prompt_builder import PromptBuilder
from src.skills.subtitle_downloader import SubtitleDownloader
from src.skills.competitor_analyzer import CompetitorAnalyzer
from src.skills.shorts_architect import ShortsArchitect
from src.skills.studio_stats_parser import StudioStatsParser


class EasySEOAgent:
    def __init__(self):
        # Initialize Gemini SDK client (used if AI_PROVIDER is "gemini")
        self.api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        # Instantiate skills
        self.image_processor = ImageProcessor()
        self.srt_parser = SRTParser()
        self.url_analyzer = URLAnalyzer()
        self.info_reader = InfoReader()
        self.file_writer = FileWriter()
        self.thumbnail_strategist = ThumbnailStrategist()
        self.prompt_builder = PromptBuilder()
        self.subtitle_downloader = SubtitleDownloader()
        self.competitor_analyzer = CompetitorAnalyzer()
        self.shorts_architect = ShortsArchitect()
        self.studio_stats_parser = StudioStatsParser()

    async def run(
        self,
        folder_name: str,
        reference_url: str = None,
        no_visual: bool = False,
        model_override: str = None,
    ) -> None:
        """
        Orchestrates skills to generate a comprehensive SEO Proposal.
        Supports both remote Gemini and local Ollama pipelines.
        """
        print(f"[*] Starting SEO Agent workflow for folder: '{folder_name}'...")
        print(f"[*] Active AI Provider: '{AI_PROVIDER.upper()}'")

        # 1. Read existing title/description/url/keyword from metadata file
        info_dict = self.info_reader.read_info(folder_name)
        title = info_dict.get("title", "")
        description = info_dict.get("description", "")
        video_url = info_dict.get("url", "")
        keyword = info_dict.get("keyword", "")

        # Automatically download subtitles if missing
        if video_url:
            await self.subtitle_downloader.download_subtitles(folder_name, video_url)

        # Scrape data from video URL if it exists
        scraped_metadata = None
        if video_url:
            print(f"[*] Found original Video URL in metadata: {video_url}. Initiating data scraping...")
            scraped_metadata = self.url_analyzer.scrape_video_metadata(video_url)
            if scraped_metadata.get("success"):
                # Save scraped metadata to a second markdown file inside the same folder
                scraped_file_path = RAW_INPUTS_DIR / folder_name / "scraped_metadata.md"
                print(f"[*] [Orchestrator] Saving scraped metadata to: {scraped_file_path}")
                try:
                    scraped_content = f"""# Scraped Video Metadata

**URL:** {video_url}
**Title:** {scraped_metadata.get('title')}
**Author/Channel:** {scraped_metadata.get('author')}
**Published Date:** {scraped_metadata.get('publish_date')}
**Live Views:** {scraped_metadata.get('views')}

**Description:**
{scraped_metadata.get('description')}
"""
                    with open(scraped_file_path, "w", encoding="utf-8") as f:
                        f.write(scraped_content)
                    print(f"[+] [Orchestrator] Scraped metadata successfully saved to {scraped_file_path.name}")
                except Exception as e:
                    print(f"[-] [Orchestrator] Error saving scraped metadata file: {e}")

                # Use scraped data as fallback if local metadata fields are empty
                if not title and scraped_metadata.get("title"):
                    title = scraped_metadata["title"]
                    print(f"[+] [Orchestrator] Populated missing Title from scraped URL: '{title}'")
                if not description and scraped_metadata.get("description"):
                    description = scraped_metadata["description"]
                    print("[+] [Orchestrator] Populated missing Description from scraped URL.")
            else:
                print(f"[!] [Orchestrator] Warning: Could not scrape live video URL: {scraped_metadata.get('error', 'unknown error')}")

        # Automatically discover and save focus keyword if missing
        if not keyword or not keyword.strip():
            print("[*] [Orchestrator] Focus keyword is missing. Initiating automatic keyword discovery...")
            discovered_keyword = ""
            
            # Method A: Try using scraped tags/keywords list and gather as many as possible
            if scraped_metadata and scraped_metadata.get("keywords"):
                scraped_keywords = scraped_metadata["keywords"]
                if scraped_keywords:
                    cleaned_keywords = []
                    for kw in scraped_keywords:
                        kw_cleaned = kw.strip()
                        if kw_cleaned and kw_cleaned not in cleaned_keywords:
                            cleaned_keywords.append(kw_cleaned)
                    
                    if cleaned_keywords:
                        discovered_keyword = ", ".join(cleaned_keywords)
            
            # Method B: Fallback to title parsing
            if not discovered_keyword and title:
                # Clean up title: remove emojis, hashtags
                clean_title = re.sub(r'#\S+', '', title)
                clean_title = re.sub(r'[^\w\s|:\-—]', '', clean_title)
                
                # Split by separators
                parts = re.split(r'[|:\-—]', clean_title)
                if parts:
                    candidate = parts[0].strip()
                    candidate = re.sub(r'\s+', ' ', candidate).strip()
                    if candidate:
                        title_lower = title.lower()
                        if "travel" in title_lower or "vlog" in title_lower or "ταξίδι" in title_lower or "ταξιδι" in title_lower:
                            discovered_keyword = f"{candidate} travel vlog"
                        else:
                            discovered_keyword = candidate
                            
            # Ultimate fallback
            if not discovered_keyword:
                discovered_keyword = "travel vlog"
                
            keyword = discovered_keyword.strip()
            
            # Save it back to input file
            meta_file_path = RAW_INPUTS_DIR / folder_name / "input.md"
            if not meta_file_path.exists():
                if (RAW_INPUTS_DIR / folder_name / "info.txt").exists():
                    meta_file_path = RAW_INPUTS_DIR / folder_name / "info.txt"
            
            self._update_keyword_in_file(meta_file_path, keyword)

        # Construct final info text block to pass into the prompt
        info_parts = []
        if title:
            info_parts.append(f"Title Draft: {title}")
        if description:
            info_parts.append(f"Description Draft:\n{description}")
        if video_url:
            info_parts.append(f"Original Video URL: {video_url}")
            if scraped_metadata and scraped_metadata.get("success"):
                info_parts.append(f"Live Video Title (Scraped): {scraped_metadata.get('title')}")
                info_parts.append(f"Live Video Author: {scraped_metadata.get('author')}")
                info_parts.append(f"Live Video Published Date: {scraped_metadata.get('publish_date')}")
                info_parts.append(f"Live Video Views: {scraped_metadata.get('views')}")
                info_parts.append(f"Live Video Description (Scraped):\n{scraped_metadata.get('description')}")
        
        info_text = "\n\n".join(info_parts) if info_parts else "Title Draft: None\nDescription Draft: None"

        # 2. Parse subtitles SRT/SBV -> clean text + timestamped timeline
        srt_result = self.srt_parser.parse(folder_name)
        if srt_result.get("truncated"):
            print("[!] Transcript was long and has been truncated for the prompt.")
        transcript_block = self._compose_transcript(srt_result)

        # 3. Process visual/retention charts (returns parts & base64)
        visual_images = []
        if not no_visual:
            visual_images = self.image_processor.process_charts(folder_name)
        else:
            print("[*] Skipping visual image analysis (--no-visual flag active).")

        # 4. Fetch/parse reference URL if provided and run Competitor Gap Analysis
        reference_data_parts = []
        if reference_url:
            ref_data = self.url_analyzer.analyze_url(reference_url)
            reference_data_parts.append(ref_data)
        
        if keyword:
            # Use the first keyword (before the first comma) for the search query to ensure high-relevance YouTube search results
            search_query = keyword.split(",")[0].strip() if "," in keyword else keyword
            competitor_data = await self.competitor_analyzer.analyze_competitors(search_query)
            reference_data_parts.append(f"--- COMPETITOR SEARCH & KEYWORD GAP ANALYSIS (Keyword: '{search_query}') ---\n{competitor_data}")
            
        reference_data = "\n\n".join(reference_data_parts) if reference_data_parts else ""

        # 5. Load thumbnail visual strategist & shorts architect guides
        thumbnail_guides = self.thumbnail_strategist.get_strategy_placeholder()
        shorts_guides = self.shorts_architect.get_shorts_guidelines()
        visual_guides = f"{thumbnail_guides}\n\n{shorts_guides}"

        print("[*] Consolidating inputs & constructing payload...")

        csv_diagnostics = self.studio_stats_parser.parse_retention_csv(folder_name)
        visual_summary = (
            f"Attached {len(visual_images)} YouTube Studio analytics screenshots / "
            "retention charts. Analyze them for intro drop-offs, valleys and spikes."
            if visual_images
            else "No visual analytics screenshots provided (text-only analysis)."
        )
        visual_summary += f"\n\n{csv_diagnostics}"

        # Build the expert prompt from .gemini.md (single source of truth).
        system_instruction = self.prompt_builder.get_system_instruction()
        prompt = self.prompt_builder.build_prompt(
            info_text=info_text,
            transcript_text=transcript_block,
            visual_data=visual_summary,
            reference_data=reference_data,
            thumbnail_guides=visual_guides,
        )

        proposal_content = ""

        # --- LOCAL OLLAMA PROVIDER PIPELINE ---
        if AI_PROVIDER == "ollama":
            print(f"[*] Calling local Ollama server at {OLLAMA_URL} using model '{OLLAMA_MODEL}'...")
            proposal_content = self._call_ollama(prompt, system_instruction, visual_images, info_text)

        # --- REMOTE GEMINI PROVIDER PIPELINE ---
        else:
            proposal_content = self._call_gemini(
                prompt, system_instruction, visual_images, info_text, model_override
            )

        # Output file
        self.file_writer.write_proposal(folder_name, proposal_content)
        print("[+] Execution finished successfully!")

    # ------------------------------------------------------------------ #
    # Provider calls
    # ------------------------------------------------------------------ #
    def _call_gemini(self, prompt, system_instruction, visual_images, info_data, model_override):
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set or invalid. Cannot generate proposal without API Key.")

        model = model_override or DEFAULT_MODEL
        print(f"[*] Calling Gemini Model '{model}' with multimodal inputs...")
        
        gemini_parts = [img["part"] for img in visual_images]
        contents = [prompt] + gemini_parts

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=LLM_TEMPERATURE,
            ),
        )
        return self._strip_reasoning(response.text)

    def _call_ollama(self, prompt, system_instruction, visual_images, info_data):
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            # Disable chain-of-thought for "thinking" models (qwen3, etc.)
            # so <think> traces don't pollute the proposal.
            "think": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                # Critical: without this local models default to ~4k ctx and
                # silently drop the tail of a long expert prompt.
                "num_ctx": OLLAMA_NUM_CTX,
            },
        }

        base64_images = [img["base64"] for img in visual_images]
        if base64_images:
            payload["images"] = base64_images
            print(f"[*] Attaching {len(base64_images)} image(s) to local Ollama multimodal request...")
            print("[!] Note: images are only analyzed if OLLAMA_MODEL is a vision model.")

        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=600.0,  # Local inference of long prompts can be slow.
        )
        response.raise_for_status()
        return self._strip_reasoning(response.json().get("response", ""))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _compose_transcript(srt_result: dict) -> str:
        """Combines the clean speech stream with the timestamped timeline so the
        model can both extract keywords and author chapters at real times."""
        clean = srt_result.get("clean_text", "")
        timeline = srt_result.get("timeline", "")
        if not timeline:
            return clean
        return (
            f"{clean}\n\n"
            "[TIMELINE — use these timestamps to build accurate chapters]\n"
            f"{timeline}"
        )

    @staticmethod
    def _strip_reasoning(text: str) -> str:
        """Removes <think>...</think> reasoning blocks emitted by some models."""
        if not text:
            return text
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _get_fallback_proposal(self, info_data: str, prompt_used: str) -> str:
        return f"""# SEO Proposal (Mocked - API Key not set or failed)

This proposal was generated as a mockup because no valid Gemini API key was provided or the API request failed.

## Original Info
{info_data}

## Proposed High-CTR Titles
1. [MODERN HOOK] {info_data.splitlines()[0] if info_data else 'Amazing Vlog!'} (2026 Trend)
2. This Changed Everything! - (Retention Strategy Applied)
3. 10x Your Views with this Simple Trick!

## Optimized Description Outline
- **0:00 - Intro Hook** (matches visual suggestions)
- **1:30 - Deep Dive** (based on SRT transcript)
- **5:00 - Outro Call to Action**

## Debug Prompt Used
```text
{prompt_used}
```
"""

    def _update_keyword_in_file(self, meta_file_path, new_keyword: str) -> None:
        try:
            content = ""
            if meta_file_path.exists():
                with open(meta_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            # Check if keyword already exists in file
            keyword_line_pattern = re.compile(r'^#*\s*\*?(?:focus\s*keyword|keyword)\*?\s*:\s*(.*)', re.IGNORECASE | re.MULTILINE)
            if keyword_line_pattern.search(content):
                # Replace it
                updated_content = keyword_line_pattern.sub(f"keyword: {new_keyword}", content)
            else:
                # Append it
                updated_content = content.rstrip() + f"\nkeyword: {new_keyword}\n"
            
            with open(meta_file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"[+] [Orchestrator] Automatically filled and saved focus keyword to {meta_file_path.name}: '{new_keyword}'")
        except Exception as e:
            print(f"[-] [Orchestrator] Error updating keyword in metadata file: {e}")
