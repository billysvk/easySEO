import base64
import mimetypes
from pathlib import Path
from google.genai import types
from config.settings import RAW_INPUTS_DIR

class ImageProcessor:
    def __init__(self):
        pass

    def process_charts(self, folder_name: str) -> list:
        """
        Loads images (screenshots, charts) from workspace/raw_inputs/{folder_name}/statistics
        if it exists, otherwise falls back to workspace/raw_inputs/{folder_name}.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        
        # Check if the statistics folder exists inside the video folder
        stats_path = folder_path / "statistics"
        if stats_path.exists() and stats_path.is_dir():
            search_path = stats_path
            print(f"[*] [Skill: ImageProcessor] Scanning for visual assets in statistics subfolder: {search_path}")
        else:
            search_path = folder_path
            print(f"[*] [Skill: ImageProcessor] Scanning for visual assets in root folder: {search_path}")
            
        if not search_path.exists():
            print(f"[!] [Skill: ImageProcessor] Folder not found: {search_path}")
            return []
            
        supported_exts = {".png", ".jpg", ".jpeg"}
        processed_images = []
        
        for file in search_path.iterdir():
            if file.suffix.lower() in supported_exts:
                print(f"[+] [Skill: ImageProcessor] Loading image: {file.name}")
                try:
                    img_bytes = file.read_bytes()
                    
                    # Base64 encoding for Ollama / HTTP APIs
                    base64_str = base64.b64encode(img_bytes).decode("utf-8")
                    
                    # Guess mime type
                    mime_type, _ = mimetypes.guess_type(file)
                    if not mime_type:
                        mime_type = "image/png" if file.suffix.lower() == ".png" else "image/jpeg"
                    
                    # Create types.Part object for Gemini SDK
                    part_obj = types.Part.from_bytes(
                        data=img_bytes,
                        mime_type=mime_type
                    )
                    
                    processed_images.append({
                        "name": file.name,
                        "bytes": img_bytes,
                        "base64": base64_str,
                        "mime_type": mime_type,
                        "part": part_obj
                    })
                except Exception as e:
                    print(f"[-] [Skill: ImageProcessor] Error processing image {file.name}: {e}")
                    
        return processed_images
