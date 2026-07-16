"""
PRODAFLT Parser Bot — Link Parser Utilities
Extracts URLs, detects platform, fetches metadata.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Platform patterns
# ------------------------------------------------------------------

PLATFORM_PATTERNS = {
    "instagram": r"instagram\.com|instagr\.am",
    "tiktok": r"tiktok\.com|vm\.tiktok\.com",
    "youtube": r"youtube\.com|youtu\.be",
    "facebook": r"facebook\.com|fb\.watch",
    "twitter": r"twitter\.com|x\.com|t\.co",
    "pinterest": r"pinterest\.",
    "snapchat": r"snapchat\.com",
    "reddit": r"reddit\.com|redd\.it",
    "telegram": r"t\.me|telegram\.me",
    "linkedin": r"linkedin\.com",
}

URL_REGEX = re.compile(
    r"https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ip
    r"(?::\d+)?"  # port
    r"(?:/?|[/?]\S+)",
    re.IGNORECASE,
)


def extract_urls(text: str) -> List[str]:
    """Return all HTTP(S) URLs found in text."""
    if not text:
        return []
    matches = URL_REGEX.findall(text)
    # dedupe while preserving order
    seen = set()
    unique = []
    for url in matches:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def detect_platform(url: str) -> Optional[str]:
    """Detect platform from URL hostname / path."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
    except Exception:
        return None

    for platform, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, netloc, re.IGNORECASE):
            return platform
    return "other"


def normalize_url(url: str) -> str:
    """Basic URL normalization (strip tracking params)."""
    try:
        parsed = urlparse(url)
        # Remove common tracking params
        query = parsed.query
        if query:
            # Keep only non-tracking params
            tracking = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                        "utm_content", "fbclid", "gclid", "ttclid", "igshid"}
            # Simple approach: strip entire query for social media
            if any(x in parsed.netloc.lower() for x in ["instagram", "tiktok", "youtube", "youtu.be"]):
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return url
    except Exception:
        return url


async def fetch_page_title(session: aiohttp.ClientSession, url: str, timeout: int = 8) -> Optional[str]:
    """Attempt to fetch <title> from URL."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=False) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None
            html = await resp.text(errors="ignore")
            # Simple regex for <title>
            match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up
                title = re.sub(r"\s+", " ", title)
                return title[:500] if len(title) > 500 else title
    except Exception as e:
        logger.debug("Could not fetch title for %s: %s", url, e)
    return None


async def enrich_link_data(session: aiohttp.ClientSession, url: str) -> Dict:
    """
    Build link record dict with platform detection + optional title fetch.
    Does NOT hit DB — pure data extraction.
    """
    platform = detect_platform(url)
    normalized = normalize_url(url)

    data = {
        "url": normalized,
        "platform": platform,
        "title": None,
        "description": None,
        "duration": None,
        "preview_url": None,
        "metadata": {"original_url": url},
    }

    # Try to get title (best effort, not blocking)
    if platform in ("instagram", "tiktok", "youtube", "twitter", "facebook"):
        # Social media often blocks; skip to save time
        logger.debug("Skipping title fetch for %s: %s", platform, url)
    else:
        title = await fetch_page_title(session, url)
        if title:
            data["title"] = title

    return data


async def process_message_text(session: aiohttp.ClientSession, text: str) -> List[Dict]:
    """
    Given a message text, extract all URLs and enrich each.
    Returns list of link dicts ready for DB insert.
    """
    urls = extract_urls(text)
    results = []
    for url in urls:
        data = await enrich_link_data(session, url)
        results.append(data)
    return results
