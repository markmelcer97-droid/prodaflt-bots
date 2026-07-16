"""
PRODAFLT — Database Seeder
==========================
Populate the database with initial reference data for development.
Safe to run multiple times (uses ON CONFLICT DO NOTHING).

Usage:
    python scripts/seed_database.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import insert, select

from config.database import AsyncSessionLocal, Base, init_db
from config.logging_config import get_logger

logger = get_logger("prodaFLT.seed")


# ------------------------------------------------------------------
# Seed Data
# ------------------------------------------------------------------
PATTERNS = [
    {
        "name": "Newsjacking Hook",
        "description": "Uses breaking news or trending topics as the opening hook to capture attention.",
        "examples": [
            {"title": "Breaking: This trick just went viral...", "platform": "TikTok"},
            {"title": "Everyone's talking about this new method", "platform": "Instagram"},
        ],
        "frequency": 45,
        "metrics": {"avg_ctr": 3.2, "avg_cpi": 4.1},
    },
    {
        "name": "Social Proof Carousel",
        "description": "Showcases real user testimonials, winnings, or success stories in a swipeable format.",
        "examples": [
            {"title": "3 people who changed their lives this week", "platform": "Instagram"},
            {"title": "Real results from real players", "platform": "Facebook"},
        ],
        "frequency": 32,
        "metrics": {"avg_ctr": 2.8, "avg_cpi": 3.9},
    },
    {
        "name": "FOMO Countdown",
        "description": "Creates urgency with limited-time offers, countdown timers, or scarcity messaging.",
        "examples": [
            {"title": "Only 24 hours left to claim your bonus", "platform": "YouTube"},
            {"title": "Hurry! Spots filling fast", "platform": "TikTok"},
        ],
        "frequency": 28,
        "metrics": {"avg_ctr": 4.1, "avg_cpi": 5.2},
    },
    {
        "name": "UGC Testimonial",
        "description": "Authentic user-generated content showing genuine reactions and experiences.",
        "examples": [
            {"title": "I couldn't believe this actually worked", "platform": "TikTok"},
            {"title": "My honest review after 30 days", "platform": "YouTube"},
        ],
        "frequency": 38,
        "metrics": {"avg_ctr": 3.5, "avg_cpi": 4.3},
    },
    {
        "name": "Problem-Solution Flip",
        "description": "Presents a relatable pain point then flips to the solution (the product/offer).",
        "examples": [
            {"title": "Tired of losing? Try this instead", "platform": "Facebook"},
            {"title": "The mistake 90% of beginners make", "platform": "YouTube"},
        ],
        "frequency": 22,
        "metrics": {"avg_ctr": 2.9, "avg_cpi": 3.7},
    },
]

USERS = [
    {"telegram_id": 1001, "username": "durovscales", "first_name": "Daniil", "role": "admin", "team_role": "TeamLead"},
    {"telegram_id": 1002, "username": "chernov_1", "first_name": "Alex", "role": "user", "team_role": "Bayer"},
    {"telegram_id": 1003, "username": "only1showbizschool", "first_name": "Maria", "role": "user", "team_role": "Design"},
]


# ------------------------------------------------------------------
# Seeding Logic
# ------------------------------------------------------------------
async def seed_patterns(session) -> int:
    """Insert pattern reference data."""
    from models.patterns import Pattern

    count = 0
    for data in PATTERNS:
        exists = await session.execute(
            select(Pattern).where(Pattern.name == data["name"])
        )
        if not exists.scalar_one_or_none():
            pattern = Pattern(**data)
            session.add(pattern)
            count += 1

    await session.commit()
    logger.info(f"Seeded {count} patterns")
    return count


async def seed_users(session) -> int:
    """Insert default users."""
    from models.users import User

    count = 0
    for data in USERS:
        exists = await session.execute(
            select(User).where(User.username == data["username"])
        )
        if not exists.scalar_one_or_none():
            user = User(**data)
            session.add(user)
            count += 1

    await session.commit()
    logger.info(f"Seeded {count} users")
    return count


async def main() -> None:
    """Run all seeders."""
    logger.info("Starting database seeding...")

    # Ensure tables exist (dev only!)
    await init_db()

    async with AsyncSessionLocal() as session:
        patterns_count = await seed_patterns(session)
        users_count = await seed_users(session)

    total = patterns_count + users_count
    logger.info(f"Seeding complete. Total records inserted: {total}")


if __name__ == "__main__":
    asyncio.run(main())
