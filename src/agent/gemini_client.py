import os
from google import genai
from config.settings import DEFAULT_MODEL, GEMINI_API_KEY
from src.skills.image_processor import ImageProcessor
from src.skills.srt_parser import SRTParser
from src.skills.url_analyzer import URLAnalyzer
from src.skills.info_reader import InfoReader
from src.skills.file_writer import FileWriter

class EasySEOAgent:
    def __init__(self):
        # Initialize the official Gemini SDK client
        self.api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # Instantiate skills
        self.image_processor = ImageProcessor()
        self.srt_parser = SRTParser()
        self.url_analyzer = URLAnalyzer()
        self.info_reader = InfoReader()
        self.file_writer = FileWriter()

    def run(self, folder_name: str, reference_url: str = None) -> None:
        """
        Orchestrates skills to generate a comprehensive SEO Proposal using Gemini.
        """
        print(f"[*] Starting SEO Agent workflow for folder: '{folder_name}'...")
        
        # 1. Read existing title/description info.txt
        info_data = self.info_reader.read_info(folder_name)
        
        # 2. Parse subtitles SRT
        srt_data = self.srt_parser.parse_srt(folder_name)
        
        # 3. Process visual/retention charts (images loaded as types.Part)
        visual_parts = self.image_processor.process_charts(folder_name)
        
        # 4. Fetch/parse reference URL if provided
        reference_data = ""
        if reference_url:
            reference_data = self.url_analyzer.analyze_url(reference_url)
            
        print("[*] Consolidating inputs & constructing multimodal payload for Gemini...")
        
        visual_summary = (
            f"Attached {len(visual_parts)} YouTube Studio analytics screenshots / retention charts." 
            if visual_parts else "No visual analytics screenshots provided."
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

Please generate an SEO Proposal containing:
- 3 high-CTR title variations (matching modern 2026 YouTube algorithm trends)
- A compelling, chapter-based description structure
- Relevant tags, key highlights, and visual hook suggestions.
"""

        proposal_content = ""
        if self.client:
            print(f"[*] Calling Gemini Model '{DEFAULT_MODEL}' with multimodal inputs...")
            try:
                # Compile contents list: text prompt + loaded image parts
                contents = [prompt] + visual_parts
                
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
