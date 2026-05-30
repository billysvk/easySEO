from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class InfoReader:
    def __init__(self):
        pass

    def read_info(self, folder_name: str) -> str:
        """
        Reads metadata title and descriptions from info.txt if present inside the folder.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        info_file = folder_path / "info.txt"
        print(f"[*] [Skill: InfoReader] Checking for metadata in: {info_file}")
        
        if not info_file.exists():
            print(f"[!] [Skill: InfoReader] info.txt not found. Using empty template.")
            return "Title Draft: None\nDescription Draft: None"
            
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            print(f"[+] [Skill: InfoReader] Loaded metadata info from info.txt")
            return content
        except Exception as e:
            return f"Error reading info.txt: {e}"
