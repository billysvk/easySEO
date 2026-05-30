import re
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class SRTParser:
    def __init__(self):
        pass

    def parse_srt(self, folder_name: str) -> str:
        """
        Parses SRT or SBV subtitles from the folder and extracts clean speech text.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: SRTParser] Scanning for subtitle files (*.srt, *.sbv) in: {folder_path}")
        
        if not folder_path.exists():
            return "No raw inputs folder found for subtitles."
            
        # Search for both srt and sbv files
        sub_files = list(folder_path.glob("*.srt")) + list(folder_path.glob("*.sbv"))
        if not sub_files:
            return "No subtitle (.srt, .sbv) files found."
            
        sub_path = sub_files[0]
        print(f"[+] [Skill: SRTParser] Parsing subtitle file: {sub_path.name}")
        
        try:
            with open(sub_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            clean_lines = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Skip numeric lines (SRT index lines)
                if line.isdigit():
                    continue
                # Skip SRT timestamps (e.g. 00:00:01,000 --> 00:00:05,000)
                if "-->" in line:
                    continue
                # Skip SBV timestamps (e.g. 0:00:02.630,0:00:04.270)
                if re.match(r'^\d+:\d{2}:\d{2}\.\d+,', line) or re.match(r'^\d+:\d{2}:\d{2}\.\d+$', line):
                    continue
                # Fallback matching for timestamp structures containing commas or dots
                if re.search(r'\d+:\d{2}:\d{2}', line):
                    continue
                clean_lines.append(line)
                
            clean_text = " ".join(clean_lines)
            # Remove duplicate spaces
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # Return truncated snippet if too long
            return clean_text[:10000] # Cap transcript text for prompt efficiency
        except Exception as e:
            return f"Error parsing subtitle file ({sub_path.name}): {e}"
