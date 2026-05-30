from pathlib import Path
from config.settings import OUTPUTS_DIR

class FileWriter:
    def __init__(self):
        pass

    def write_proposal(self, folder_name: str, content: str) -> None:
        """
        Outputs the generated SEO proposal file under the workspace/outputs/ directory.
        """
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUTS_DIR / f"{folder_name}_SEO_PROPOSAL.md"
        print(f"[*] [Skill: FileWriter] Saving SEO proposal to: {output_file}")
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[+] [Skill: FileWriter] SEO proposal written successfully to {output_file.name}")
        except Exception as e:
            print(f"[-] [Skill: FileWriter] Error writing proposal to file: {e}")
            raise e
