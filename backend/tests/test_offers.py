"""«Рекламные задания»: rewarded views (trust / verify mode, cap, once per ymid) and the AdsGram Task (server Reward URL,
app report, no double reward when both arrive)."""
import os
import sys
import uuid
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def _setup():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    import ads
    import offers
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    state = {"user": None}
    app = FastAPI()
    admin = lambda: SimpleNamespace(id="a", is_admin=True)
    app.include_router(ads.create_ads_router(db, lambda: state["user"], admin))
    app.include_router(offers.create_offers_router(db, lambda: state["user"], admin))
    return TestClient(app), db, state


def _bonus(c, db, uid):
    u = c.portal.call(db.users.find_one, {"id": uid}, {"_id": 0, "bonus_balance": 1})
    return round(float(u.get("bonus_balance") or 0) * 1000, 3)


def _run(fn):
    c, db, state = _setup()
    uid = str(uuid.uuid4())
    tid = str(900000000 + uuid.uuid4().int % 99999999)
    with c:
        ads0 = c.portal.call(db.admin_settings.find_one, {"type": "ads"}, {"_id": 0})
        of0 = c.portal.call(db.admin_settings.find_one, {"type": "offers"}, {"_id": 0})
        try:
            c.portal.call(db.users.insert_one, {"id": uid, "username": "offertest", "telegram_id": tid, "bonus_balance": 0.0})
            state["user"] = SimpleNamespace(id=uid)
            fn(c, db, uid, tid)
        finally:
            for col in ("ad_views", "ad_sessions", "offer_rewards", "transactions"):
                c.portal.call(getattr(db, col).delete_many, {"user_id": uid})
            c.portal.call(db.ad_postbacks.delete_many, {"$or": [{"ymid": {"$regex": f"^{uid}"}}, {"telegram_id": tid}]})
            c.portal.call(db.users.delete_one, {"id": uid})
            for typ, doc in (("ads", ads0), ("offers", of0)):
                c.portal.call(db.admin_settings.delete_one, {"type": typ})
                if doc:
                    c.portal.call(db.admin_settings.insert_one, doc)


def test_ad_offer_trust_mode_cap_and_once():
    def body(c, db, uid, tid):
        c.put("/api/admin/ads", json={"monetag_zone_id": "123", "verify_postback": False, "require_valued": False})
        c.put("/api/admin/offers", json={"ad_offers_enabled": True, "ad_offer_reward": 20, "ad_offer_daily_cap": 2, "ad_offer_gap_sec": 0})
        st = c.get("/api/offers").json()
        assert st["ad"]["enabled"] and st["ad"]["left"] == 2 and st["resets_at"]
        y1 = c.post("/api/offers/ad/start").json()["ymid"]
        r = c.post("/api/offers/ad/watched", json={"ymid": y1}).json()
        assert r["credited"] is True and _bonus(c, db, uid) == 20
        assert c.post("/api/offers/ad/watched", json={"ymid": y1}).json()["credited"] is False   # same show twice
        y2 = c.post("/api/offers/ad/start").json()["ymid"]
        r = c.post("/api/offers/ad/watched", json={"ymid": y2}).json()
        assert r["credited"] is True and r["state"]["ad"]["left"] == 0
        assert c.post("/api/offers/ad/start").status_code == 400                              # daily cap
        assert c.post("/api/offers/ad/watched", json={"ymid": "bogus"}).status_code == 400
        assert _bonus(c, db, uid) == 40
    _run(body)


