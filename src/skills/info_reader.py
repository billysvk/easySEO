from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class InfoReader:
    def __init__(self):
        pass

    def read_info(self, folder_name: str) -> str:
        """
        Reads metadata title and descriptions from info.txt or any other .txt/.md file (like ham.md)
        present inside the folder.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: InfoReader] Scanning for metadata files in: {folder_path}")
        
        if not folder_path.exists():
            return "Title Draft: None\nDescription Draft: None"
            
        # Try info.txt first
        info_file = folder_path / "info.txt"
        if info_file.exists():
            return self._read_file_content(info_file)
            
        # Fallback: scan for any other .txt or .md file that is not a subtitle file
        for file in folder_path.iterdir():
            if file.is_file() and file.suffix.lower() in {".txt", ".md"}:
                if file.name.lower() != "info.txt":
                    print(f"[+] [Skill: InfoReader] Found alternative metadata file: {file.name}")
                    return self._read_file_content(file)
                    
        print(f"[!] [Skill: InfoReader] No metadata files (info.txt or any other .txt/.md) found.")
        return "Title Draft: None\nDescription Draft: None"

    def _read_file_content(self, file_path: Path) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            print(f"[+] [Skill: InfoReader] Loaded metadata from {file_path.name}")
            if not content:
                print(f"[!] [Skill: InfoReader] Warning: Metadata file {file_path.name} is empty.")
                return f"Title Draft: None (File {file_path.name} was empty)\nDescription Draft: None"
            return content
        except Exception as e:
            return f"Error reading {file_path.name}: {e}"
