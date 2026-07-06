"""ChannelAnalyzer — scrapes the video's own channel to learn its baseline.

A professional channel manager never optimizes a video in isolation: they
know the channel's median performance, which uploads over/under-performed,
and which packaging styles the audience already responds to. This skill
scrapes the channel's public /videos tab (ytInitialData) and computes:

- recent uploads with views & age
- the channel's approximate median views (baseline)
- overperformers (>= 2x baseline) and underperformers (<= 0.5x baseline)
- title patterns of the overperformers (what THIS audience clicks)

All keyless, one HTTP request. Handles both the legacy `videoRenderer`
grid and the 2025+ `lockupViewModel` grid, and bypasses the EU consent
wall via cookies.
"""

import json
import re
from collections import Counter

import httpx

from src.skills.http_common import HEADERS, CONSENT_COOKIES

MAX_VIDEOS = 30


class ChannelAnalyzer:
    async def analyze_channel(self, video_url: str) -> str:
        """Resolves the channel from a video URL and profiles its recent uploads."""
        channel_url = await self._resolve_channel_url(video_url)
        if not channel_url:
            return "Channel could not be resolved from the video URL."

        print(f"[*] [Skill: ChannelAnalyzer] Profiling channel: {channel_url}")
        videos, channel_name = await self._scrape_videos_tab(channel_url)
        if not videos:
            return f"Channel videos tab could not be parsed ({channel_url})."

        return self._build_report(channel_name or channel_url, videos)

    # ------------------------------------------------------------------ #
    # Scraping
    # ------------------------------------------------------------------ #
    async def _resolve_channel_url(self, video_url: str) -> str:
        try:
            async with httpx.AsyncClient(headers=HEADERS, cookies=CONSENT_COOKIES, timeout=15.0) as client:
                response = await client.get(video_url, follow_redirects=True)
                response.raise_for_status()
            match = re.search(r'"ownerProfileUrl"\s*:\s*"([^"]+)"', response.text)
            if match:
                return match.group(1).replace("\\/", "/").replace("http://", "https://")
            match = re.search(r'"channelId"\s*:\s*"(UC[\w-]{22})"', response.text)
            if match:
                return f"https://www.youtube.com/channel/{match.group(1)}"
        except Exception as e:
            print(f"[-] [Skill: ChannelAnalyzer] Error resolving channel: {e}")
        return ""

    async def _scrape_videos_tab(self, channel_url: str) -> tuple[list, str]:
        url = channel_url.rstrip("/") + "/videos"
        try:
            async with httpx.AsyncClient(headers=HEADERS, cookies=CONSENT_COOKIES, timeout=15.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
        except Exception as e:
            print(f"[-] [Skill: ChannelAnalyzer] Error fetching videos tab: {e}")
            return [], ""

        match = re.search(r"ytInitialData\s*=\s*({.+?});", response.text, re.DOTALL)
        if not match:
            print("[-] [Skill: ChannelAnalyzer] ytInitialData not found on channel page.")
            return [], ""
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return [], ""

        channel_name = data.get("metadata", {}).get("channelMetadataRenderer", {}).get("title", "")

        videos = []
        # Legacy grid: videoRenderer nodes.
        for renderer in self._iter_key(data, "videoRenderer"):
            title = "".join(r.get("text", "") for r in renderer.get("title", {}).get("runs", []))
            views_text = renderer.get("viewCountText", {}).get("simpleText", "")
            published = renderer.get("publishedTimeText", {}).get("simpleText", "")
            if title:
                videos.append(self._entry(title, views_text, published))
            if len(videos) >= MAX_VIDEOS:
                break

        # 2025+ grid: lockupViewModel nodes.
        if not videos:
            for lockup in self._iter_key(data, "lockupViewModel"):
                meta = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
                title = meta.get("title", {}).get("content", "")
                views_text, published = "", ""
                rows = (
                    meta.get("metadata", {})
                    .get("contentMetadataViewModel", {})
                    .get("metadataRows", [])
                )
                for row in rows:
                    parts = [p.get("text", {}).get("content", "") for p in row.get("metadataParts", [])]
                    for part in parts:
                        if re.search(r"\d", part) and re.search(r"προβολ|view", part, re.IGNORECASE):
                            views_text = part
                        elif part:
                            published = published or part
                if title:
                    videos.append(self._entry(title, views_text, published))
                if len(videos) >= MAX_VIDEOS:
                    break
        return videos, channel_name

    def _entry(self, title: str, views_text: str, published: str) -> dict:
        return {
            "title": title.strip(),
            "views": self._parse_views(views_text),
            "views_text": views_text or "views n/a",
            "published": published,
        }

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #
    def _build_report(self, channel_name: str, videos: list) -> str:
        counted = [v for v in videos if v["views"] > 0]
        if not counted:
            return f"Channel '{channel_name}': {len(videos)} uploads found, but view counts were not visible."

        sorted_views = sorted(v["views"] for v in counted)
        median = sorted_views[len(sorted_views) // 2]

        over = [v for v in counted if median and v["views"] >= 2 * median]
        under = [v for v in counted if median and v["views"] <= 0.5 * median]

        word_counter: Counter = Counter()
        for v in over:
            for word in re.findall(r"[\w']+", v["title"].lower()):
                if len(word) > 3:
                    word_counter[word] += 1
        winning_words = [w for w, c in word_counter.most_common(10) if c >= 2]

        recent = counted[:10]
        lines = [
            f"CHANNEL BASELINE — '{channel_name}' (last {len(counted)} uploads):",
            f"- Median views per upload: ~{median:,}",
            "- Most recent uploads:",
        ]
        lines += [f"    * \"{v['title']}\" — {v['views_text']} ({v['published']})" for v in recent[:5]]
        if over:
            lines.append("- OVERPERFORMERS (>=2x baseline — packaging styles THIS audience clicks):")
            lines += [f"    * \"{v['title']}\" — {v['views_text']} ({v['published']})" for v in over[:6]]
        if winning_words:
            lines.append(f"- Recurring words in overperformer titles: {', '.join(winning_words)}")
        if under:
            lines.append("- UNDERPERFORMERS (<=0.5x baseline — packaging styles to avoid):")
            lines += [f"    * \"{v['title']}\" — {v['views_text']} ({v['published']})" for v in under[:5]]
        lines.append(
            "- STRATEGY: model the new packaging on the overperformers' psychology, "
            "and judge this video's own view count against the channel median above "
            "(if it's far below median, treat this as a REVIVAL case)."
        )
        print(f"[+] [Skill: ChannelAnalyzer] Baseline computed: median ~{median:,} views, "
              f"{len(over)} overperformers, {len(under)} underperformers.")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def _iter_key(cls, node, key):
        """Recursively yields every value of `key` in a nested dict/list."""
        if isinstance(node, dict):
            for k, v in node.items():
                if k == key and isinstance(v, dict):
                    yield v
                else:
                    yield from cls._iter_key(v, key)
        elif isinstance(node, list):
            for item in node:
                yield from cls._iter_key(item, key)

    @staticmethod
    def _parse_views(views_text: str) -> int:
        """Parses '1.234.567 views' / '1,2 εκ. προβολές' / '12K views' to int."""
        if not views_text:
            return 0
        text = views_text.lower().replace(" ", " ")
        multiplier = 1
        if any(m in text for m in ("εκ.", "εκατ", "million")) or re.search(r"[\d.,]\s*m\b", text):
            multiplier = 1_000_000
        elif any(m in text for m in ("χιλ", "thousand")) or re.search(r"[\d.,]\s*k\b", text):
            multiplier = 1_000
        num_match = re.search(r"([\d.,]+)", text)
        if not num_match:
            return 0
        raw = num_match.group(1)
        if multiplier > 1:
            raw = raw.replace(",", ".")
            parts = raw.split(".")
            raw = parts[0] + ("." + parts[1] if len(parts) > 1 else "")
            try:
                return int(float(raw) * multiplier)
            except ValueError:
                return 0
        raw = re.sub(r"[.,]", "", raw)
        try:
            return int(raw)
        except ValueError:
            return 0
