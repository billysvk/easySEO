import re
import json
import httpx
import urllib.parse
from bs4 import BeautifulSoup

class CompetitorAnalyzer:
    def __init__(self):
        pass

    async def analyze_competitors(self, keyword: str, max_results: int = 3) -> str:
        """
        Searches YouTube for the target keyword, scrapes metadata for the top 3 ranking videos,
        and constructs a detailed structured text summary of competitor packaging for prompt optimization.
        """
        if not keyword:
            return "No focus keyword provided for competitor search."

        print(f"[*] [Skill: CompetitorAnalyzer] Launching competitor search for: '{keyword}'...")
        video_ids = await self._search_youtube_videos(keyword, max_results)
        if not video_ids:
            return f"No competitor videos found for keyword: '{keyword}'."

        print(f"[+] [Skill: CompetitorAnalyzer] Found {len(video_ids)} ranking videos. Scraping metadata...")
        
        competitor_profiles = []
        for i, video_id in enumerate(video_ids):
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            metadata = await self._scrape_video_details(video_url)
            
            profile = f"""### Competitor Video #{i+1}
* **Watch URL**: {video_url}
* **Title**: {metadata.get('title', 'N/A')}
* **Keywords/Tags**: {', '.join(metadata.get('keywords', [])) if metadata.get('keywords') else 'None'}
* **Description Snippet**:
{metadata.get('description', 'N/A')[:400]}...
"""
            competitor_profiles.append(profile)

        return "\n\n".join(competitor_profiles)

    async def _search_youtube_videos(self, keyword: str, max_results: int = 3) -> list:
        query = urllib.parse.quote_plus(keyword)
        url = f"https://www.youtube.com/results?search_query={query}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "el,en-US;q=0.9,en;q=0.8"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=15.0)
                response.raise_for_status()

            match = re.search(r'ytInitialData\s*=\s*({.+?});', response.text)
            if not match:
                match = re.search(r'ytInitialData\s*=\s*({.+?})\s*;</script>', response.text)
            if not match:
                match = re.search(r'ytInitialData\s*=\s*(\{.*?\});', response.text, re.DOTALL)

            video_ids = []
            if match:
                data = json.loads(match.group(1))
                contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                
                for content_item in contents:
                    item_section = content_item.get("itemSectionRenderer", {})
                    items = item_section.get("contents", [])
                    for item in items:
                        video_renderer = item.get("videoRenderer", {})
                        if video_renderer:
                            v_id = video_renderer.get("videoId")
                            if v_id and v_id not in video_ids:
                                video_ids.append(v_id)
                                if len(video_ids) >= max_results:
                                    break
                    if len(video_ids) >= max_results:
                        break
            return video_ids
        except Exception as e:
            print(f"[-] [Skill: CompetitorAnalyzer] Error searching YouTube: {e}")
            return []

    async def _scrape_video_details(self, url: str) -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "el,en-US;q=0.9,en;q=0.8"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=15.0, follow_redirects=True)
                response.raise_for_status()

            title = ""
            desc = ""
            keywords = []

            # Try parsing ytInitialPlayerResponse
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', response.text)
            if not match:
                match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;</script>', response.text)
            if not match:
                match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\});', response.text, re.DOTALL)

            if match:
                try:
                    player_data = json.loads(match.group(1))
                    title = player_data.get("videoDetails", {}).get("title", "")
                    desc = player_data.get("videoDetails", {}).get("shortDescription", "")
                    keywords = player_data.get("videoDetails", {}).get("keywords", [])
                except:
                    pass

            # Fallback to BeautifulSoup meta tags
            if not title or not desc or not keywords:
                soup = BeautifulSoup(response.text, "html.parser")
                if not title:
                    title_elem = soup.find("meta", {"property": "og:title"}) or soup.find("meta", {"name": "title"})
                    title = title_elem.get("content", "").strip() if title_elem else ""
                if not desc:
                    desc_elem = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
                    desc = desc_elem.get("content", "").strip() if desc_elem else ""
                if not keywords:
                    keywords_elem = soup.find("meta", {"name": "keywords"})
                    if keywords_elem and keywords_elem.get("content"):
                        keywords = [k.strip() for k in keywords_elem["content"].split(",")]

                if not title and soup.title:
                    title = soup.title.string.strip() if soup.title.string else ""

            return {
                "title": title,
                "description": desc,
                "keywords": keywords
            }
        except Exception as e:
            print(f"[-] [Skill: CompetitorAnalyzer] Error scraping details for {url}: {e}")
            return {}
