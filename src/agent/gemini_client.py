"""EasySEOAgent — the orchestrator of the easySEO Viral Engine.

One input (a YouTube URL or a workspace folder) is transformed into a full
viral optimization package. The agent:

1. Resolves the target (URL -> auto-provisioned workspace folder).
2. Gathers ALL intelligence concurrently:
   - official/auto subtitles          (SubtitleDownloader)
   - live video metadata + tags       (URLAnalyzer)
   - live SERP + competitor packaging (CompetitorAnalyzer)
   - real search demand & trends      (TrendHunter)
3. Audits the current packaging deterministically (SEOAuditor).
4. Feeds everything into the LLM blueprint (.gemini.md) via PromptBuilder.
5. Writes the SEO proposal + a copy-paste upload pack.
"""

import asyncio
import os
import re
import shutil
import subprocess
import time

import httpx
from google import genai
from google.genai import types

from config.settings import (
    DEFAULT_MODEL,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    AI_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TIMEOUT,
    LLM_TEMPERATURE,
    RAW_INPUTS_DIR,
    TREND_GEO,
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
from src.skills.trend_hunter import TrendHunter
from src.skills.seo_auditor import SEOAuditor
from src.skills.channel_analyzer import ChannelAnalyzer
from src.skills.comment_miner import CommentMiner

_YOUTUBE_URL_RE = re.compile(r"(?:v=|/v/|embed/|youtu\.be/|/watch\?v=|\?v=|/shorts/)([\w-]{11})")


class EasySEOAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

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
        self.trend_hunter = TrendHunter()
        self.seo_auditor = SEOAuditor()
        self.channel_analyzer = ChannelAnalyzer()
        self.comment_miner = CommentMiner()

    # ------------------------------------------------------------------ #
    # Target resolution: URL-in -> workspace folder
    # ------------------------------------------------------------------ #
    @staticmethod
    def resolve_target(target: str) -> tuple[str, str]:
        """Accepts either a YouTube URL or a workspace folder name.
        Returns (folder_name, video_url). For URLs a workspace folder named
        after the video id is auto-provisioned with an input.md stub."""
        target = (target or "").strip()
        match = _YOUTUBE_URL_RE.search(target)
        if target.lower().startswith(("http://", "https://")) and match:
            video_id = match.group(1)
            folder_name = f"video_{video_id}"
            folder_path = RAW_INPUTS_DIR / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            meta_file = folder_path / "input.md"
            if not meta_file.exists():
                meta_file.write_text(f"url: {target}\n", encoding="utf-8")
                print(f"[+] [Orchestrator] Auto-provisioned workspace folder '{folder_name}' from URL.")
            return folder_name, target
        return target, ""

    # ------------------------------------------------------------------ #
    # Main workflow
    # ------------------------------------------------------------------ #
    async def run(
        self,
        folder_name: str,
        reference_url: str = None,
        no_visual: bool = False,
        model_override: str = None,
        dry_run: bool = False,
        provider: str = None,
    ) -> None:
        start_time = time.monotonic()
        provider = (provider or AI_PROVIDER).lower()
        print(f"[*] Starting Viral Engine workflow for: '{folder_name}'")
        print(f"[*] Active AI Provider: '{provider.upper()}'")

        # 1. Read existing metadata (title/description/url/keyword)
        info_dict = self.info_reader.read_info(folder_name)
        title = info_dict.get("title", "")
        description = info_dict.get("description", "")
        video_url = info_dict.get("url", "")
        keyword = info_dict.get("keyword", "")

        # ------------------------------------------------------------------
        # PHASE 1 — video-level intelligence (concurrent)
        # ------------------------------------------------------------------
        scraped_metadata = None
        if video_url:
            print(f"[*] [Phase 1/4] Harvesting video intelligence for: {video_url}")
            subs_task = self.subtitle_downloader.download_subtitles(folder_name, video_url)
            scrape_task = asyncio.to_thread(self.url_analyzer.scrape_video_metadata, video_url)
            _, scraped_metadata = await asyncio.gather(subs_task, scrape_task)

            if scraped_metadata.get("success"):
                self._save_scraped_metadata(folder_name, video_url, scraped_metadata)
                if not title and scraped_metadata.get("title"):
                    title = scraped_metadata["title"]
                    print(f"[+] [Orchestrator] Populated missing Title from live video: '{title}'")
                if not description and scraped_metadata.get("description"):
                    description = scraped_metadata["description"]
                    print("[+] [Orchestrator] Populated missing Description from live video.")
            else:
                print(f"[!] [Orchestrator] Warning: could not scrape live video URL: {scraped_metadata.get('error', 'unknown error')}")

        # Keyword discovery (needs the scraped tags, so runs after Phase 1)
        if not keyword or not keyword.strip():
            keyword = self._discover_keyword(folder_name, title, scraped_metadata)

        # ------------------------------------------------------------------
        # PHASE 2 — market intelligence (concurrent: SERP + trends + reference)
        # ------------------------------------------------------------------
        print("[*] [Phase 2/4] Sweeping the market: SERP competitors, channel baseline, comments, search demand & live trends...")
        search_query = self._pick_search_seed(keyword, title)
        if search_query:
            print(f"[*] [Orchestrator] Selected search seed for market sweep: '{search_query}'")
        market_tasks = [
            self.competitor_analyzer.analyze_competitors(search_query),
            self.trend_hunter.hunt(search_query, geo=TREND_GEO),
            self.channel_analyzer.analyze_channel(video_url) if video_url
            else asyncio.sleep(0, result="No video URL — channel baseline skipped."),
            self.comment_miner.mine(video_url),
        ]
        if reference_url:
            market_tasks.append(asyncio.to_thread(self.url_analyzer.analyze_url, reference_url))

        market_results = await asyncio.gather(*market_tasks, return_exceptions=True)
        competitor_data = market_results[0] if not isinstance(market_results[0], BaseException) else f"Competitor sweep failed: {market_results[0]}"
        trend_data = market_results[1] if not isinstance(market_results[1], BaseException) else f"Trend sweep failed: {market_results[1]}"
        channel_data = market_results[2] if not isinstance(market_results[2], BaseException) else f"Channel profiling failed: {market_results[2]}"
        comments_data = market_results[3] if not isinstance(market_results[3], BaseException) else f"Comment mining failed: {market_results[3]}"
        reference_parts = []
        if reference_url and len(market_results) > 4 and not isinstance(market_results[4], BaseException):
            reference_parts.append(market_results[4])
        reference_parts.append(
            f"--- COMPETITOR SEARCH & KEYWORD GAP ANALYSIS (Keyword: '{search_query}') ---\n{competitor_data}"
        )
        reference_data = "\n\n".join(reference_parts)

        # ------------------------------------------------------------------
        # PHASE 3 — local assets: transcript, retention charts, CSV stats
        # ------------------------------------------------------------------
        print("[*] [Phase 3/4] Processing local assets (transcript, retention data, screenshots)...")
        srt_result = self.srt_parser.parse(folder_name)
        if srt_result.get("truncated"):
            print("[!] Transcript was long and has been truncated for the prompt.")
        transcript_block = self._compose_transcript(srt_result)

        visual_images = []
        if not no_visual:
            visual_images = self.image_processor.process_charts(folder_name)
        else:
            print("[*] Skipping visual image analysis (--no-visual flag active).")

        csv_diagnostics = self.studio_stats_parser.parse_retention_csv(folder_name)
        visual_summary = (
            f"Attached {len(visual_images)} YouTube Studio analytics screenshots / "
            "retention charts. Analyze them for intro drop-offs, valleys and spikes."
            if visual_images
            else "No visual analytics screenshots provided (text-only analysis)."
        )
        visual_summary += f"\n\n{csv_diagnostics}"

        # Deterministic packaging audit — the "before" scorecard.
        scraped_tags = (scraped_metadata or {}).get("keywords", []) or []
        audit = self.seo_auditor.audit(
            title=title,
            description=description,
            keyword=keyword,
            tags=scraped_tags,
            transcript_text=srt_result.get("clean_text", ""),
        )

        # ------------------------------------------------------------------
        # PHASE 4 — synthesis
        # ------------------------------------------------------------------
        print("[*] [Phase 4/4] Consolidating intelligence & synthesizing the viral package...")
        info_text = self._compose_info_text(title, description, video_url, scraped_metadata)
        thumbnail_guides = self.thumbnail_strategist.get_strategy_placeholder()
        shorts_guides = self.shorts_architect.get_shorts_guidelines()
        visual_guides = f"{thumbnail_guides}\n\n{shorts_guides}"

        system_instruction = self.prompt_builder.get_system_instruction()
        prompt = self.prompt_builder.build_prompt(
            info_text=info_text,
            transcript_text=transcript_block,
            visual_data=visual_summary,
            reference_data=reference_data,
            thumbnail_guides=visual_guides,
            trend_data=trend_data,
            audit_report=audit["report"],
            channel_data=channel_data,
            comments_data=comments_data,
        )

        if dry_run:
            self.file_writer.write_debug_prompt(folder_name, system_instruction, prompt)
            elapsed = time.monotonic() - start_time
            print(f"[+] DRY RUN complete in {elapsed:.1f}s — full intelligence prompt saved (no LLM call).")
            return

        if provider == "ollama":
            ollama_model = model_override or OLLAMA_MODEL
            print(f"[*] Calling local Ollama server at {OLLAMA_URL} using model '{ollama_model}'...")
            proposal_content = self._call_ollama(prompt, system_instruction, visual_images, ollama_model)
        elif provider == "claude":
            proposal_content = self._call_claude(prompt, system_instruction, visual_images, model_override)
        else:
            proposal_content = self._call_gemini(prompt, system_instruction, visual_images, model_override)

        self.file_writer.write_proposal(folder_name, proposal_content)
        self.file_writer.write_upload_pack(folder_name, proposal_content)
        elapsed = time.monotonic() - start_time
        print(f"[+] Viral package ready in {elapsed:.1f}s. Packaging score before optimization: {audit['score']}/100.")

    # ------------------------------------------------------------------ #
    # Provider calls
    # ------------------------------------------------------------------ #
    def _call_gemini(self, prompt, system_instruction, visual_images, model_override):
        if not self.client:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to .env, or run with --dry-run "
                "to generate the full intelligence prompt without an LLM call."
            )

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

    def _call_claude(self, prompt, system_instruction, visual_images, model_override=None):
        """Generates the proposal with Claude.

        Path 1 (preferred): the official Anthropic SDK when an API key or an
        `ant auth login` profile is available — full multimodal support.
        Path 2 (fallback): the Claude Code CLI (`claude -p`), which reuses the
        user's existing Claude subscription login — text-only.
        """
        if ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return self._call_claude_sdk(prompt, system_instruction, visual_images, model_override)

        claude_bin = shutil.which("claude")
        if claude_bin:
            return self._call_claude_cli(claude_bin, prompt, system_instruction, model_override)

        # Last attempt: the SDK also resolves `ant auth login` profiles on its own.
        try:
            return self._call_claude_sdk(prompt, system_instruction, visual_images, model_override)
        except Exception as e:
            raise ValueError(
                "No Claude access found. Either set ANTHROPIC_API_KEY in .env, "
                "or install/log in to the Claude Code CLI (`claude`). "
                f"(SDK error: {e})"
            )

    def _call_claude_sdk(self, prompt, system_instruction, visual_images, model_override=None):
        import anthropic

        model = model_override or CLAUDE_MODEL
        print(f"[*] Calling Claude via Anthropic SDK, model '{model}' (multimodal)...")

        content = [{"type": "text", "text": prompt}]
        for img in visual_images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("mime_type", "image/png"),
                        "data": img["base64"],
                    },
                }
            )

        client = anthropic.Anthropic()
        with client.messages.stream(
            model=model,
            max_tokens=32000,
            system=system_instruction,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": content}],
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            raise ValueError("Claude declined this request (stop_reason=refusal).")
        text = "".join(b.text for b in response.content if b.type == "text")
        return self._strip_reasoning(text)

    def _call_claude_cli(self, claude_bin, prompt, system_instruction, model_override=None):
        model_note = f" (model: {model_override})" if model_override else " (your default Claude model)"
        print(f"[*] Calling Claude via the Claude Code CLI using your subscription{model_note}...")
        print("[*] This generates the full package in one shot — allow a few minutes.")

        full_prompt = (
            f"{system_instruction}\n\n{prompt}\n\n"
            "IMPORTANT: Reply ONLY with the completed YOUTUBE VIRAL OPTIMIZATION PACKAGE "
            "markdown document. No preamble, no questions, no tool use."
        )
        cmd = [claude_bin, "-p"]
        if model_override:
            cmd += ["--model", model_override]

        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        if result.returncode != 0 or not (result.stdout or "").strip():
            raise ValueError(
                f"Claude CLI failed (exit {result.returncode}): {(result.stderr or '')[:500]}"
            )
        return self._strip_reasoning(result.stdout.strip())

    def _call_ollama(self, prompt, system_instruction, visual_images, model=None):
        payload = {
            "model": model or OLLAMA_MODEL,
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
            timeout=OLLAMA_TIMEOUT,  # CPU inference of long prompts is slow.
        )
        response.raise_for_status()
        return self._strip_reasoning(response.json().get("response", ""))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _discover_keyword(self, folder_name: str, title: str, scraped_metadata: dict | None) -> str:
        print("[*] [Orchestrator] Focus keyword is missing. Initiating automatic keyword discovery...")
        discovered_keyword = ""

        # Method A: use the video's own hidden tags (strongest signal).
        if scraped_metadata and scraped_metadata.get("keywords"):
            cleaned = []
            for kw in scraped_metadata["keywords"]:
                kw = kw.strip()
                if kw and kw not in cleaned:
                    cleaned.append(kw)
            if cleaned:
                discovered_keyword = ", ".join(cleaned)

        # Method B: fall back to parsing the title.
        if not discovered_keyword and title:
            clean_title = re.sub(r"#\S+", "", title)
            clean_title = re.sub(r"[^\w\s|:\-—]", "", clean_title)
            parts = re.split(r"[|:\-—]", clean_title)
            if parts:
                candidate = re.sub(r"\s+", " ", parts[0]).strip()
                if candidate:
                    title_lower = title.lower()
                    if any(t in title_lower for t in ("travel", "vlog", "ταξίδι", "ταξιδι")):
                        discovered_keyword = f"{candidate} travel vlog"
                    else:
                        discovered_keyword = candidate

        if not discovered_keyword:
            discovered_keyword = "travel vlog"

        keyword = discovered_keyword.strip()

        meta_file_path = RAW_INPUTS_DIR / folder_name / "input.md"
        if not meta_file_path.exists() and (RAW_INPUTS_DIR / folder_name / "info.txt").exists():
            meta_file_path = RAW_INPUTS_DIR / folder_name / "info.txt"
        self._update_keyword_in_file(meta_file_path, keyword)
        return keyword

    def _save_scraped_metadata(self, folder_name: str, video_url: str, scraped_metadata: dict) -> None:
        scraped_file_path = RAW_INPUTS_DIR / folder_name / "scraped_metadata.md"
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
            scraped_file_path.write_text(scraped_content, encoding="utf-8")
            print(f"[+] [Orchestrator] Scraped metadata saved to {scraped_file_path.name}")
        except Exception as e:
            print(f"[-] [Orchestrator] Error saving scraped metadata file: {e}")

    @staticmethod
    def _pick_search_seed(keyword: str, title: str) -> str:
        """Chooses the smartest search seed from the keyword list.

        A generic first tag like 'turkey' pollutes the SERP/trend sweep with
        irrelevant results. Prefer a multi-word tag that actually appears in
        the video title (highest topical specificity), then any tag found in
        the title, then the longest multi-word tag, then the first tag."""
        if not keyword:
            return ""
        tags = [t.strip() for t in keyword.split(",") if t.strip()]
        if not tags:
            return ""
        title_lower = (title or "").lower()

        in_title = [t for t in tags if t.lower() in title_lower]
        multiword_in_title = [t for t in in_title if " " in t]
        if multiword_in_title:
            return max(multiword_in_title, key=len)
        if in_title:
            return max(in_title, key=len)
        multiword = [t for t in tags if " " in t and len(t) <= 40]
        if multiword:
            return multiword[0]
        return tags[0]

    @staticmethod
    def _compose_info_text(title, description, video_url, scraped_metadata) -> str:
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
        return "\n\n".join(info_parts) if info_parts else "Title Draft: None\nDescription Draft: None"

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

    def _update_keyword_in_file(self, meta_file_path, new_keyword: str) -> None:
        try:
            content = ""
            if meta_file_path.exists():
                content = meta_file_path.read_text(encoding="utf-8")

            keyword_line_pattern = re.compile(
                r"^#*\s*\*?(?:focus\s*keyword|keyword)\*?\s*:\s*(.*)",
                re.IGNORECASE | re.MULTILINE,
            )
            if keyword_line_pattern.search(content):
                updated_content = keyword_line_pattern.sub(f"keyword: {new_keyword}", content)
            else:
                updated_content = content.rstrip() + f"\nkeyword: {new_keyword}\n"

            meta_file_path.write_text(updated_content, encoding="utf-8")
            print(f"[+] [Orchestrator] Automatically filled and saved focus keyword to {meta_file_path.name}: '{new_keyword}'")
        except Exception as e:
            print(f"[-] [Orchestrator] Error updating keyword in metadata file: {e}")
