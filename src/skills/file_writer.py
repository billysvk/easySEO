import re
from config.settings import OUTPUTS_DIR


class FileWriter:
    def write_proposal(self, folder_name: str, content: str) -> None:
        """Writes the full SEO proposal under workspace/outputs/."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUTS_DIR / f"{folder_name}_SEO_PROPOSAL.md"
        print(f"[*] [Skill: FileWriter] Saving SEO proposal to outputs directory: {output_file}")
        try:
            output_file.write_text(content, encoding="utf-8")
            print(f"[+] [Skill: FileWriter] SEO proposal written successfully to {output_file.name}")
        except Exception as e:
            print(f"[-] [Skill: FileWriter] Error writing proposal to outputs: {e}")
            raise e

    def write_upload_pack(self, folder_name: str, content: str) -> None:
        """Extracts the 'COPY-PASTE UPLOAD PACK' section of the proposal into
        its own file so the creator can paste straight into YouTube Studio."""
        match = re.search(
            r"#+\s*\d*\.?\s*COPY-PASTE UPLOAD PACK.*?(?=\n#\s|\Z)",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not match:
            print("[!] [Skill: FileWriter] No upload-pack section found in proposal; skipping pack file.")
            return
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        pack_file = OUTPUTS_DIR / f"{folder_name}_UPLOAD_PACK.md"
        try:
            pack_file.write_text(match.group(0).strip() + "\n", encoding="utf-8")
            print(f"[+] [Skill: FileWriter] Copy-paste upload pack written to {pack_file.name}")
        except Exception as e:
            print(f"[-] [Skill: FileWriter] Error writing upload pack: {e}")

    def write_debug_prompt(self, folder_name: str, system_instruction: str, prompt: str) -> None:
        """Dry-run artifact: the exact intelligence package that would be sent
        to the LLM, for inspection or manual use in any chat model."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        debug_file = OUTPUTS_DIR / f"{folder_name}_INTELLIGENCE_PROMPT.md"
        try:
            debug_file.write_text(
                "# SYSTEM INSTRUCTION\n\n" + system_instruction + "\n\n# PROMPT\n\n" + prompt,
                encoding="utf-8",
            )
            print(f"[+] [Skill: FileWriter] Full intelligence prompt saved to {debug_file.name}")
        except Exception as e:
            print(f"[-] [Skill: FileWriter] Error writing debug prompt: {e}")
