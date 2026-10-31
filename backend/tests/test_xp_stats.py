"""Admin «XP игроков»: totals / averages / the most per day, week and month, all XP or the games' only."""
import asyncio
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
mongomock_motor = pytest.importorskip("mongomock_motor")
import xp_stats  # noqa: E402


def test_xp_stats_periods():
    db = mongomock_motor.AsyncMongoMockClient()["xps"]
    today = date(2026, 10, 30)

    async def run():
        await db.users.insert_many([{"id": "a", "username": "alice"}, {"id": "b", "username": "bob"}])
        await db.city_pass_progress.insert_many([
            {"user_id": "a", "season_id": "s1", "daily": {"2026-10-30": {"xp": 100, "arcade": 40},
                                                         "2026-10-29": {"xp": 50, "arcade": 0},
                                                         "2026-10-10": {"xp": 999}}},
            {"user_id": "b", "season_id": "s1", "daily": {"2026-10-30": {"xp": 30, "arcade": 30}}},
            {"user_id": "a", "season_id": "s0", "daily": {"2026-10-25": {"xp": 20, "arcade": 20}}},   # older season
        ])
        d = await xp_stats.xp_stats(db, "day", today=today)
        assert d["players"] == 2 and d["total"] == 130 and d["max"]["username"] == "alice" and d["max"]["xp"] == 100
        assert d["avg"] == 65
        y = await xp_stats.xp_stats(db, "yesterday", today=today)
        assert y["total"] == 50 and y["players"] == 1
        w = await xp_stats.xp_stats(db, "week", today=today)
        assert w["total"] == 200 and w["max"]["xp"] == 170 and len(w["series"]) == 7
        assert w["per_player_day"]["max"] == 100
        m = await xp_stats.xp_stats(db, "month", today=today)
        assert m["total"] == 1199
        g = await xp_stats.xp_stats(db, "week", "games", today=today)
        assert g["total"] == 90 and g["max"]["xp"] == 60
    asyncio.run(run())
