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
                    "Mozilla/5.0 (compatible; easySEO-Agent/1.0; YouTube SEO CLI)"
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

    @staticmethod
    def _meta(soup: BeautifulSoup, name: str = None, prop: str = None) -> str:
        """Reads a <meta> tag's content by name= or property= (Open Graph)."""
        attrs = {"name": name} if name else {"property": prop}
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""
