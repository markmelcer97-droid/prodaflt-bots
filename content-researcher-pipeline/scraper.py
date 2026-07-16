"""
PRODAFLT Content Researcher Pipeline — Scraper
Handles content extraction from Instagram Reels, TikTok, YouTube Shorts,
and generic web pages.  Falls back to yt-dlp for video downloads.
"""

import asyncio
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx

import config


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORM_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/(?:reel|p|tv)/([^/?]+)"),
    "tiktok": re.compile(r"tiktok\.com/.*(?:video|@[\w.]+/video)/(\d+)"),
    "youtube": re.compile(r"(?:youtube\.com/shorts/|youtu\.be/)([\w-]+)"),
    "facebook": re.compile(r"facebook\.com/.*(?:videos?|reel)/(\d+)"),
}


def detect_platform(url: str) -> Optional[str]:
    """Return platform key or None."""
    lowered = url.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(lowered):
            return platform
    return None


def extract_video_id(url: str) -> Optional[str]:
    """Extract platform-specific video ID."""
    lowered = url.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        m = pattern.search(lowered)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Download helpers (yt-dlp)
# ---------------------------------------------------------------------------

async def download_media(
    url: str,
    output_dir: Path = config.MEDIA_DOWNLOAD_PATH,
    max_duration_sec: int = 120,
) -> Optional[Path]:
    """Download video to local disk using yt-dlp.  Returns path or None."""
    vid = extract_video_id(url) or hashlib.md5(url.encode()).hexdigest()[:12]
    out_template = str(output_dir / f"{vid}.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--max-filesize", "100M",
        "--format", "best[height<=720]/best",
        "--output", out_template,
        "--quiet",
        "--no-warnings",
        url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            return None
    except Exception:
        return None

    # Find downloaded file
    candidates = list(output_dir.glob(f"{vid}.*"))
    for c in candidates:
        if c.suffix in {".mp4", ".webm", ".mkv", ".mov"}:
            return c
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

async def fetch_page_metadata(url: str) -> Dict:
    """Fetch OpenGraph / generic meta tags from a URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text
    except Exception:
        return {"title": None, "description": None, "image": None, "platform": detect_platform(url)}

    def _meta(name: str) -> Optional[str]:
        for pat in [
            re.compile(rf'<meta[^>]+property="og:{name}"[^>]+content="([^"]+)"', re.I),
            re.compile(rf'<meta[^>]+name="{name}"[^>]+content="([^"]+)"', re.I),
            re.compile(rf'<meta[^>]+content="([^"]+)"[^>]+property="og:{name}"', re.I),
        ]:
            m = pat.search(text)
            if m:
                return m.group(1)
        return None

    title = _meta("title") or _meta("twitter:title")
    description = _meta("description") or _meta("twitter:description")
    image = _meta("image") or _meta("twitter:image")

    # Try to infer duration from JSON-LD or meta
    duration = None
    dur_match = re.search(r'"duration"[:\s]*"?PT(\d+)M?(\d*)S?', text)
    if dur_match:
        mins = int(dur_match.group(1) or 0)
        secs = int(dur_match.group(2) or 0)
        duration = mins * 60 + secs

    return {
        "title": title,
        "description": description,
        "image": image,
        "duration": duration,
        "platform": detect_platform(url),
    }


async def fetch_youtube_metadata(video_id: str) -> Dict:
    """Enrich metadata via YouTube oEmbed (no API key required)."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(oembed_url)
            data = resp.json()
            return {
                "title": data.get("title"),
                "author": data.get("author_name"),
                "platform": "youtube",
            }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Instagram-specific (unauthenticated, limited)
# ---------------------------------------------------------------------------

async def fetch_instagram_metadata(url: str) -> Dict:
    """Best-effort metadata for Instagram Reels without full auth."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    if config.INSTAGRAM_SESSION_ID:
        headers["Cookie"] = f"sessionid={config.INSTAGRAM_SESSION_ID}"

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(url, headers=headers)
            text = resp.text
    except Exception:
        return {"platform": "instagram"}

    # Extract from sharedData or meta tags
    title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', text, re.I)
    desc_match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', text, re.I)
    img_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', text, re.I)

    return {
        "title": title_match.group(1) if title_match else None,
        "description": desc_match.group(1) if desc_match else None,
        "image": img_match.group(1) if img_match else None,
        "platform": "instagram",
    }


# ---------------------------------------------------------------------------
# TikTok-specific (unauthenticated, limited)
# ---------------------------------------------------------------------------

async def fetch_tiktok_metadata(url: str) -> Dict:
    """Best-effort metadata for TikTok."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(url, headers=headers)
            text = resp.text
    except Exception:
        return {"platform": "tiktok"}

    title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', text, re.I)
    desc_match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', text, re.I)

    return {
        "title": title_match.group(1) if title_match else None,
        "description": desc_match.group(1) if desc_match else None,
        "platform": "tiktok",
    }


# ---------------------------------------------------------------------------
# Unified scraper entrypoint
# ---------------------------------------------------------------------------

async def scrape_link(url: str) -> Dict:
    """
    Scrape a single URL.
    Returns dict with keys:
      - url, platform, title, description, duration, preview_url, raw_metadata
      - local_media_path (if video downloaded)
    """
    platform = detect_platform(url)
    meta: Dict = {"platform": platform}

    if platform == "youtube":
        vid = extract_video_id(url)
        yt_meta = await fetch_youtube_metadata(vid) if vid else {}
        meta.update(yt_meta)
    elif platform == "instagram":
        ig_meta = await fetch_instagram_metadata(url)
        meta.update(ig_meta)
    elif platform == "tiktok":
        tt_meta = await fetch_tiktok_metadata(url)
        meta.update(tt_meta)
    else:
        generic = await fetch_page_metadata(url)
        meta.update(generic)

    # Download media for video platforms
    local_media_path: Optional[Path] = None
    if platform in {"youtube", "tiktok", "instagram", "facebook"}:
        local_media_path = await download_media(url)

    return {
        "url": url,
        "platform": meta.get("platform") or platform,
        "title": meta.get("title"),
        "description": meta.get("description"),
        "duration": meta.get("duration"),
        "preview_url": meta.get("image"),
        "raw_metadata": meta,
        "local_media_path": str(local_media_path) if local_media_path else None,
    }


async def batch_scrape(urls: List[str]) -> List[Dict]:
    """Scrape multiple URLs concurrently with rate limiting."""
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent downloads

    async def _scrape(u: str) -> Dict:
        async with semaphore:
            return await scrape_link(u)

    results = await asyncio.gather(*[_scrape(u) for u in urls])
    return list(results)
