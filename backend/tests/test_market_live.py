"""Live market (market_live.py): the diff, and a real push over the personal socket after a lot changes."""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

import market_live  # noqa: E402


def test_diff():
    d = market_live.diff({"a": 10, "b": 5, "c": 1}, {"a": 10, "b": 3, "d": 7})
    assert d == {"removed": ["c"], "added": ["d"], "updated": [{"id": "b", "amount": 3}]}


def test_push_over_socket():
    import httpx
    try:
        httpx.get("http://127.0.0.1:8001/api/health", timeout=3)
        import websockets
    except Exception:
        pytest.skip("server not running")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    lid = "ml-test-" + uuid.uuid4().hex[:8]

    async def go():
        async with websockets.connect(f"ws://127.0.0.1:8001/api/ws/ml-test-{uuid.uuid4().hex[:6]}") as ws:
            await asyncio.sleep(market_live.TICK * 2 + 0.5)            # the watcher takes its baseline
            db.market_listings.insert_one({"id": lid, "seller_id": "ml-seller", "resource_type": "energy", "amount": 40,
                                           "price_per_unit": 0.003, "status": "active",
                                           "created_at": datetime.now(timezone.utc).isoformat()})
            got = await _wait(ws, lambda m: any(x.get("id") == lid for x in m.get("added") or []))
            assert got["added"][0]["amount"] == 40
            db.market_listings.update_one({"id": lid}, {"$set": {"amount": 10}})
            await _wait(ws, lambda m: {"id": lid, "amount": 10} in (m.get("updated") or []))
            db.market_listings.update_one({"id": lid}, {"$set": {"status": "sold", "amount": 0}})
            await _wait(ws, lambda m: lid in (m.get("removed") or []))

    async def _wait(ws, pred, timeout=8):
        end = asyncio.get_event_loop().time() + timeout
        while True:
            left = end - asyncio.get_event_loop().time()
            assert left > 0, "no market_update push"
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=left))
            if m.get("type") == "market_update" and pred(m):
                return m
    try:
        asyncio.run(go())
    finally:
        db.market_listings.delete_many({"id": lid})
