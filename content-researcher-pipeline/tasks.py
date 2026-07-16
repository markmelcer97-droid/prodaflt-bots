"""
PRODAFLT Content Researcher Pipeline — Scheduled Tasks
Runs the pipeline on a schedule and can be triggered manually.
Designed for integration with APScheduler or cron.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Optional

import httpx

import config
from pipeline import get_top_references, run_pipeline, run_pipeline_for_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("content-researcher-tasks")


# ---------------------------------------------------------------------------
# Daily auto-scraping task
# ---------------------------------------------------------------------------

async def task_daily_research(limit: int = config.DAILY_LINK_LIMIT) -> None:
    """
    Daily scheduled task:
      1. Run pipeline on pending links
      2. Filter top N by final score
      3. Send summary to Router Bot (Telegram) or webhook
    """
    logger.info(f"=== Daily Research Started at {datetime.utcnow().isoformat()} ===")

    # Run pipeline
    analyses = await run_pipeline(limit=limit)

    if not analyses:
        logger.info("No new analyses produced")
        await _send_notification("📋 Daily Research: No pending links to process.")
        return

    # Get top references
    top = await get_top_references(min_score=config.SCORE_THRESHOLD, limit=15)

    # Build report
    lines = [f"📊 *Daily Research Report* — {datetime.utcnow().strftime('%Y-%m-%d')}", ""]
    lines.append(f"Processed: {len(analyses)} links")
    lines.append(f"Top references (score ≥ {config.SCORE_THRESHOLD}): {len(top)}")
    lines.append("")

    for i, ref in enumerate(top[:10], 1):
        score = ref.get("final_score", "N/A")
        fmt = ref.get("format", "unknown")
        platform = ref.get("platform", "unknown")
        url = ref.get("url", "")
        hook = (ref.get("hook_text") or "")[:60]
        lines.append(
            f"{i}. *{fmt}* | {platform} | Score: {score}\n"
            f"   Hook: {hook}...\n"
            f"   {url[:80]}"
        )

    report = "\n".join(lines)
    await _send_notification(report)
    logger.info(f"=== Daily Research Complete: {len(analyses)} processed, {len(top)} top ===")


# ---------------------------------------------------------------------------
# Trend monitoring task (3x per week: Mon, Wed, Fri)
# ---------------------------------------------------------------------------

async def task_trend_monitor() -> None:
    """
    Weekly trend monitor: compare pattern frequencies week-over-week.
    """
    logger.info("=== Trend Monitor Started ===")
    from db import Pattern, get_session
    from sqlalchemy import func, select

    async with get_session() as session:
        result = await session.execute(
            select(Pattern.name, Pattern.frequency, Pattern.week_of)
            .order_by(Pattern.frequency.desc())
            .limit(10)
        )
        rows = result.all()

    lines = ["🔥 *Trend Monitor Report*", ""]
    for name, freq, week in rows:
        lines.append(f"• *{name}* — frequency: {freq}, week: {week}")

    report = "\n".join(lines)
    await _send_notification(report)
    logger.info("=== Trend Monitor Complete ===")


# ---------------------------------------------------------------------------
# Manual research task
# ---------------------------------------------------------------------------

async def task_research_url(url: str, added_by: Optional[int] = None) -> None:
    """Manual one-off research for a single URL."""
    logger.info(f"Manual research for: {url}")
    analysis = await run_pipeline_for_url(url, added_by=added_by)

    if not analysis:
        await _send_notification(f"❌ Failed to analyze: {url}")
        return

    score = float(analysis.final_score) if analysis.final_score else 0
    emoji = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"

    msg = (
        f"{emoji} *Research Complete*\n\n"
        f"Format: {analysis.content_format}\n"
        f"Virality: {analysis.virality_score}/10\n"
        f"Adaptation: {analysis.adaptation_potential}/10\n"
        f"*Final Score: {analysis.final_score}/10*\n\n"
        f"Hook: {analysis.hook_text or 'N/A'}\n"
        f"CTA: {analysis.cta_text or 'N/A'}"
    )
    await _send_notification(msg)


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

async def _send_notification(text: str) -> None:
    """Send notification via Telegram bot or webhook."""
    # Try Telegram bot first
    if config.ROUTER_BOT_TOKEN:
        await _send_telegram(text)
    # Fallback to webhook
    elif config.ALERT_WEBHOOK_URL:
        await _send_webhook(text)
    else:
        logger.info(f"[NOTIFICATION] {text}")


async def _send_telegram(text: str, chat_id: Optional[str] = None) -> None:
    """Send message via Telegram Bot API."""
    if not config.ROUTER_BOT_TOKEN:
        return
    # Default chat ID for admin (should be configured in DB or env)
    chat_id = chat_id or "___ADMIN_CHAT_ID___"
    if chat_id == "___ADMIN_CHAT_ID___":
        logger.warning("No admin chat_id configured; skipping Telegram send")
        return

    url = f"https://api.telegram.org/bot{config.ROUTER_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4096],  # Telegram limit
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(url, json=payload)
    except Exception as exc:
        logger.error(f"Telegram send failed: {exc}")


async def _send_webhook(text: str) -> None:
    """Send to generic webhook."""
    if not config.ALERT_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(
                config.ALERT_WEBHOOK_URL,
                json={"message": text, "source": "content-researcher", "timestamp": datetime.utcnow().isoformat()},
            )
    except Exception as exc:
        logger.error(f"Webhook send failed: {exc}")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="PRODAFLT Content Researcher Tasks")
    parser.add_argument("task", choices=["daily", "trends", "research"], help="Task to run")
    parser.add_argument("--url", help="URL for manual research")
    parser.add_argument("--limit", type=int, default=config.DAILY_LINK_LIMIT, help="Daily link limit")
    parser.add_argument("--user-id", type=int, help="Telegram user ID who submitted")

    args = parser.parse_args()

    if args.task == "daily":
        asyncio.run(task_daily_research(limit=args.limit))
    elif args.task == "trends":
        asyncio.run(task_trend_monitor())
    elif args.task == "research":
        if not args.url:
            print("ERROR: --url required for research task", file=sys.stderr)
            sys.exit(1)
        asyncio.run(task_research_url(args.url, added_by=args.user_id))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
