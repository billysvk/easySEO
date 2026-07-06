import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import httpx
from config.settings import RAW_INPUTS_DIR

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

class SubtitleDownloader:
    def __init__(self):
        pass

    async def download_subtitles(self, folder_name: str, video_url: str) -> bool:
        """
        Attempts to download subtitles for a given YouTube URL and save them as
        captions.sbv inside workspace/raw_inputs/{folder_name}/.
        """
        if not video_url:
            return False

        video_id = self._extract_video_id(video_url)
        if not video_id:
            print(f"[!] [Skill: SubtitleDownloader] Could not extract YouTube video ID from: {video_url}")
            return False

        folder_path = RAW_INPUTS_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        output_file = folder_path / "captions.sbv"

        # If a subtitle file already exists, don't download it again
        if (folder_path / "captions.sbv").exists() or (folder_path / "subs.sbv").exists() or list(folder_path.glob("*.srt")):
            print(f"[+] [Skill: SubtitleDownloader] Subtitle file already exists in {folder_name}. Skipping download.")
            return True

        print(f"[*] [Skill: SubtitleDownloader] Attempting to download subtitles for video: {video_id}...")

        # Method 1: youtube-transcript-api (robust official captions)
        if YouTubeTranscriptApi:
            try:
                api = YouTubeTranscriptApi()
                # Try getting Greek or English transcripts
                try:
                    cues = api.fetch(video_id, languages=['el', 'en'])
                except Exception as fetch_err:
                    print(f"[*] [Skill: SubtitleDownloader] Direct API fetch failed: {fetch_err}. Trying listing...")
                    transcript_list = api.list(video_id)
                    # Fetch Greek first, then English, or whatever is available
                    try:
                        transcript = transcript_list.find_transcript(['el', 'en'])
                    except:
                        transcript = next(iter(transcript_list))
                    cues = transcript.fetch()

                sbv_content = self._format_as_sbv(cues)
                output_file.write_text(sbv_content, encoding="utf-8")
                print(f"[+] [Skill: SubtitleDownloader] Successfully downloaded subtitles via API to {output_file.name}")
                return True
            except Exception as api_err:
                print(f"[*] [Skill: SubtitleDownloader] youtube-transcript-api failed: {api_err}. Trying fallback scraper...")

        # Method 2: Scrape and parse ytInitialPlayerResponse captions track
        try:
            from src.skills.http_common import HEADERS, CONSENT_COOKIES
            async with httpx.AsyncClient(cookies=CONSENT_COOKIES) as client:
                response = await client.get(video_url, headers=HEADERS, timeout=15.0, follow_redirects=True)
                response.raise_for_status()

            # Find ytInitialPlayerResponse
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', response.text)
            if not match:
                match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;</script>', response.text)
            if not match:
                match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\});', response.text, re.DOTALL)

            if match:
                player_data = json.loads(match.group(1))
                caption_tracks = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
                
                if caption_tracks:
                    # Select Greek track if available, else first track
                    track_url = ""
                    for track in caption_tracks:
                        if track.get("languageCode") == "el":
                            track_url = track.get("baseUrl")
                            break
                    if not track_url:
                        track_url = caption_tracks[0].get("baseUrl")

                    if track_url:
                        print(f"[*] [Skill: SubtitleDownloader] Fetching captions XML track...")
                        async with httpx.AsyncClient() as client:
                            xml_response = await client.get(track_url, timeout=10.0)
                            xml_response.raise_for_status()

                        # Parse XML cues
                        cues = self._parse_xml_captions(xml_response.text)
                        if cues:
                            sbv_content = self._format_as_sbv(cues)
                            output_file.write_text(sbv_content, encoding="utf-8")
                            print(f"[+] [Skill: SubtitleDownloader] Successfully scraped subtitles to {output_file.name}")
                            return True

        except Exception as fallback_err:
            print(f"[!] [Skill: SubtitleDownloader] Fallback scraper failed: {fallback_err}")

        print(f"[!] [Skill: SubtitleDownloader] Could not download subtitles for video: {video_id}")
        return False

    def _extract_video_id(self, url: str) -> str:
        patterns = [
            r'(?:v=|/v/|embed/|youtu\.be/|/watch\?v=|\?v=)([^#\&\?]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ""

    def _parse_xml_captions(self, xml_text: str) -> list:
        cues = []
        try:
            # Parse XML. Standard YouTube captions XML format:
            # <transcript><text start="1.23" dur="4.56">Hello</text></transcript>
            root = ET.fromstring(xml_text)
            for text_elem in root.findall("text"):
                start = float(text_elem.get("start", 0.0))
                dur = float(text_elem.get("dur", 0.0))
                text = text_elem.text or ""
                # Decode HTML entities if present
                text = re.sub(r'&amp;', '&', text)
                text = re.sub(r'&lt;', '<', text)
                text = re.sub(r'&gt;', '>', text)
                text = re.sub(r'&quot;', '"', text)
                text = re.sub(r'&#39;', "'", text)
                
                cues.append({
                    "start": start,
                    "duration": dur,
                    "text": text.strip()
                })
        except Exception as e:
            print(f"[!] [Skill: SubtitleDownloader] XML parse error: {e}")
        return cues

    def _format_as_sbv(self, cues: list) -> str:
        """Formats list of cues into standard SBV format."""
        sbv_lines = []
        for cue in cues:
            # Handle both dictionary (fallback XML parser) and object-like cues (youtube-transcript-api)
            if isinstance(cue, dict):
                start = cue.get("start", 0.0)
                duration = cue.get("duration", 0.0)
                text = cue.get("text", "")
            else:
                start = getattr(cue, "start", 0.0)
                duration = getattr(cue, "duration", 0.0)
                text = getattr(cue, "text", "")
            
            if not text:
                continue

            start_stamp = self._format_timestamp(start)
            end_stamp = self._format_timestamp(start + duration)
            
            sbv_lines.append(f"{start_stamp},{end_stamp}")
            sbv_lines.append(text)
            sbv_lines.append("") # Empty line separator
            
        return "\n".join(sbv_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Formats seconds into YouTube's SBV timestamp format: H:MM:SS.mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds % 1) * 1000))
        if ms >= 1000:
            s += 1
            ms -= 1000
        return f"{h}:{m:02d}:{s:02d}.{ms:03d}"
