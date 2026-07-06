"""CompetitorAnalyzer — deep, keyless YouTube SERP intelligence.

For the focus keyword it:
1. Scrapes the live YouTube search results page (ytInitialData) and extracts
   the top-ranking videos WITH their public performance signals: view count,
   upload age, duration and channel — the exact packaging the algorithm is
   rewarding for this query right now.
2. Deep-scrapes the top videos concurrently for their hidden tags and full
   descriptions (ytInitialPlayerResponse).
3. Distills a "Packaging Intelligence" digest: recurring title words, the
   most reused tags across winners, and title-length norms — so the LLM can
   beat the pattern instead of guessing it.
"""

import asyncio
import json
import re
import urllib.parse
from collections import Counter

import httpx

from src.skills.http_common import HEADERS as _HEADERS, CONSENT_COOKIES as _COOKIES

# Words too generic to count as packaging signals.
_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "this", "that", "how", "what",
    "από", "και", "για", "στο", "στη", "στην", "τον", "την", "του", "της",
    "τα", "το", "μου", "σας", "μας", "ένα", "μια", "είναι", "vlog", "video",
    "2024", "2025", "2026",
}

MAX_SERP_RESULTS = 8
MAX_DEEP_SCRAPES = 5


class CompetitorAnalyzer:
    async def analyze_competitors(self, keyword: str, max_results: int = MAX_SERP_RESULTS) -> str:
        """Full competitive sweep for a keyword. Returns a structured text
        report (SERP snapshot + deep profiles + packaging intelligence)."""
        if not keyword:
            return "No focus keyword provided for competitor search."

        print(f"[*] [Skill: CompetitorAnalyzer] Launching deep competitor sweep for: '{keyword}' ...")
        serp_entries = await self._search_youtube(keyword, max_results)
        if not serp_entries:
            return f"No competitor videos found for keyword: '{keyword}'."

        print(f"[+] [Skill: CompetitorAnalyzer] SERP captured: {len(serp_entries)} ranking videos. Deep-scraping top {min(len(serp_entries), MAX_DEEP_SCRAPES)}...")

        # Deep-scrape the top videos concurrently for tags + descriptions.
        deep_targets = serp_entries[:MAX_DEEP_SCRAPES]
        details = await asyncio.gather(
            *(self._scrape_video_details(f"https://www.youtube.com/watch?v={e['video_id']}") for e in deep_targets),
            return_exceptions=True,
        )
        for entry, detail in zip(deep_targets, details):
            if isinstance(detail, BaseException) or not detail:
                continue
            entry["tags"] = detail.get("keywords", [])
            entry["description"] = detail.get("description", "")

        return self._build_report(keyword, serp_entries)

    # ------------------------------------------------------------------ #
    # SERP scraping
    # ------------------------------------------------------------------ #
    async def _search_youtube(self, keyword: str, max_results: int) -> list:
        query = urllib.parse.quote_plus(keyword)
        url = f"https://www.youtube.com/results?search_query={query}"
        try:
            async with httpx.AsyncClient(headers=_HEADERS, cookies=_COOKIES, timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception as e:
            print(f"[-] [Skill: CompetitorAnalyzer] Error searching YouTube: {e}")
            return []

        data = self._extract_json(response.text, "ytInitialData")
        if not data:
            return []

        entries = []
        try:
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for content_item in contents:
                for item in content_item.get("itemSectionRenderer", {}).get("contents", []):
                    vr = item.get("videoRenderer")
                    if not vr or not vr.get("videoId"):
                        continue
                    entries.append(
                        {
                            "video_id": vr["videoId"],
                            "title": self._runs_text(vr.get("title")),
                            "channel": self._runs_text(vr.get("ownerText")),
                            "views": self._simple_text(vr.get("viewCountText")),
                            "published": self._simple_text(vr.get("publishedTimeText")),
                            "duration": self._simple_text(vr.get("lengthText")),
                            "tags": [],
                            "description": "",
                        }
                    )
                    if len(entries) >= max_results:
                        return entries
        except Exception as e:
            print(f"[-] [Skill: CompetitorAnalyzer] Error parsing SERP structure: {e}")
        return entries

    async def _scrape_video_details(self, url: str) -> dict:
        try:
            async with httpx.AsyncClient(headers=_HEADERS, cookies=_COOKIES, timeout=15.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
        except Exception as e:
            print(f"[-] [Skill: CompetitorAnalyzer] Error scraping details for {url}: {e}")
            return {}

        player_data = self._extract_json(response.text, "ytInitialPlayerResponse")
        if not player_data:
            return {}
        video_details = player_data.get("videoDetails", {})
        return {
            "description": video_details.get("shortDescription", ""),
            "keywords": video_details.get("keywords", []),
        }

    # ------------------------------------------------------------------ #
    # Report building
    # ------------------------------------------------------------------ #
    def _build_report(self, keyword: str, entries: list) -> str:
        serp_lines = []
        for i, e in enumerate(entries, 1):
            serp_lines.append(
                f"{i}. \"{e['title']}\" — {e['channel']} | {e['views']} | {e['published']} | {e['duration']}"
            )

        profiles = []
        for i, e in enumerate(entries[:MAX_DEEP_SCRAPES], 1):
            tags = ", ".join(e["tags"][:25]) if e["tags"] else "None visible"
            desc = (e["description"] or "N/A")[:400]
            profiles.append(
                f"### Competitor #{i}: {e['title']}\n"
                f"* **URL**: https://www.youtube.com/watch?v={e['video_id']}\n"
                f"* **Channel**: {e['channel']} | **Views**: {e['views']} | **Age**: {e['published']} | **Length**: {e['duration']}\n"
                f"* **Hidden Tags**: {tags}\n"
                f"* **Description Snippet**:\n{desc}..."
            )

        intelligence = self._packaging_intelligence(entries)

        return (
            f"## LIVE YOUTUBE SERP SNAPSHOT (query: '{keyword}')\n"
            "The algorithm currently rewards these videos for this exact search:\n"
            + "\n".join(serp_lines)
            + "\n\n## DEEP COMPETITOR PROFILES\n"
            + "\n\n".join(profiles)
            + f"\n\n## PACKAGING INTELLIGENCE (auto-computed patterns of the winners)\n{intelligence}"
        )

    @staticmethod
    def _packaging_intelligence(entries: list) -> str:
        titles = [e["title"] for e in entries if e.get("title")]
        if not titles:
            return "Not enough data to compute patterns."

        word_counter: Counter = Counter()
        for title in titles:
            for word in re.findall(r"[\w']+", title.lower()):
                if len(word) > 2 and word not in _STOPWORDS:
                    word_counter[word] += 1
        recurring_words = [f"{w} (x{c})" for w, c in word_counter.most_common(12) if c >= 2]

        tag_counter: Counter = Counter()
        for e in entries:
            for tag in e.get("tags", []):
                tag_counter[tag.lower().strip()] += 1
        shared_tags = [f"{t} (x{c})" for t, c in tag_counter.most_common(15) if c >= 2]

        avg_len = round(sum(len(t) for t in titles) / len(titles))
        lines = [
            f"- Average competitor title length: {avg_len} characters.",
            "- Recurring title words among ranking videos: "
            + (", ".join(recurring_words) if recurring_words else "no strong repetition — the SERP is diverse, a unique angle can win."),
            "- Tags reused by multiple winners (steal-worthy semantic core): "
            + (", ".join(shared_tags) if shared_tags else "no shared tags detected."),
            "- STRATEGY: cover the shared semantic core in tags/description, but differentiate the title angle from the recurring words above to stand out in the same SERP.",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_json(html: str, var_name: str) -> dict:
        """Extracts a big JS JSON blob (ytInitialData / ytInitialPlayerResponse)."""
        for pattern in (
            rf"{var_name}\s*=\s*({{.+?}});",
            rf"{var_name}\s*=\s*({{.+?}})\s*;</script>",
        ):
            match = re.search(pattern, html)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return {}

    @staticmethod
    def _runs_text(node) -> str:
        """Reads YouTube's {runs: [{text: ...}]} text structure."""
        if not node:
            return ""
        runs = node.get("runs", [])
        return "".join(r.get("text", "") for r in runs).strip()

    @staticmethod
    def _simple_text(node) -> str:
        """Reads YouTube's {simpleText: ...} text structure."""
        if not node:
            return ""
        return node.get("simpleText", "") or CompetitorAnalyzer._runs_text(node)
