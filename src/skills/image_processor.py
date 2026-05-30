import mimetypes
from pathlib import Path
from google.genai import types
from config.settings import RAW_INPUTS_DIR

class ImageProcessor:
    def __init__(self):
        pass

    def process_charts(self, folder_name: str) -> list:
        """
        Loads images (screenshots, charts) from workspace/raw_inputs/{folder_name}
        and returns them as Gemini types.Part objects.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: ImageProcessor] Scanning for visual assets in: {folder_path}")
        
        if not folder_path.exists():
            print(f"[!] [Skill: ImageProcessor] Folder not found: {folder_path}")
            return []
            
        supported_exts = {".png", ".jpg", ".jpeg"}
        image_parts = []
        
        for file in folder_path.iterdir():
            if file.suffix.lower() in supported_exts:
                print(f"[+] [Skill: ImageProcessor] Loading image for multimodal analysis: {file.name}")
                try:
                    # Read image bytes
                    img_bytes = file.read_bytes()
                    # Guess mime type
                    mime_type, _ = mimetypes.guess_type(file)
                    if not mime_type:
                        mime_type = "image/png" if file.suffix.lower() == ".png" else "image/jpeg"
                    
                    # Create types.Part object
                    part = types.Part.from_bytes(
                        data=img_bytes,
                        mime_type=mime_type
                    )
                    image_parts.append(part)
                except Exception as e:
                    print(f"[-] [Skill: ImageProcessor] Error loading image {file.name}: {e}")
                    
        return image_parts
