import httpx
from bs4 import BeautifulSoup

class URLAnalyzer:
    def __init__(self):
        pass

    def analyze_url(self, url: str) -> str:
        """
        Fetches the web URL and extracts main contents, headers, or metadata.
        """
        print(f"[*] [Skill: URLAnalyzer] Fetching external reference URL: {url}")
        try:
            # Using HTTPX client
            headers = {"User-Agent": "easySEO-Agent/1.0 (YouTube SEO CLI)"}
            response = httpx.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            # Parsing HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract basic tags
            title = soup.title.string.strip() if soup.title else "No Title"
            
            # Simple text content extraction
            paragraphs = [p.get_text().strip() for p in soup.find_all("p")]
            clean_text = "\n".join([p for p in paragraphs if p])[:5000] # Cap text
            
            print(f"[+] [Skill: URLAnalyzer] Successfully parsed URL title: '{title}'")
            return f"Source URL: {url}\nTitle: {title}\nContent Snippet:\n{clean_text}"
        except Exception as e:
            return f"Failed to fetch or parse reference URL ({url}): {e}"
