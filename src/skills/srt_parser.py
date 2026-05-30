import re
from pathlib import Path
from config.settings import RAW_INPUTS_DIR

# Caps keep the prompt within the model context window. Greek text tokenizes
# heavily, so these are deliberately conservative.
CLEAN_TEXT_CAP = 14000
TIMELINE_CAP = 5000
# Seconds per timeline bucket: one navigational marker per window so the model
# can author chapters at real timestamps without us dumping every cue.
BUCKET_SECONDS = 45
SNIPPET_CHARS = 110


class SRTParser:
    def __init__(self):
        pass

    def parse(self, folder_name: str) -> dict:
        """
        Parses SRT/SBV subtitles and returns a structured result:
          {
            "clean_text": str,    # timestamp-free speech, for semantic keywords
            "timeline": str,      # [MM:SS] markers, so the model can build chapters
            "truncated": bool,    # whether clean_text was capped
            "found": bool,        # whether a subtitle file was located
          }
        """
        folder_path = RAW_INPUTS_DIR / folder_name
        print(f"[*] [Skill: SRTParser] Scanning for subtitle files (*.srt, *.sbv) in: {folder_path}")

        empty = {"clean_text": "", "timeline": "", "truncated": False, "found": False}

        if not folder_path.exists():
            empty["clean_text"] = "No raw inputs folder found for subtitles."
            return empty

        sub_files = list(folder_path.glob("*.srt")) + list(folder_path.glob("*.sbv"))
        if not sub_files:
            empty["clean_text"] = "No subtitle (.srt, .sbv) files found."
            return empty

        sub_path = sub_files[0]
        print(f"[+] [Skill: SRTParser] Parsing subtitle file: {sub_path.name}")

        try:
            content = sub_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            empty["clean_text"] = f"Error parsing subtitle file ({sub_path.name}): {e}"
            return empty

        cues = self._extract_cues(content)
        if not cues:
            empty["found"] = True
            empty["clean_text"] = "Subtitle file found but no readable speech text could be extracted."
            return empty

        # Clean speech stream (no timestamps) for keyword/semantic analysis.
        clean_text = " ".join(text for _, text in cues)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        truncated = len(clean_text) > CLEAN_TEXT_CAP
        if truncated:
            clean_text = clean_text[:CLEAN_TEXT_CAP].rsplit(" ", 1)[0] + " […]"

        timeline = self._build_timeline(cues)

        return {
            "clean_text": clean_text,
            "timeline": timeline,
            "truncated": truncated,
            "found": True,
        }

    def _extract_cues(self, content: str) -> list:
        """Returns a list of (start_seconds, text) tuples from SRT or SBV."""
        cues = []
        pending_start = None
        buffer = []

        def flush():
            if buffer:
                text = " ".join(buffer).strip()
                if text:
                    cues.append((pending_start if pending_start is not None else 0.0, text))

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # SRT numeric index lines.
            if line.isdigit():
                continue

            ts = self._parse_timestamp_line(line)
            if ts is not None:
                # New cue starts: flush previous buffer first.
                flush()
                buffer = []
                pending_start = ts
                continue

            # Any other line containing a timestamp pattern is metadata noise.
            if re.search(r"\d+:\d{2}:\d{2}", line):
                continue

            buffer.append(line)

        flush()
        return cues

    @staticmethod
    def _parse_timestamp_line(line: str):
        """Detects a cue header and returns its start time in seconds, else None."""
        # SRT: 00:00:01,000 --> 00:00:05,000
        m = re.match(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->", line)
        # SBV: 0:00:02.630,0:00:04.270
        if not m:
            m = re.match(r"(\d+):(\d{2}):(\d{2})[.,](\d{1,3})\s*,", line)
        if not m:
            return None
        h, mnt, s, ms = (int(x) for x in m.groups())
        return h * 3600 + mnt * 60 + s + ms / 1000.0

    def _build_timeline(self, cues: list) -> str:
        """Groups cues into time buckets and emits one [MM:SS] marker each."""
        lines = []
        current_bucket = -1
        snippet = ""

        for start, text in cues:
            bucket = int(start // BUCKET_SECONDS)
            if bucket != current_bucket:
                if snippet:
                    lines.append(snippet)
                current_bucket = bucket
                stamp = self._format_stamp(bucket * BUCKET_SECONDS)
                clipped = text[:SNIPPET_CHARS].strip()
                snippet = f"[{stamp}] {clipped}"
        if snippet:
            lines.append(snippet)

        timeline = "\n".join(lines)
        if len(timeline) > TIMELINE_CAP:
            timeline = timeline[:TIMELINE_CAP].rsplit("\n", 1)[0] + "\n[…]"
        return timeline

    @staticmethod
    def _format_stamp(total_seconds: float) -> str:
        total = int(total_seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
