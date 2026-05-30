import re
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class SRTParser:
    def __init__(self):
        pass

    def parse_srt(self, folder_name: str) -> str:
        """
        Parses SRT subtitles from the folder and extracts clean speech text.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: SRTParser] Scanning for subtitle files (*.srt) in: {folder_path}")
        
        if not folder_path.exists():
            return "No raw inputs folder found for subtitles."
            
        srt_files = list(folder_path.glob("*.srt"))
        if not srt_files:
            return "No subtitle (.srt) files found."
            
        srt_path = srt_files[0]
        print(f"[+] [Skill: SRTParser] Parsing subtitle file: {srt_path.name}")
        
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple regex to strip timestamps and line numbers
            # Match line numbers, timestamps like 00:00:00,000 --> 00:00:00,000, and leave plain text
            clean_lines = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.isdigit():
                    continue
                if "-->" in line:
                    continue
                clean_lines.append(line)
                
            clean_text = " ".join(clean_lines)
            # Remove duplicate spaces
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # Return truncated snippet if too long
            return clean_text[:10000] # Cap transcript text for prompt efficiency
        except Exception as e:
            return f"Error parsing SRT file: {e}"
        
