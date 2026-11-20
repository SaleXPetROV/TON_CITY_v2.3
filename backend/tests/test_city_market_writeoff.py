"""The admin reduces the City Market's stock bought from players: the stock and the city's lot shrink together,
the cost leaves proportionally, nothing can be added, the write-off is journaled."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
mongomock_motor = pytest.importorskip("mongomock_motor")
import market_maker as mm  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def test_writeoff_reduces_stock_and_lot():
    db = mongomock_motor.AsyncMongoMockClient()["mmwo"]

    async def run():
        await db.mm_inventory.insert_one({"resource": "energy", "amount": 300, "cost_ton": 0.6})
        await mm.run_sell_side(db)
        lot = await db.market_listings.find_one({"seller_id": mm.CITY_MARKET_ID, "status": "active"})
        assert lot["amount"] == 300
        r = await mm.stock_writeoff(db, "energy", 100, "admin")
        assert r == {"ok": True, "resource": "energy", "removed": 100, "left": 200}
        inv = await db.mm_inventory.find_one({"resource": "energy"})
        assert inv["amount"] == 200 and abs(inv["cost_ton"] - 0.4) < 1e-9
        lot = await db.market_listings.find_one({"seller_id": mm.CITY_MARKET_ID, "status": "active"})
        assert lot["amount"] == 200
        wo = await db.mm_writeoffs.find_one({})
        assert wo["units"] == 100 and wo["admin"] == "admin"
        # more than there is → everything left; the lot goes away
        r = await mm.stock_writeoff(db, "energy", 999, "admin")
        assert r["removed"] == 200 and r["left"] == 0
        assert await db.market_listings.count_documents({"seller_id": mm.CITY_MARKET_ID, "status": "active"}) == 0
        for bad in (("energy", 5), ("nope", 5), ("energy", 0), ("energy", -3)):
            with pytest.raises(HTTPException):
                await mm.stock_writeoff(db, *bad)
        # the analytics do not count a write-off as a sale
        a = await mm.analytics(db, 7)
        row = next((x for x in a["resources"] if x["resource"] == "energy"), None)
        assert row is None or row["sold_units"] == 0
    asyncio.run(run())
