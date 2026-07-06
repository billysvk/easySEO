"""TrendHunter — keyless search-demand & trend intelligence.

Gathers everything the public internet reveals about what people are
searching for around the video's topic, without needing any API key:

1. YouTube search autocomplete (suggestqueries.google.com, ds=yt)
   - direct suggestions for the focus keyword
   - question/intent expansions ("how", "why", "best", "vs", Greek variants)
   - alphabet soup expansion (keyword + a..z) for long-tail discovery
2. Google web autocomplete (what people search on Google, feeds YT search too)
3. Google Trends "trending now" RSS (geo-targeted) to catch anything
   currently viral that can be tied into the packaging.

Everything is fetched concurrently and condensed into a single structured
text block ready to be injected into the LLM prompt.
"""

import asyncio
import json
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "el,en-US;q=0.9,en;q=0.8",
}

# Intent prefixes/suffixes that surface high-value long-tail queries.
_INTENT_MODIFIERS_EN = ["how to", "best", "why", "vs", "guide", "tips"]
_INTENT_MODIFIERS_EL = ["πως", "γιατι", "καλυτερα", "οδηγος", "τι να"]

_ALPHABET_EL = "αβγδεκλμνπστ"
_ALPHABET_EN = "abcdefghistw"

MAX_SUGGESTIONS_PER_QUERY = 8
MAX_TOTAL_SUGGESTIONS = 80


class TrendHunter:
    async def hunt(self, keyword: str, geo: str = "GR") -> str:
        """Runs the full trend sweep for a focus keyword and returns a
        structured text report for the prompt."""
        keyword = (keyword or "").strip()
        if not keyword:
            return "No focus keyword available - trend analysis skipped."

        # Use only the primary keyword (before any comma) as the seed.
        seed = keyword.split(",")[0].strip()
        print(f"[*] [Skill: TrendHunter] Sweeping search demand & trends for seed: '{seed}' ...")

        async with httpx.AsyncClient(headers=_HEADERS, timeout=10.0) as client:
            tasks = [
                self._youtube_suggestions_sweep(client, seed),
                self._google_suggestions(client, seed),
                self._google_trending_now(client, geo),
            ]
            yt_suggestions, g_suggestions, trending_now = await asyncio.gather(
                *tasks, return_exceptions=True
            )

        # Normalize exceptions to empty results so one failed source never
        # kills the sweep.
        if isinstance(yt_suggestions, BaseException):
            print(f"[!] [Skill: TrendHunter] YouTube suggest sweep failed: {yt_suggestions}")
            yt_suggestions = []
        if isinstance(g_suggestions, BaseException):
            print(f"[!] [Skill: TrendHunter] Google suggest failed: {g_suggestions}")
            g_suggestions = []
        if isinstance(trending_now, BaseException):
            print(f"[!] [Skill: TrendHunter] Google Trends RSS failed: {trending_now}")
            trending_now = []

        print(
            f"[+] [Skill: TrendHunter] Collected {len(yt_suggestions)} YouTube long-tail queries, "
            f"{len(g_suggestions)} Google queries, {len(trending_now)} trending topics."
        )

        parts = [f"Focus keyword seed: '{seed}'"]
        if yt_suggestions:
            parts.append(
                "REAL YOUTUBE SEARCH QUERIES (live autocomplete - what people actually type "
                "in YouTube search right now, ordered by relevance):\n"
                + "\n".join(f"- {s}" for s in yt_suggestions)
            )
        if g_suggestions:
            parts.append(
                "REAL GOOGLE SEARCH QUERIES (live autocomplete - Google search demand that "
                "also feeds YouTube results in Google SERP):\n"
                + "\n".join(f"- {s}" for s in g_suggestions)
            )
        if trending_now:
            parts.append(
                f"CURRENTLY TRENDING SEARCHES ({geo} - Google Trends right now; tie the video "
                "into any topic here ONLY if genuinely relevant):\n"
                + "\n".join(f"- {t}" for t in trending_now)
            )
        if len(parts) == 1:
            parts.append("No live trend data could be fetched (offline or blocked).")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # YouTube autocomplete
    # ------------------------------------------------------------------ #
    async def _youtube_suggestions_sweep(self, client: httpx.AsyncClient, seed: str) -> list:
        """Direct + intent-modified + alphabet-soup autocomplete sweep."""
        is_greek = any("Ͱ" <= ch <= "Ͽ" for ch in seed)
        modifiers = _INTENT_MODIFIERS_EL if is_greek else _INTENT_MODIFIERS_EN
        alphabet = _ALPHABET_EL if is_greek else _ALPHABET_EN

        queries = [seed]
        queries += [f"{m} {seed}" for m in modifiers[:4]]
        queries += [f"{seed} {c}" for c in alphabet]

        results = await asyncio.gather(
            *(self._fetch_suggestions(client, q, ds="yt") for q in queries),
            return_exceptions=True,
        )

        seen: dict[str, None] = {}
        for res in results:
            if isinstance(res, BaseException):
                continue
            for suggestion in res[:MAX_SUGGESTIONS_PER_QUERY]:
                key = suggestion.lower().strip()
                if key and key != seed.lower() and key not in seen:
                    seen[key] = None
                if len(seen) >= MAX_TOTAL_SUGGESTIONS:
                    break
        return list(seen.keys())

    async def _google_suggestions(self, client: httpx.AsyncClient, seed: str) -> list:
        suggestions = await self._fetch_suggestions(client, seed, ds="")
        return suggestions[:15]

    @staticmethod
    async def _fetch_suggestions(client: httpx.AsyncClient, query: str, ds: str = "yt") -> list:
        """Hits Google's public suggest endpoint (the same one the YouTube
        search box uses when ds=yt). Returns a list of suggestion strings."""
        params = {"client": "firefox", "q": query, "hl": "el"}
        if ds:
            params["ds"] = ds
        url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(params)
        response = await client.get(url)
        response.raise_for_status()
        # Response is JSON: ["query", ["suggestion1", "suggestion2", ...]]
        data = json.loads(response.content.decode("utf-8", errors="replace"))
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
            return [s for s in data[1] if isinstance(s, str)]
        return []

    # ------------------------------------------------------------------ #
    # Google Trends
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _google_trending_now(client: httpx.AsyncClient, geo: str) -> list:
        """Fetches the 'Trending now' RSS feed for the target country."""
        url = f"https://trends.google.com/trending/rss?geo={geo}"
        response = await client.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        titles = []
        for item in root.iter("item"):
            title_elem = item.find("title")
            traffic_elem = item.find("{https://trends.google.com/trending/rss}approx_traffic")
            if title_elem is not None and title_elem.text:
                label = title_elem.text.strip()
                if traffic_elem is not None and traffic_elem.text:
                    label += f" (~{traffic_elem.text.strip()} searches)"
                titles.append(label)
            if len(titles) >= 15:
                break
        return titles
