"""Guide: a newcomer goes the «claim a free business» way (steps 10–12) only while the City's presale has a free
level-0 lot he can take; otherwise the «returning» way, like a player who already has a business."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import presale_gate as pg  # noqa: E402
from core.ttl_cache import invalidate  # noqa: E402

CELLS = [{"x": 1, "y": 1, "district": 1, "zone": "a", "pre_business": "farm"},
         {"x": 2, "y": 1, "district": 1, "zone": "a", "pre_business": "farm"},
         {"x": 3, "y": 1, "district": 2, "zone": "a", "pre_business": "farm"}]


async def _db(**presale):
    invalidate("")
    db = AsyncMongoMockClient()["t"]
    await db.islands.insert_one({"id": "ton_island", "cells": CELLS})
    doc = {"type": "presale", "active": True, "map_id": "ton_island",
           "selected_plots": [{"x": c["x"], "y": c["y"], "business_type": "farm"} for c in CELLS]}
    doc.update(presale)
    await db.admin_settings.insert_one(doc)
    return db


def test_free_lots_follow_the_buy_rules():
    async def go():
        db = await _db()
        assert await pg._count_free_plots(db) == 3
        await db.plots.insert_one({"island_id": "ton_island", "x": 1, "y": 1, "owner": "u1"})          # taken
        await db.admin_settings.insert_one({"type": "city_districts", "unlocked": {"2": False}})       # closed district
        invalidate("")
        assert await pg._count_free_plots(db) == 1
    asyncio.run(go())


def test_no_free_lots_without_an_open_presale():
    async def go():
        assert await pg._count_free_plots(await _db(active=False)) == 0
        later = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        assert await pg._count_free_plots(await _db(opens_at=later)) == 0                            # countdown running
        assert await pg._count_free_plots(await _db(selected_plots=[])) == 0
        stale = [{"x": 1, "y": 1, "business_type": "quartz_mine"}]                                    # an older layout
        assert await pg._count_free_plots(await _db(selected_plots=stale)) == 0
    asyncio.run(go())
