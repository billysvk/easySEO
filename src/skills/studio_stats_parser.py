import csv
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

class StudioStatsParser:
    def __init__(self):
        pass

    def parse_retention_csv(self, folder_name: str) -> str:
        """
        Scans for CSV files inside the folder, parses retention statistics,
        identifies drop-off intervals, and formats a diagnostic summary.
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        csv_files = list(folder_path.glob("*.csv"))
        
        if not csv_files:
            return "No audience retention CSV report provided."

        csv_path = csv_files[0]
        print(f"[*] [Skill: StudioStatsParser] Parsing audience retention CSV: {csv_path.name}")
        
        try:
            cues = []
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                # Read headers
                headers = next(reader, None)
                
                for row in reader:
                    if len(row) >= 2:
                        time_str = row[0].strip()
                        ret_str = row[1].strip().replace('%', '')
                        try:
                              ret_pct = float(ret_str)
                              cues.append((time_str, ret_pct))
                        except ValueError:
                              continue
            
            if not cues:
                return "CSV file found but no valid time/retention data could be parsed."

            # Analyze drops
            drops = []
            prev_pct = cues[0][1] if cues else 100.0
            
            # A drop is significant if retention falls by more than 8% in a single step
            for time_str, pct in cues[1:]:
                diff = prev_pct - pct
                if diff >= 8.0:
                    drops.append(f"- **Drop at {time_str}**: Lost {diff:.1f}% of audience in this segment (from {prev_pct:.1f}% to {pct:.1f}%)")
                prev_pct = pct

            summary = [
                f"### Audience Retention CSV Diagnostics ({csv_path.name})",
                f"Initial Retention: {cues[0][1]}% at {cues[0][0]}",
                f"Final Retention: {cues[-1][1]}% at {cues[-1][0]}"
            ]
            if drops:
                summary.append("#### Critical Retention Drops Identified:")
                summary.extend(drops[:10]) # Limit to top 10 drops
            else:
                summary.append("No sudden significant retention drops identified in the CSV.")

            return "\n".join(summary)
        except Exception as e:
            return f"Failed to parse retention CSV file: {e}"
