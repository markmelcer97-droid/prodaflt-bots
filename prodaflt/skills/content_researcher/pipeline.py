"""
PRODAFLT Content Researcher Pipeline — Main Orchestrator
End-to-end flow:  fetch pending links → scrape → classify → score → video analyze → persist.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

import config
from classifier import ClassificationResult, classify_content
from db import (
    ContentAnalysis,
    Link,
    LinkStatus,
    fetch_pending_links,
    get_session,
    upsert_pattern,
)
from scorer import score_from_classification
from scraper import batch_scrape, scrape_link
from video_analyzer import analyze_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("content-researcher-pipeline")

# Thread pool for CPU-intensive video analysis
_video_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="video-analysis")


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

async def step_fetch_links(session: AsyncSession, limit: int = config.DAILY_LINK_LIMIT) -> List[Link]:
    """Fetch pending links from DB."""
    links = await fetch_pending_links(session, limit=limit)
    logger.info(f"Fetched {len(links)} pending links")
    return links


async def step_scrape(links: List[Link]) -> Dict[int, Dict]:
    """Scrape all links concurrently.  Returns {link_id: scrape_result}."""
    urls = [link.url for link in links]
    results = await batch_scrape(urls)
    return {link.link_id: res for link, res in zip(links, results)}


async def step_classify(
    session: AsyncSession,
    links: List[Link],
    scraped: Dict[int, Dict],
) -> Dict[int, ClassificationResult]:
    """Classify each scraped result.  Returns {link_id: classification}."""
    out = {}
    for link in links:
        res = scraped.get(link.link_id, {})
        classification = classify_content(
            title=res.get("title") or link.title,
            description=res.get("description") or link.description,
            transcript=res.get("transcript"),
            metadata=res.get("raw_metadata"),
        )
        out[link.link_id] = classification
    logger.info(f"Classified {len(out)} items")
    return out


async def step_score(
    classifications: Dict[int, ClassificationResult],
    scraped: Dict[int, Dict],
) -> Dict[int, Dict]:
    """Calculate scores for each classified item."""
    out = {}
    for link_id, clf in classifications.items():
        meta = scraped.get(link_id, {})
        score_result = score_from_classification(
            classification={
                "hook_text": clf.hook_text,
                "cta_text": clf.cta_text,
                "detected_patterns": clf.detected_patterns,
            },
            platform=meta.get("platform"),
            duration_sec=meta.get("duration"),
            has_transcript=bool(meta.get("transcript")),
        )
        out[link_id] = score_result
    logger.info(f"Scored {len(out)} items")
    return out


def _sync_video_analyze(links: List[Link], scraped: Dict[int, Dict]) -> Dict[int, Optional[Dict]]:
    """Synchronous wrapper for video analysis (runs in thread pool)."""
    out = {}
    for link in links:
        res = scraped.get(link.link_id, {})
        media_path = res.get("local_media_path")
        if media_path and Path(media_path).exists():
            try:
                analysis = analyze_video(Path(media_path))
                out[link.link_id] = analysis
            except Exception as exc:
                logger.warning(f"Video analysis failed for link {link.link_id}: {exc}")
                out[link.link_id] = None
        else:
            out[link.link_id] = None
    logger.info(f"Analyzed video for {sum(1 for v in out.values() if v)} items")
    return out


async def step_video_analyze(
    links: List[Link],
    scraped: Dict[int, Dict],
) -> Dict[int, Optional[Dict]]:
    """Run video analysis for items with downloaded media (offloads to thread pool)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_video_executor, _sync_video_analyze, links, scraped)


async def step_persist(
    session: AsyncSession,
    links: List[Link],
    classifications: Dict[int, ClassificationResult],
    scores: Dict[int, Dict],
    video_analyses: Dict[int, Optional[Dict]],
) -> List[ContentAnalysis]:
    """Persist analysis results to DB: content_analysis + patterns."""
    persisted = []

    for link in links:
        link_id = link.link_id
        clf = classifications.get(link_id)
        score = scores.get(link_id, {})
        video = video_analyses.get(link_id)

        if not clf:
            continue

        # Build ContentAnalysis record
        analysis = ContentAnalysis(
            link_id=link_id,
            pattern=clf.format_name,
            researcher_comment=clf.reasoning,
            creative_potential=int(score.get("final_score", 5)),
            virality_score=score.get("virality_score"),
            adaptation_potential=score.get("adaptation_potential"),
            final_score=score.get("final_score"),
            content_format=clf.format_name,
            hook_text=video.get("hook_text") if video else clf.hook_text,
            cta_text=video.get("cta_text") if video else clf.cta_text,
            visual_tags=clf.visual_tags,
            audio_transcript=video.get("transcription", {}).get("full_text") if video else None,
            frame_timestamps=[
                {"ts": f["timestamp"], "tags": f["tags"]}
                for f in video.get("frames", [])
            ] if video else None,
        )
        session.add(analysis)
        persisted.append(analysis)

        # Update link status
        link.status = LinkStatus.analyzed

        # Upsert pattern
        await upsert_pattern(
            session,
            name=clf.format_name,
            description=FORMAT_DESCRIPTIONS.get(clf.format_name, ""),
            examples=[{"url": link.url, "score": score.get("final_score")}],
        )

    await session.commit()
    logger.info(f"Persisted {len(persisted)} analyses")
    return persisted


