"""Seized-for-inactivity businesses are listed at a fair price: the island cell's map price, never below the
base build cost — not the old 1 TON fallback; listings already put up too cheap are repriced."""
import asyncio
import os
import sys
import uuid

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

import inactivity  # noqa: E402


def _db():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_window_is_10_days():
    assert inactivity.WINDOW_DAYS == 10


def test_fair_price_by_level_and_reprice():
    async def run():
        from core.seizure import seizure_price_breakdown, _resource_price_ton
        from business_config import UPGRADE_COSTS_TABLE
        db = _db()
        isl = await db.islands.find_one({"id": "ton_island"}, {"_id": 0, "cells": 1})
        cell = max(isl["cells"], key=lambda c: float(c.get("price_ton") or 0))
        cell_ton = float(cell["price_ton"])
        tag = f"inact-price-{uuid.uuid4().hex[:8]}"
        biz = {"id": tag, "business_type": "helios", "level": 4, "x": cell["x"], "y": cell["y"],
               "island_id": "ton_island", "plot_id": f"{tag}-plot", "is_seized": True}
        unit = await _resource_price_ton(db, "neuro_core")
        steps = [UPGRADE_COSTS_TABLE["helios"][lvl] for lvl in (2, 3, 4)]
        expect4 = cell_ton + sum(s["city"] for s in steps) / 1000 + sum(s["qty"] for s in steps) * unit
        try:
            # plots keep price_ton (no "price" field) — that was the 1 TON bug
            await db.plots.insert_one({"id": f"{tag}-plot", "x": cell["x"], "y": cell["y"], "price_ton": 5.0})
            # level 1 = map price of the cell; level 4 = + upgrades ($CITY + neuro_core at the market price)
            assert abs(await inactivity._map_price_for_business(db, biz, 1) - cell_ton) < 1e-6
            bd = await seizure_price_breakdown(db, biz)
            assert bd["level"] == 4 and abs(bd["total"] - expect4) < 1e-4
            assert bd["resources"]["neuro_core"]["qty"] == sum(s["qty"] for s in steps)
            assert bd["total"] > await inactivity._map_price_for_business(db, {**biz, "level": 3})
            # no cell, no plot → base build cost, not 1 TON
            p2 = await inactivity._map_price_for_business(db, {"business_type": "helios", "x": 99999, "y": 99999})
            assert p2 == inactivity._base_cost_ton({"business_type": "helios"}) and p2 > 1.0
            # an old listing (business reset to level 1, 1 TON) gets its level back and the price for it;
            # a sold one and one priced by the admin by hand are not touched
            await db.businesses.insert_one({**biz, "level": 1})
            common = {"business_id": tag, "x": cell["x"], "y": cell["y"], "price": 1.0, "seller_receives": 1.0,
                      "tax_amount": 0.0, "seller_id": "SYSTEM_GRAM_CITY", "seizure_reason": "inactivity",
                      "former_level": 4, "business": {"type": "helios", "level": 1}}
            await db.land_listings.insert_many([
                {**common, "id": f"{tag}-l1", "status": "active"},
                {**common, "id": f"{tag}-l2", "status": "sold"},
                {**common, "id": f"{tag}-l3", "status": "active", "price_manual": True}])
            assert await inactivity.reprice_underpriced_listings(db) >= 1
            l1 = await db.land_listings.find_one({"id": f"{tag}-l1"}, {"_id": 0})
            assert abs(l1["price"] - expect4) < 1e-4 and l1["seller_receives"] == l1["price"]
            assert l1["business"]["level"] == 4 and l1["price_breakdown"]["level"] == 4
            assert (await db.businesses.find_one({"id": tag}, {"_id": 0}))["level"] == 4
            for lid in ("l2", "l3"):
                assert (await db.land_listings.find_one({"id": f"{tag}-{lid}"}, {"_id": 0}))["price"] == 1.0
            # frozen: a second pass changes nothing
            await db.land_listings.delete_many({"id": {"$in": [f"{tag}-l2", f"{tag}-l3"]}})
            assert await inactivity.reprice_underpriced_listings(db) == 0
        finally:
            await db.plots.delete_many({"id": f"{tag}-plot"})
            await db.businesses.delete_many({"id": tag})
            await db.land_listings.delete_many({"id": {"$regex": f"^{tag}"}})
    asyncio.run(run())


def test_seizure_keeps_level_and_prices_it():
    """The whole inactivity seizure on a scratch database: the business keeps its level, the listing costs the fair
    price for that level; a durability seizure is priced the same way."""
    async def run():
        from core.seizure import seize_business, seizure_price_breakdown
        main = _db()
        scratch = main.client[f"gc_scratch_{uuid.uuid4().hex[:8]}"]
        try:
            isl = await main.islands.find_one({"id": "ton_island"}, {"_id": 0})
            await scratch.islands.insert_one(isl)
            cell = isl["cells"][0]
            await scratch.users.insert_one({"id": "u1", "username": "idle"})
            await scratch.businesses.insert_many([
                {"id": "b1", "owner": "u1", "business_type": "helios", "level": 5, "x": cell["x"], "y": cell["y"],
                 "island_id": "ton_island", "status": "active", "is_active": True},
                {"id": "b2", "owner": "u1", "business_type": "helios", "level": 3, "x": cell["x"] + 100,
                 "y": cell["y"], "island_id": "ton_island", "status": "active", "is_active": True}])
            res = await inactivity.seize_inactive_businesses(scratch)
            assert res["seized_regular"] == 2
            b1 = await scratch.businesses.find_one({"id": "b1"}, {"_id": 0})
            lst = await scratch.land_listings.find_one({"business_id": "b1"}, {"_id": 0})
            assert b1["level"] == 5 and lst["business"]["level"] == 5 and lst["former_level"] == 5
            fair = (await seizure_price_breakdown(scratch, {**b1, "is_seized": False}, 5))["total"]
            assert abs(lst["price"] - fair) < 1e-6 and lst["seller_receives"] == lst["price"]
            assert lst["price"] > float(cell["price_ton"])
            # durability / credit seizure: same formula
            await scratch.businesses.insert_one({"id": "b3", "owner": "u1", "business_type": "helios", "level": 4,
                                                 "x": cell["x"], "y": cell["y"], "island_id": "ton_island"})
            l3 = await seize_business(scratch, await scratch.businesses.find_one({"id": "b3"}, {"_id": 0}),
                                      "durability_zero")
            assert l3["price_breakdown"]["level"] == 4 and l3["price"] == l3["price_breakdown"]["total"]
            assert l3["price_breakdown"]["level1_ton"] == float(cell["price_ton"]) or \
                l3["price_breakdown"]["level1_ton"] == l3["price_breakdown"]["base_cost_ton"]
        finally:
            await main.client.drop_database(scratch.name)
    asyncio.run(run())
