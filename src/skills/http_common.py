"""Shared HTTP constants for all scraping skills.

The consent cookies matter: without them YouTube redirects EU traffic to
consent.youtube.com and the page contains no ytInitialData at all.
"""

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "el,en-US;q=0.9,en;q=0.8",
}

CONSENT_COOKIES = {
    "CONSENT": "YES+cb.20240101-00-p0.en+FX+100",
    "SOCS": "CAISAiAD",
}
