"""Market analytics: trade journal, overview (volumes, price change, demand, trends), resource screen, chain."""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from functools import partial
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def test_market_analytics():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    import market_analytics as ma
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    app = FastAPI()
    app.include_router(ma.create_analytics_router(db, lambda: SimpleNamespace(id="u")))
    c = TestClient(app)
    tag = uuid.uuid4().hex[:6]
    b, s = f"mab-{tag}", f"mas-{tag}"
    now = datetime.now(timezone.utc)
    with c:
        try:
            rec = lambda **kw: c.portal.call(partial(ma.record_trade, db, **kw))
            # previous day: 100 luck_chip... use a T3 resource rarely traded in the test DB
            rec(resource="war_protocol", units=2, total_ton=10.0, source="p2p", buyer_id=b, buyer_name="buyerA",
                seller_id=s, seller_name="sellerB", ts=now - timedelta(hours=30))
            rec(resource="war_protocol", units=2, total_ton=12.0, source="p2p", buyer_id=b, buyer_name="buyerA",
                seller_id=s, seller_name="sellerB", ts=now - timedelta(hours=2))
            rec(resource="war_protocol", units=1, total_ton=6.0, source="city_sell", buyer_id=b, buyer_name="buyerA",
                seller_id="CITY_MARKET", ts=now - timedelta(hours=1))
            rec(resource="war_protocol", units=0, total_ton=6.0, source="p2p")            # ignored
            rec(resource="war_protocol_tutorial", units=1, total_ton=6.0, source="p2p")   # ignored
            c.portal.call(partial(ma.record_supply, db, contract_id=f"sc-{tag}", resource="war_protocol", units=0.5,
                                  total_city=3000, buyer_id=b, seller_id=s))
            c.portal.call(partial(ma.record_supply, db, contract_id=f"sc-{tag}", resource="war_protocol", units=0.5,
                                  total_city=3000, buyer_id=b, seller_id=s))
            ma._cache.clear()
            ov = c.get("/api/analytics/overview", params={"period": "24h"}).json()
            wp = next(x for x in ov["resources"] if x["resource"] == "war_protocol")
            assert wp["deals"] >= 3 and wp["units"] >= 4
            # 24h: (12000 + 6000 + 6000) / 4 = 6000 / unit; previous 24h: 5000 → +20 %
            mine = c.portal.call(lambda: db.market_trades.find({"buyer_id": b}).to_list(50))
            assert len(mine) == 4 and sum(1 for m in mine if m["source"] == "supply") == 1
            sup = next(m for m in mine if m["source"] == "supply")
            assert sup["units"] == 1 and sup["total_city"] == 6000
            assert len(ov["resources"]) == 21 and "trends" in ov
            rd = c.get("/api/analytics/resource/war_protocol", params={"period": "7d"}).json()
            assert rd["made_by"] == ["arena"] and rd["tier"] == 3
            assert any(d["buyer_name"] == "buyerA" and d["seller_name"] == "sellerB" for d in rd["deals"])
            assert rd["series"] and rd["summary"]["deals"] >= 4
            assert c.get("/api/analytics/resource/nope").status_code == 404
            ch = c.get("/api/economy/chain").json()
            chips = next(x for x in ch["businesses"] if x["code"] == "chips_factory")
            assert chips["produces"] == "chips" and set(chips["consumes"]) == {"quartz", "repair_kits"}
            assert len(ch["resources"]) == 21
        finally:
            c.portal.call(db.market_trades.delete_many, {"$or": [{"buyer_id": b}, {"seller_id": s}, {"ref": f"sc-{tag}"}]})
            ma._cache.clear()
