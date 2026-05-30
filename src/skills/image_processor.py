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
        Loads images (screenshots, charts) from workspace/raw_inputs/{folder_name}
        and returns a list of dictionaries with raw bytes, base64 strings, and Gemini Part objects.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: ImageProcessor] Scanning for visual assets in: {folder_path}")
        
        if not folder_path.exists():
            print(f"[!] [Skill: ImageProcessor] Folder not found: {folder_path}")
            return []
            
        supported_exts = {".png", ".jpg", ".jpeg"}
        processed_images = []
        
        for file in folder_path.iterdir():
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
