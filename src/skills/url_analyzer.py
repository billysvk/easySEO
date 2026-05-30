import re
import json
import httpx
from bs4 import BeautifulSoup

BODY_TEXT_CAP = 4000


class URLAnalyzer:
    def __init__(self):
        pass

    def analyze_url(self, url: str) -> str:
        """
        Fetches a reference/competitor URL and extracts SEO-relevant signals:
        title, meta description, Open Graph tags, keywords and headings.

        For YouTube links (youtu.be / youtube.com) the og:title / og:description
        are server-rendered, so this surfaces the competitor's actual packaging
        even though the visible page is JS-heavy.
        """
        print(f"[*] [Skill: URLAnalyzer] Fetching external reference URL: {url}")
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
            meta_desc = self._meta(soup, name="description")
            keywords = self._meta(soup, name="keywords")
            og_title = self._meta(soup, prop="og:title")
            og_desc = self._meta(soup, prop="og:description")

            headings = []
            for tag in soup.find_all(["h1", "h2"]):
                text = tag.get_text(strip=True)
                if text:
                    headings.append(f"- {text}")
                if len(headings) >= 15:
                    break

            paragraphs = [p.get_text().strip() for p in soup.find_all("p")]
            body_text = "\n".join(p for p in paragraphs if p)[:BODY_TEXT_CAP]

            # UnicodeEncodeError can't fire here (stdout is hardened to utf-8 in
            # settings), but keep a defensive guard for unusual stream configs.
            try:
                print(f"[+] [Skill: URLAnalyzer] Parsed reference. Title: '{title}'")
            except UnicodeEncodeError:
                print("[+] [Skill: URLAnalyzer] Parsed reference (title contains non-ASCII).")

            parts = [
                f"Source URL: {url}",
                f"Page Title: {title}",
            ]
            if og_title:
                parts.append(f"OG Title (competitor packaging): {og_title}")
            if meta_desc or og_desc:
                parts.append(f"Meta/OG Description: {meta_desc or og_desc}")
            if keywords:
                parts.append(f"Meta Keywords: {keywords}")
            if headings:
                parts.append("Headings (H1/H2):\n" + "\n".join(headings))
            if body_text:
                parts.append(f"Body Snippet:\n{body_text}")

            return "\n".join(parts)
        except Exception as e:
            return f"Failed to fetch or parse reference URL ({url}): {e}"

    def scrape_video_metadata(self, url: str) -> dict:
        """
        Fetches and extracts metadata (title, description) from a video URL.
        For YouTube videos, it parses ytInitialPlayerResponse to retrieve the
        complete, multi-line video description. Otherwise, it falls back to
        Open Graph and meta tags.
        """
        print(f"[*] [Skill: URLAnalyzer] Scraping video metadata from URL: {url}")
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "el,en-US;q=0.9,en;q=0.8"
            }
            response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
            response.raise_for_status()

            og_title = ""
            og_desc = ""

            # Check if this is a YouTube URL
            is_youtube = "youtube.com" in url or "youtu.be" in url

            views = "0"
            publish_date = ""
            author = ""

            if is_youtube:
                # Attempt to extract full description and title from YouTube's player response JSON
                match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', response.text)
                if not match:
                    match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;</script>', response.text)
                if not match:
                    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\});', response.text, re.DOTALL)
                
                if match:
                    try:
                        player_data = json.loads(match.group(1))
                        og_desc = player_data.get("videoDetails", {}).get("shortDescription", "")
                        og_title = player_data.get("videoDetails", {}).get("title", "")
                        views = player_data.get("videoDetails", {}).get("viewCount", "0")
                        author = player_data.get("videoDetails", {}).get("author", "")
                        publish_date = player_data.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "")
                        print(f"[+] [Skill: URLAnalyzer] Extracted full description, title and public stats (Views: {views}) from YouTube player response.")
                    except Exception as json_err:
                        print(f"[*] [Skill: URLAnalyzer] Could not parse ytInitialPlayerResponse JSON: {json_err}")

            # Fallback to BeautifulSoup if YouTube JSON extraction failed or for non-YouTube URLs
            if not og_title or not og_desc:
                soup = BeautifulSoup(response.text, "html.parser")
                if not og_title:
                    og_title = self._meta(soup, prop="og:title") or self._meta(soup, name="title")
                if not og_desc:
                    og_desc = self._meta(soup, prop="og:description") or self._meta(soup, name="description")
                
                # Ultimate fallback for title
                if not og_title and soup.title:
                    og_title = soup.title.string.strip() if soup.title.string else ""

            return {
                "title": og_title.strip() if og_title else "",
                "description": og_desc.strip() if og_desc else "",
                "views": views,
                "author": author,
                "publish_date": publish_date,
                "success": True
            }
        except Exception as e:
            print(f"[-] [Skill: URLAnalyzer] Error scraping video metadata: {e}")
            return {
                "title": "",
                "description": "",
                "views": "0",
                "author": "",
                "publish_date": "",
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def _meta(soup: BeautifulSoup, name: str = None, prop: str = None) -> str:
        """Reads a <meta> tag's content by name= or property= (Open Graph)."""
        attrs = {"name": name} if name else {"property": prop}
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""
