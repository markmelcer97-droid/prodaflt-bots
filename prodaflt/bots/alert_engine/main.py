"""
PRODAFLT Alert Engine — Main Entry Point
=========================================
CLI + scheduled loop for evaluating campaign metrics and firing alerts.

Usage:
    python main.py run-once       # Single evaluation pass
    python main.py daemon         # Continuous loop (every N seconds)
    python main.py test-alert     # Send a test Telegram alert

Environment:
    Copy .env.example → .env and fill in your credentials.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from decimal import Decimal
from typing import List

from config import get_settings
from database import (
    get_db,
    fetch_active_campaigns,
    insert_alert_log,
    check_recent_alert_exists,
    AlertsLogORM,
)
from engine import evaluate_all
from models import CampaignMetrics, AlertDecision, AlertFlag
from notifier import TelegramNotifier

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)


# ---------------------------------------------------------------------------
# Evaluation pipeline
# ---------------------------------------------------------------------------

async def run_evaluation(notifier: TelegramNotifier, dedup_minutes: int = 30) -> List[AlertDecision]:
    """
    Fetch active campaigns, evaluate thresholds, log alerts, send Telegram.

    Args:
        notifier: TelegramNotifier instance.
        dedup_minutes: Skip if identical alert was fired within this window.

    Returns:
        List of AlertDecisions that resulted in alerts.
    """
    logger = logging.getLogger("alert_engine")
    fired: List[AlertDecision] = []

    with get_db() as session:
        rows = fetch_active_campaigns(session)
        if not rows:
            logger.info("No active campaigns to evaluate.")
            return fired

        campaigns = [CampaignMetrics.model_validate(r) for r in rows]
        logger.info("Evaluating %d active campaigns", len(campaigns))

        decisions = evaluate_all(campaigns)
        logger.info("%d campaigns triggered alerts", len(decisions))

        for d in decisions:
            # Deduplication: skip if same flag was already fired recently
            if check_recent_alert_exists(session, d.campaign_id, d.flag.value, dedup_minutes):
                logger.info(
                    "Deduplicated alert for campaign %s (%s) — already fired within %dm",
                    d.creative_code, d.flag.value, dedup_minutes,
                )
                continue

            # Persist to alerts_log
            for alert_type in d.alert_types:
                log_orm = AlertsLogORM(
                    campaign_id=d.campaign_id,
                    alert_type=alert_type.value,
                    flag=d.flag.value,
                    triggered_metrics=d.triggered_metrics,
                    confidence=d.confidence,
                    decision=d.decision,
                    reason=d.reason,
                )
                insert_alert_log(session, log_orm)

            # Send Telegram
            msg_id = await notifier.send_alert(d)
            if msg_id:
                # Update sent_at + sent_to on the latest log row
                # (In production you might link msg_id directly; keeping it simple here.)
                pass

            fired.append(d)

    return fired


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

async def daemon_loop(notifier: TelegramNotifier, interval: int) -> None:
    """Run evaluation every `interval` seconds forever."""
    logger = logging.getLogger("alert_engine")
    logger.info("Starting alert engine daemon (interval=%ds)", interval)

    while True:
        try:
            fired = await run_evaluation(notifier)
            if fired:
                logger.info("Daemon cycle complete — %d alerts fired", len(fired))
            else:
                logger.info("Daemon cycle complete — no alerts")
        except Exception:
            logger.exception("Daemon cycle failed")

        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Test alert
# ---------------------------------------------------------------------------

async def send_test_alert(notifier: TelegramNotifier) -> None:
    """Send a fake RED alert to verify Telegram connectivity."""
    test = AlertDecision(
        campaign_id=0,
        creative_code="TEST-ALERT-001",
        flag=AlertFlag.RED,
        alert_types=[],
        confidence=Decimal("95"),
        decision="KILL — CPI $5.30 ≥ $5.00",
        reason="This is a test alert from PRODAFLT Alert Engine. If you see this, Telegram is configured correctly.",
        triggered_metrics={"cpi": "5.30", "spend": "120.00", "clicks": "45"},
    )
    msg_id = await notifier.send_alert(test)
    if msg_id:
        print(f"✅ Test alert delivered (msg_id={msg_id})")
    else:
        print("❌ Test alert failed — check TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID in .env")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="PRODAFLT Alert Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run-once", help="Evaluate campaigns once and exit")
    sub.add_parser("daemon", help="Run continuous evaluation loop")
    sub.add_parser("test-alert", help="Send a test Telegram alert")

    args = parser.parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    notifier = TelegramNotifier()

    if args.command == "run-once":
        fired = asyncio.run(run_evaluation(notifier))
        print(f"Fired {len(fired)} alert(s)")
        for d in fired:
            print(f"  • {d.flag.value:5} | {d.creative_code} | {d.decision}")
        return 0

    if args.command == "daemon":
        try:
            asyncio.run(daemon_loop(notifier, settings.alert_engine_interval_seconds))
        except KeyboardInterrupt:
            print("\n👋 Daemon stopped by user.")
        return 0

    if args.command == "test-alert":
        asyncio.run(send_test_alert(notifier))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
