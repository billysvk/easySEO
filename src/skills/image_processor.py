import os
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class ImageProcessor:
    def __init__(self):
        pass

    def process_charts(self, folder_name: str) -> str:
        """
        Loads and prepares chart screenshots, retention curves, and video frames
        from the folder inside raw_inputs.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: ImageProcessor] Scanning for visual assets in: {folder_path}")
        
        if not folder_path.exists():
            return "No visual inputs folder found."
            
        supported_exts = {".png", ".jpg", ".jpeg"}
        found_images = []
        for file in folder_path.iterdir():
            if file.suffix.lower() in supported_exts:
                found_images.append(file.name)
                
        if not found_images:
            return "No image assets (screenshots, charts) found in folder."
            
        print(f"[+] [Skill: ImageProcessor] Found image assets: {found_images}")
        return f"Detected image assets for Gemini multi-modal processing: {', '.join(found_images)}"
