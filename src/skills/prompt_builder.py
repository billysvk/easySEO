import re
from pathlib import Path
from config.settings import SYSTEM_PROMPT_PATH

# Fallback persona used only if .gemini.md is missing or unreadable, so neither
# provider path ever dies because of a documentation file.
_FALLBACK_SYSTEM_INSTRUCTION = (
    "You are easySEO, an elite senior YouTube SEO consultant and audience "
    "retention architect. Transform the provided raw video assets into a "
    "high-conversion, 2026-standard YouTube optimization package: 3 high-CTR "
    "titles (under 60 characters), a chapter-based description with timestamps, "
    "retention diagnostics, a thumbnail blueprint, and semantic tags. Always "
    "answer in the same language as the source title/transcript."
)

# Minimal fallback template if the structured block in .gemini.md is not found.
_FALLBACK_TEMPLATE = """Analyze the following YouTube video inputs and produce a complete SEO proposal.

--- CURRENT METADATA DRAFTS ---
{info_text}

--- CLEAN SPEECH TRANSCRIPT ---
{transcript_text}

--- VISUAL & RETENTION DATA ---
{visual_data}

--- EXTERNAL REFERENCE / COMPETITOR CONTENT ---
{reference_data}

--- THUMBNAIL GUIDELINE BASE ---
{thumbnail_guides}

Deliver: 3 high-CTR title variations (under 60 chars, distinct psychological
angles), an above-the-fold hook, a value summary, a granular timestamped
chapter list, retention diagnostics, a thumbnail blueprint with 2 ready-to-use
image-generator prompts, and categorized SEO tags."""

_PLACEHOLDERS = (
    "info_text",
    "transcript_text",
    "visual_data",
    "reference_data",
    "thumbnail_guides",
)


class PromptBuilder:
    """Loads the SEO persona + output blueprint from .gemini.md and assembles
    the final prompt. Keeps .gemini.md as the single source of truth instead of
    hard-coding the prompt in the orchestrator."""

    def __init__(self) -> None:
        self._raw = self._load_raw()

    def _load_raw(self) -> str:
        try:
            return Path(SYSTEM_PROMPT_PATH).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[!] [Skill: PromptBuilder] Could not read {SYSTEM_PROMPT_PATH}: {e}")
            return ""

    def get_system_instruction(self) -> str:
        """Extracts Section 1 (Role & Directives) as the system instruction."""
        if not self._raw:
            return _FALLBACK_SYSTEM_INSTRUCTION

        # Section 1 spans from "## 1." up to the start of "## 2." (template).
        match = re.search(
            r"##\s*1\.\s*System Instructions.*?(?=\n##\s*2\.)",
            self._raw,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if match:
            section = match.group(0).strip()
            if section:
                print("[+] [Skill: PromptBuilder] Loaded system instruction from .gemini.md")
                return section

        print("[!] [Skill: PromptBuilder] Section 1 not found; using fallback persona.")
        return _FALLBACK_SYSTEM_INSTRUCTION

    def _get_template(self) -> str:
        """Extracts the fenced template block inside Section 2."""
        if not self._raw:
            return _FALLBACK_TEMPLATE

        # Grab the first fenced ```text ... ``` block (the proposal template).
        match = re.search(r"```(?:text)?\s*\n(.*?)```", self._raw, flags=re.DOTALL)
        if match and "{info_text}" in match.group(1):
            return match.group(1).strip()

        print("[!] [Skill: PromptBuilder] Template block not found; using fallback template.")
        return _FALLBACK_TEMPLATE

    def build_prompt(
        self,
        info_text: str,
        transcript_text: str,
        visual_data: str,
        reference_data: str,
        thumbnail_guides: str,
    ) -> str:
        """Fills the template with the gathered inputs.

        Uses per-placeholder str.replace (not str.format) so stray braces in the
        markdown or in the input data can never raise KeyError / ValueError.
        """
        template = self._get_template()
        values = {
            "info_text": info_text or "None provided.",
            "transcript_text": transcript_text or "No transcript available.",
            "visual_data": visual_data or "No visual data provided.",
            "reference_data": reference_data or "No external reference provided.",
            "thumbnail_guides": thumbnail_guides or "",
        }
        for key in _PLACEHOLDERS:
            template = template.replace("{" + key + "}", values[key])
        return template
