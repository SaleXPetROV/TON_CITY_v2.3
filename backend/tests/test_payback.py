"""Окупаемость при идеальных условиях: a day = output × price × (1 − tax) − raw materials − repair; days = cost / day."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import payback as pb  # noqa: E402
from business_config import get_production, get_consumption_breakdown, RESOURCE_TYPES  # noqa: E402


def test_a_day_and_the_payback_add_up():
    async def go():
        db = AsyncMongoMockClient()["t"]
        await db.market_prices.insert_one({"type": "current", "prices": {"quartz": 4.0, "scrap": 3.0}})
        r = await pb.for_type(db, "quartz_mine", 2, 10.0)                       # bought for 10 TON = 10 000 $CITY
        d = r["day"]
        q = get_production("quartz_mine", 2)
        assert d["qty"] == q and abs(d["gross_city"] - q * 4.0) < 0.01 and d["tax_rate"] == 0.15
        raw = sum(v * (3.0 if k == "scrap" else RESOURCE_TYPES[k]["base_price"]) for k, v in get_consumption_breakdown("quartz_mine", 2).items())
        assert abs(d["inputs_city"] - raw) < 0.01
        assert abs(d["profit_city"] - (q * 4.0 * 0.85 - raw - d["repair_city"])) < 0.02
        assert abs(r["days"] - 10000 / d["profit_city"]) < 0.1
        nx = r["next"]
        assert nx["level"] == 3 and nx["cost_city"] > 0 and abs(nx["extra_city"] - (nx["profit_city"] - d["profit_city"])) < 0.02
    asyncio.run(go())


def test_never_pays_back_when_the_day_loses_money():
    async def go():
        db = AsyncMongoMockClient()["t"]
        await db.market_prices.insert_one({"type": "current", "prices": {"quartz": 0.01}})
        r = await pb.for_type(db, "quartz_mine", 1, 5.0)
        assert r["day"]["profit_city"] < 0 and r["days"] is None
    asyncio.run(go())


def test_a_free_level0_business_shows_the_buyout():
    async def go():
        db = AsyncMongoMockClient()["t"]
        r = await pb.for_business(db, {"id": "z", "business_type": "bio_farm", "level": 0, "is_zero_business": True})
        assert r["buyout"] and r["level"] == 1 and r["invest_city"] > 0 and r["days"] and r["days"] > 0
        nx = r["next"]                                          # its next step is the buyout 0 → 1, not 1 → 2
        assert nx["level"] == 1 and nx["mode"] == "buyout" and nx["cost_city"] == r["invest_city"] and nx["days"] == r["days"]
    asyncio.run(go())


def test_an_upgrade_always_has_a_payback():
    """A level that adds no profit by itself (casino 1 → 2) pays back as the whole business on that level."""
    async def go():
        db = AsyncMongoMockClient()["t"]
        from business_config import BUSINESSES
        for t in BUSINESSES:
            for lvl in range(1, 10):
                r = await pb.for_type(db, t, lvl, 50.0)
                nx = r.get("next")
                if nx and r["day"]["profit_city"] > 0:
                    assert nx["days"] is not None and nx["days"] > 0, (t, lvl, nx)
        r = await pb.for_type(db, "casino", 1, 50.0)
        if r["next"]["extra_city"] <= 0:
            assert r["next"]["mode"] == "full"
    asyncio.run(go())