# Format description lookup for pattern upserts
FORMAT_DESCRIPTIONS = {
    "newsjacking": "Exploits breaking news / viral events to grab attention.",
    "fake_podcast": "Simulates podcast/TV interview with authority figure.",
    "ugc_testimonial": "User-generated content showing 'real' win or experience.",
    "money_counter": "Visual counter / stack growing rapidly.",
    "fake_live": "Simulates live stream with fake comments and reactions.",
    "challenge": "Social challenge with progression and reward promise.",
    "transformation": "Before/after lifestyle transformation linked to gambling win.",
    "fomo_urgency": "Scarcity / limited-time offer creating FOMO.",
    "educational_hook": "Teaches a 'strategy' or 'secret' then pivots to CTA.",
}


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------

async def run_pipeline(limit: int = config.DAILY_LINK_LIMIT) -> List[ContentAnalysis]:
    """
    Full pipeline: fetch → scrape → classify → score → video analyze → persist.
    Returns list of persisted ContentAnalysis records.
    """
    async with get_session() as session:
        # 1. Fetch
        links = await step_fetch_links(session, limit=limit)
        if not links:
            logger.info("No pending links to process")
            return []

        # 2. Scrape
        scraped = await step_scrape(links)

        # 3. Classify
        classifications = await step_classify(session, links, scraped)

        # 4. Score
        scores = await step_score(classifications, scraped)

        # 5. Video analysis (CPU-intensive, runs in thread pool)
        video_analyses = await step_video_analyze(links, scraped)

        # 6. Persist
        persisted = await step_persist(session, links, classifications, scores, video_analyses)
        return persisted


async def run_pipeline_for_url(url: str, added_by: Optional[int] = None) -> Optional[ContentAnalysis]:
    """
    One-off pipeline for a single URL (e.g., manual research request).
    """
    async with get_session() as session:
        # Insert link
        link = Link(url=url, status=LinkStatus.processing, added_by=added_by)
        session.add(link)
        await session.flush()

        # Scrape
        scraped = await scrape_link(url)

        # Classify
        classification = classify_content(
            title=scraped.get("title"),
            description=scraped.get("description"),
            transcript=scraped.get("transcript"),
            metadata=scraped.get("raw_metadata"),
        )

        # Score
        score_result = score_from_classification(
            classification={
                "hook_text": classification.hook_text,
                "cta_text": classification.cta_text,
                "detected_patterns": classification.detected_patterns,
            },
            platform=scraped.get("platform"),
        )

        # Video analysis
        video_analysis = None
        media_path = scraped.get("local_media_path")
        if media_path and Path(media_path).exists():
            try:
                video_analysis = analyze_video(Path(media_path))
            except Exception as exc:
                logger.warning(f"Video analysis failed: {exc}")

        # Persist
        analysis = ContentAnalysis(
            link_id=link.link_id,
            pattern=classification.format_name,
            researcher_comment=classification.reasoning,
            creative_potential=int(score_result.get("final_score", 5)),
            virality_score=score_result.get("virality_score"),
            adaptation_potential=score_result.get("adaptation_potential"),
            final_score=score_result.get("final_score"),
            content_format=classification.format_name,
            hook_text=video_analysis.get("hook_text") if video_analysis else classification.hook_text,
            cta_text=video_analysis.get("cta_text") if video_analysis else classification.cta_text,
            visual_tags=classification.visual_tags,
            audio_transcript=video_analysis.get("transcription", {}).get("full_text") if video_analysis else None,
            frame_timestamps=[
                {"ts": f["timestamp"], "tags": f["tags"]}
                for f in video_analysis.get("frames", [])
            ] if video_analysis else None,
        )
        session.add(analysis)
        link.status = LinkStatus.analyzed
        await session.commit()

        return analysis


async def get_top_references(min_score: float = config.SCORE_THRESHOLD, limit: int = 15) -> List[Dict]:
    """
    Fetch top-scored analyses from DB with full link info.
    """
    async with get_session() as session:
        from db import fetch_top_scored
        analyses = await fetch_top_scored(session, min_score=min_score, limit=limit)

        results = []
        for a in analyses:
            results.append({
                "analysis_id": a.id,
                "link_id": a.link_id,
                "url": a.link.url if a.link else None,
                "platform": a.link.platform if a.link else None,
                "format": a.content_format,
                "pattern": a.pattern,
                "virality_score": float(a.virality_score) if a.virality_score else None,
                "adaptation_potential": float(a.adaptation_potential) if a.adaptation_potential else None,
                "final_score": float(a.final_score) if a.final_score else None,
                "hook_text": a.hook_text,
                "cta_text": a.cta_text,
                "visual_tags": a.visual_tags,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
        return results
