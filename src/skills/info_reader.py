import re
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class InfoReader:
    def __init__(self):
        pass

    def read_info(self, folder_name: str) -> dict:
        """
        Reads metadata title, description, video URL, and keyword from a .txt or .md file
        present inside the folder, excluding subtitles and generated SEO proposals.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: InfoReader] Scanning for metadata files inside: {folder_path}")
        
        empty_res = {"title": "", "description": "", "url": "", "keyword": ""}
        
        if not folder_path.exists():
            return empty_res
            
        # Try info.txt first
        info_file = folder_path / "info.txt"
        if info_file.exists():
            return self._read_file_content(info_file)
            
        # Scan for any other .txt or .md file that is not a subtitle or proposal file
        for file in folder_path.iterdir():
            if file.is_file() and file.suffix.lower() in {".txt", ".md"}:
                file_name_lower = file.name.lower()
                # Exclude subtitle files, proposal files, and already scraped metadata files
                if (file_name_lower != "info.txt" and 
                    "seo_proposal" not in file_name_lower and 
                    "scraped_metadata" not in file_name_lower and 
                    file.suffix.lower() != ".srt" and 
                    file.suffix.lower() != ".sbv"):
                    print(f"[+] [Skill: InfoReader] Found alternative metadata file: {file.name}")
                    return self._read_file_content(file)
                    
        print(f"[!] [Skill: InfoReader] No metadata files (info.txt or any other .txt/.md) found.")
        return empty_res

    def _read_file_content(self, file_path: Path) -> dict:
        empty_res = {"title": "", "description": "", "url": "", "keyword": ""}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            print(f"[+] [Skill: InfoReader] Loaded metadata from {file_path.name}")
            if not content:
                print(f"[!] [Skill: InfoReader] Warning: Metadata file {file_path.name} is empty.")
                return empty_res
            
            return self._parse_content(content)
        except Exception as e:
            print(f"[-] [Skill: InfoReader] Error reading {file_path.name}: {e}")
            return empty_res

    def _parse_content(self, content: str) -> dict:
        lines = content.splitlines()
        title = ""
        url = ""
        keyword = ""
        desc_lines = []
        
        current_field = None
        
        for line in lines:
            # Match fields case-insensitively, allowing optional bold stars or hashtags
            title_m = re.match(r'^#*\s*\*?title\*?\s*:\s*(.*)', line, re.IGNORECASE)
            url_m = re.match(r'^#*\s*\*?(?:video\s*url|video_url|url)\*?\s*:\s*(.*)', line, re.IGNORECASE)
            keyword_m = re.match(r'^#*\s*\*?(?:focus\s*keyword|keyword)\*?\s*:\s*(.*)', line, re.IGNORECASE)
            desc_m = re.match(r'^#*\s*\*?description\*?\s*:\s*(.*)', line, re.IGNORECASE)
            
            if title_m:
                title = title_m.group(1).strip()
                current_field = "title"
            elif url_m:
                url = url_m.group(1).strip()
                current_field = "url"
            elif keyword_m:
                keyword = keyword_m.group(1).strip()
                current_field = "keyword"
            elif desc_m:
                desc_lines.append(desc_m.group(1).strip())
                current_field = "description"
            else:
                if current_field == "description":
                    desc_lines.append(line)
                elif current_field == "title" and line.strip():
                    title += " " + line.strip()
                elif current_field == "url" and line.strip():
                    url += " " + line.strip()
                elif current_field == "keyword" and line.strip():
                    keyword += " " + line.strip()
        
        # If we failed to find any structured fields, return the entire file content as description
        # to preserve compatibility with raw text files.
        if not title and not desc_lines and not url and not keyword:
            print("[*] [Skill: InfoReader] No structured metadata fields found. Defaulting entire file content as description.")
            return {
                "title": "",
                "description": content.strip(),
                "url": "",
                "keyword": ""
            }
            
        description = "\n".join(desc_lines).strip()
        return {
            "title": title,
            "description": description,
            "url": url,
            "keyword": keyword
        }