def test_ad_offer_verify_mode_credits_on_postback():
    def body(c, db, uid, tid):
        c.put("/api/admin/ads", json={"monetag_zone_id": "123", "verify_postback": True, "require_valued": False})
        c.put("/api/admin/offers", json={"ad_offers_enabled": True, "ad_offer_reward": 15, "ad_offer_daily_cap": 3, "ad_offer_gap_sec": 0})
        sec = c.get("/api/admin/ads").json()["postback_secret"]
        y = c.post("/api/offers/ad/start").json()["ymid"]
        r = c.post("/api/offers/ad/watched", json={"ymid": y}).json()
        assert r["credited"] is False and r["pending"] is True and r["state"]["ad"]["pending"] == 1
        assert _bonus(c, db, uid) == 0
        pb = c.get("/api/ads/monetag/postback", params={"ymid": y, "event": "impression", "reward": "valued", "secret": sec}).json()
        assert pb["counted"] is True and pb["purpose"] == "offer"
        assert _bonus(c, db, uid) == 15
        c.get("/api/ads/monetag/postback", params={"ymid": y, "event": "impression", "secret": sec})     # retry
        c.get("/api/ads/monetag/postback", params={"ymid": y, "event": "click", "secret": sec})          # clicks never pay
        assert _bonus(c, db, uid) == 15
        assert c.get("/api/offers").json()["ad"]["pending"] == 0
        # the daily bonus gate does not count offer views
        assert c.portal.call(db.ad_views.count_documents, {"user_id": uid, "purpose": "daily"}) == 0
    _run(body)


def test_adsgram_task_server_and_app_paired():
    def body(c, db, uid, tid):
        c.put("/api/admin/offers", json={"adsgram_task_enabled": True, "adsgram_task_block_id": "123", "adsgram_task_reward": 50,
                                         "adsgram_task_daily_cap": 5, "adsgram_task_trust_client": False})
        sec = c.get("/api/admin/offers").json()["postback_secret"]
        st = c.get("/api/offers").json()["adsgram_task"]
        assert st["enabled"] and st["block_id"] == "task-123"
        # the app reports first → pending, AdsGram's call credits it
        r = c.post("/api/offers/adsgram-task/done").json()
        assert r["pending"] is True and _bonus(c, db, uid) == 0
        assert c.get("/api/offers/adsgram-task/reward", params={"userid": tid, "secret": sec}).json()["credited"] is True
        assert _bonus(c, db, uid) == 50
        # AdsGram first → credited, the app's report that follows is the same task
        c.portal.call(db.offer_rewards.update_many, {"user_id": uid}, {"$set": {"created_at": "2020-01-01T00:00:00+00:00"}})
        assert c.get("/api/offers/adsgram-task/reward", params={"userid": tid, "secret": sec}).json()["credited"] is True
        r = c.post("/api/offers/adsgram-task/done").json()
        assert r.get("already") is True
        assert _bonus(c, db, uid) == 100
        st = c.get("/api/offers").json()["adsgram_task"]
        assert st["done_today"] == 2 and st["left"] == 3 and st["pending"] == 0
        assert c.get("/api/offers/adsgram-task/reward", params={"userid": tid, "secret": "x"}).status_code == 403
        assert c.get("/api/offers/adsgram-task/reward", params={"userid": "1", "secret": sec}).json()["reason"] == "unknown_user"
        assert c.put("/api/admin/offers", json={"adsgram_task_block_id": "abc"}).status_code == 400
    _run(body)


def test_adsgram_task_trust_client_no_double():
    def body(c, db, uid, tid):
        c.put("/api/admin/offers", json={"adsgram_task_enabled": True, "adsgram_task_block_id": "task-7", "adsgram_task_reward": 30,
                                         "adsgram_task_daily_cap": 1, "adsgram_task_trust_client": True})
        sec = c.get("/api/admin/offers").json()["postback_secret"]
        assert c.post("/api/offers/adsgram-task/done").json()["credited"] is True
        assert c.post("/api/offers/adsgram-task/done").status_code == 429                    # a burst of reports
        assert c.get("/api/offers/adsgram-task/reward", params={"userid": tid, "secret": sec}).json()["reason"] == "already_credited_by_app"
        assert _bonus(c, db, uid) == 30
        c.portal.call(db.offer_rewards.update_many, {"user_id": uid}, {"$set": {"created_at": "2020-01-01T00:00:00+00:00"}})
        assert c.post("/api/offers/adsgram-task/done").json()["credited"] is False           # cap 1
        assert _bonus(c, db, uid) == 30
    _run(body)
