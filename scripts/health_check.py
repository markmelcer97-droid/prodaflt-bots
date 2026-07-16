"""
PRODAFLT — Health Check Script
==============================
Standalone script to verify all external dependencies are reachable.
Run manually or via CI/CD pipeline before deployment.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any

import asyncpg
import httpx
import redis.asyncio as aioredis

from config.settings import settings


class HealthChecker:
    """Run health checks against all external services."""

    def __init__(self) -> None:
        self.results: dict[str, dict[str, Any]] = {}
        self.overall_status = "healthy"

    # ------------------------------------------------------------------
    # Checkers
    # ------------------------------------------------------------------
    async def check_database(self) -> dict[str, Any]:
        """Check Neon PostgreSQL connectivity."""
        try:
            conn = await asyncpg.connect(settings.database_url_str)
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return {
                "status": "healthy",
                "message": "Connected",
                "version": version.split()[1] if version else "unknown",
            }
        except Exception as e:
            self.overall_status = "unhealthy"
            return {"status": "unhealthy", "message": str(e)}

    async def check_redis(self) -> dict[str, Any]:
        """Check Redis connectivity."""
        try:
            client = aioredis.from_url(settings.redis_url)
            pong = await client.ping()
            info = await client.info("server")
            await client.close()
            return {
                "status": "healthy" if pong else "unhealthy",
                "message": "PONG" if pong else "No response",
                "version": info.get("redis_version", "unknown"),
            }
        except Exception as e:
            self.overall_status = "unhealthy"
            return {"status": "unhealthy", "message": str(e)}

    async def check_kimi_api(self) -> dict[str, Any]:
        """Check Kimi API connectivity."""
        try:
            headers = {
                "Authorization": f"Bearer {settings.kimi_api_key.get_secret_value()}",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.kimi_api_base_url}/models",
                    headers=headers,
                )
                if resp.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "API reachable",
                        "models_available": len(resp.json().get("data", [])),
                    }
                else:
                    self.overall_status = "degraded"
                    return {
                        "status": "degraded",
                        "message": f"HTTP {resp.status_code}",
                    }
        except Exception as e:
            self.overall_status = "degraded"
            return {"status": "degraded", "message": str(e)}

    async def check_telegram_api(self) -> dict[str, Any]:
        """Check Telegram Bot API connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://api.telegram.org/bot/getMe")
                # Will return 401 Unauthorized (expected without token)
                # but proves API is reachable
                if resp.status_code in (401, 404):
                    return {
                        "status": "healthy",
                        "message": "Telegram API reachable",
                    }
                resp.raise_for_status()
                return {"status": "healthy", "message": "API reachable"}
        except Exception as e:
            self.overall_status = "degraded"
            return {"status": "degraded", "message": str(e)}

    # ------------------------------------------------------------------
    # Run all checks
    # ------------------------------------------------------------------
    async def run(self) -> dict[str, Any]:
        """Execute all health checks concurrently."""
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "kimi_api": self.check_kimi_api(),
            "telegram_api": self.check_telegram_api(),
        }

        for name, coro in checks.items():
            self.results[name] = await coro

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": self.overall_status,
            "environment": settings.project_environment.value,
            "version": settings.project_version,
            "checks": self.results,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRODAFLT Health Check")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    checker = HealthChecker()
    report = asyncio.run(checker.run())

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║              PRODAFLT — Health Report                     ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print(f"  Status:     {report['status'].upper()}")
        print(f"  Time:       {report['timestamp']}")
        print(f"  Version:    {report['version']}")
        print("")
        for name, result in report["checks"].items():
            icon = "✅" if result["status"] == "healthy" else "⚠️" if result["status"] == "degraded" else "❌"
            print(f"  {icon} {name:20s} → {result['status']:10s} | {result['message']}")
        print("")

    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
