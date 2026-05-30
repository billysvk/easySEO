import os
import httpx
from google import genai
from config.settings import (
    DEFAULT_MODEL,
    GEMINI_API_KEY,
    AI_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL
)
from src.skills.image_processor import ImageProcessor
from src.skills.srt_parser import SRTParser
from src.skills.url_analyzer import URLAnalyzer
from src.skills.info_reader import InfoReader
from src.skills.file_writer import FileWriter
from src.skills.thumbnail_strategist import ThumbnailStrategist

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

    def run(self, folder_name: str, reference_url: str = None) -> None:
        """
        Orchestrates skills to generate a comprehensive SEO Proposal.
        Supports both remote Gemini and local Ollama pipelines.
        """
        print(f"[*] Starting SEO Agent workflow for folder: '{folder_name}'...")
        print(f"[*] Active AI Provider: '{AI_PROVIDER.upper()}'")
        
        # 1. Read existing title/description info.txt
        info_data = self.info_reader.read_info(folder_name)
        
        # 2. Parse subtitles SRT/SBV
        srt_data = self.srt_parser.parse_srt(folder_name)
        
        # 3. Process visual/retention charts (returns structured lists with parts & base64)
        visual_images = self.image_processor.process_charts(folder_name)
        
        # 4. Fetch/parse reference URL if provided
        reference_data = ""
        if reference_url:
            reference_data = self.url_analyzer.analyze_url(reference_url)
            
        # 5. Load thumbnail visual strategist guides
        thumbnail_guides = self.thumbnail_strategist.get_strategy_placeholder()
            
        print("[*] Consolidating inputs & constructing payload...")
        
        visual_summary = (
            f"Attached {len(visual_images)} YouTube Studio analytics screenshots / retention charts." 
            if visual_images else "No visual analytics screenshots provided."
        )
        
        # Construct dynamic prompt
        prompt = f"""
Analyze the following inputs for the YouTube video:
1. Current Title/Description:
{info_data}

2. Cleaned Transcript:
{srt_data}

3. Key Visual/Retention Data:
{visual_summary}

4. External Reference Materials:
{reference_data}

5. Thumbnail Strategy Guidelines to follow:
{thumbnail_guides}

Please generate an SEO Proposal containing:
- 3 high-CTR title variations (matching modern 2026 YouTube algorithm trends)
- A compelling, chapter-based description structure
- Relevant tags, key highlights, and visual hook suggestions.
- A highly detailed Thumbnail Blueprint: Including visual layout guidelines, exact 3-word text overlays, and 2 ready-to-use image generator prompts (e.g., Midjourney).
"""

        proposal_content = ""
        
        # --- LOCAL OLLAMA PROVIDER PIPELINE ---
        if AI_PROVIDER == "ollama":
            print(f"[*] Calling local Ollama server at {OLLAMA_URL} using model '{OLLAMA_MODEL}'...")
            try:
                # Compile base64 strings of visual images for Ollama multimodal support
                base64_images = [img["base64"] for img in visual_images]
                
                # Payload matching Ollama's native API
                payload = {
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }
                if base64_images:
                    payload["images"] = base64_images
                    print(f"[*] Attaching {len(base64_images)} image(s) to local Ollama multimodal request...")
                
                # Make HTTP call to local daemon
                response = httpx.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=90.0  # Local models can take a moment to compute
                )
                response.raise_for_status()
                proposal_content = response.json().get("response", "")
                
            except Exception as e:
                print(f"[-] Local Ollama call failed: {e}. Falling back to boilerplate text.")
                proposal_content = self._get_fallback_proposal(info_data, prompt)
                
        # --- REMOTE GEMINI PROVIDER PIPELINE ---
        else:
            if self.client:
                print(f"[*] Calling Gemini Model '{DEFAULT_MODEL}' with multimodal inputs...")
                try:
                    # Extract Gemini Part objects from visual images
                    gemini_parts = [img["part"] for img in visual_images]
                    contents = [prompt] + gemini_parts
                    
                    response = self.client.models.generate_content(
                        model=DEFAULT_MODEL,
                        contents=contents,
                    )
                    proposal_content = response.text
                except Exception as e:
                    print(f"[-] Gemini API call failed: {e}. Falling back to boilerplate text.")
                    proposal_content = self._get_fallback_proposal(info_data, prompt)
            else:
                print("[!] No GEMINI_API_KEY found. Generating draft proposal using local rules.")
                proposal_content = self._get_fallback_proposal(info_data, prompt)

        # 5. Output file
        self.file_writer.write_proposal(folder_name, proposal_content)
        print("[+] Execution finished successfully!")

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
