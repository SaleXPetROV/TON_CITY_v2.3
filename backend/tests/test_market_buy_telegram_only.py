"""A Telegram-only player (no wallet, no email) can buy on the resource market. Before: every buy answered
404 «Buyer not found» (the app showed «lot sold out») because the buyer was looked up only for wallet / email users."""
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def test_telegram_only_player_buys():
    import httpx
    import jwt
    try:
        httpx.get("http://127.0.0.1:8001/api/health", timeout=3)
    except Exception:
        pytest.skip("server not running")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from pymongo import MongoClient
    from security_middleware import get_or_generate_jwt_secret
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    k = uuid.uuid4().hex[:8]
    uid, uname, sid, lid, bid = f"tgo-{k}", f"tgonly_{k}", f"tgo-seller-{k}", f"tgo-lot-{k}", f"tgo-biz-{k}"
    try:
        db.users.insert_one({"id": uid, "username": uname, "telegram_id": f"9{k[:6]}", "balance_ton": 0.0, "bonus_balance": 0.38,
                             "resources": {}, "created_at": datetime.now(timezone.utc).isoformat()})
        db.users.insert_one({"id": sid, "username": f"seller_{k}", "email": f"s{k}@x.io", "resources": {}})
        db.businesses.insert_one({"id": bid, "owner": uid, "business_type": "helios", "level": 0, "tier": 1,
                                  "storage": {"capacity": 500, "items": {}}, "is_active": True})
        db.market_listings.insert_one({"id": lid, "seller_id": sid, "resource_type": "cooling", "amount": 70, "price_per_unit": 0.003,
                                       "status": "active", "created_at": datetime.now(timezone.utc).isoformat()})
        tok = jwt.encode({"sub": uname, "exp": 9999999999}, get_or_generate_jwt_secret(), algorithm="HS256")
        r = httpx.post("http://127.0.0.1:8001/api/market/buy", json={"listing_id": lid, "amount": 10},
                       headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code != 404 or "Buyer" not in r.text, r.text
        assert r.status_code == 200, r.text
        assert db.market_listings.find_one({"id": lid})["amount"] == 60
        # a City Market lot (no seller email at all) — the empty email must not count as «your own listing»
        db.market_listings.insert_one({"id": lid + "c", "seller_id": "CITY_MARKET", "resource_type": "energy", "amount": 50,
                                       "price_per_unit": 0.004, "status": "active", "is_city_market": True,
                                       "created_at": datetime.now(timezone.utc).isoformat()})
        r = httpx.post("http://127.0.0.1:8001/api/market/buy", json={"listing_id": lid + "c", "amount": 10},
                       headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 200, r.text
    finally:
        db.users.delete_many({"id": {"$in": [uid, sid]}})
        db.businesses.delete_many({"id": bid})
        db.market_listings.delete_many({"id": {"$in": [lid, lid + "c"]}})
        for c in ("transactions", "notifications", "mm_trades"):
            db[c].delete_many({"$or": [{"user_id": {"$in": [uid, sid]}}, {"buyer_id": uid}, {"seller_id": sid}]})
