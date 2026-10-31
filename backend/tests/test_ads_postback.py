"""Monetag: a ymid per show, postback matched by ymid, retries and «click» not counted twice, verify mode + pending."""
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
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    state = {"user": None}
    app = FastAPI()
    app.include_router(ads.create_ads_router(db, lambda: state["user"], lambda: SimpleNamespace(id="a", is_admin=True)))
    return TestClient(app), db, state


def test_ymid_postback_flow():
    c, db, state = _setup()
    uid = str(uuid.uuid4())
    with c:
        orig = c.get("/api/admin/ads").json()
        try:
            c.portal.call(db.users.insert_one, {"id": uid, "username": "adtest"})
            state["user"] = SimpleNamespace(id=uid)
            c.put("/api/admin/ads", json={"enabled": True, "monetag_zone_id": "123", "daily_ads_required": 2,
                                          "min_gap_sec": 0, "verify_postback": True, "require_valued": False})
            sec = c.get("/api/admin/ads").json()["postback_secret"]

            y1 = c.post("/api/ads/daily/start").json()["ymid"]
            assert y1.startswith(uid + ".")
            g = c.post("/api/ads/daily/watched", json={"ymid": y1, "reward_event_type": "valued"}).json()
            assert g["watched"] == 0 and g["pending"] == 1           # verify mode: waits for Monetag

            pb = lambda y, ev: c.get("/api/ads/monetag/postback", params={"ymid": y, "event": ev, "reward": "valued", "secret": sec}).json()
            assert pb(y1, "impression")["counted"] is True
            assert pb(y1, "impression")["counted"] is False         # Monetag retry
            assert pb(y1, "click")["counted"] is False              # same show, not a second view
            g = c.get("/api/ads/daily/gate").json()
            assert g["watched"] == 1 and g["pending"] == 0

            y2 = c.post("/api/ads/daily/start").json()["ymid"]
            c.post("/api/ads/daily/watched", json={"ymid": y2})
            pb(y2, "impression")
            assert c.get("/api/ads/daily/gate").json()["ok"] is True

            assert c.get("/api/ads/monetag/postback", params={"ymid": y2, "event": "impression", "secret": "bad"}).status_code == 403
            assert c.get("/api/ads/monetag/postback", params={"ymid": "", "event": "impression", "secret": sec}).json()["ok"] is False
        finally:
            for col in ("ad_views", "ad_sessions"):
                c.portal.call(getattr(db, col).delete_many, {"user_id": uid})
            c.portal.call(db.ad_postbacks.delete_many, {"ymid": {"$regex": f"^{uid}"}})
            c.portal.call(db.users.delete_one, {"id": uid})
            c.put("/api/admin/ads", json={k: orig.get(k) for k in ("enabled", "monetag_zone_id", "daily_ads_required", "min_gap_sec",
                                                                    "verify_postback", "require_valued")})


def test_adsgram_reward_confirms_the_latest_show():
    """AdsGram: its «Reward URL» (Telegram id) confirms the player's latest open show; AdsGram alone makes ads active."""
    import ads
    assert ads.ads_active({"enabled": True, "daily_ads_required": 1, "adsgram_enabled": True, "adsgram_block_id": "77"})
    assert not ads.ads_active({"enabled": True, "daily_ads_required": 1, "adsgram_enabled": True, "adsgram_block_id": "77",
                               "ads_order": "monetag"})
    c, db, state = _setup()
    uid = str(uuid.uuid4())
    tid = 700000000 + int(uuid.uuid4().int % 1000000)
    with c:
        orig = c.get("/api/admin/ads").json()
        try:
            c.portal.call(db.users.insert_one, {"id": uid, "username": "agtest", "telegram_id": tid})
            state["user"] = SimpleNamespace(id=uid)
            c.put("/api/admin/ads", json={"enabled": True, "monetag_zone_id": "", "adsgram_enabled": True, "adsgram_block_id": "77",
                                          "ads_order": "adsgram", "daily_ads_required": 1, "min_gap_sec": 0, "verify_postback": True})
            cfg = c.get("/api/ads/config").json()
            assert cfg["enabled"] and cfg["adsgram"] == {"enabled": True, "block_id": "77"} and cfg["monetag"] is False
            sec = c.get("/api/admin/ads").json()["postback_secret"]
            assert c.get(f"/api/ads/adsgram/reward?userid={tid}&secret=bad").status_code == 403
            assert c.get(f"/api/ads/adsgram/reward?userid={tid}&secret={sec}").json()["reason"] == "no_open_show"
            y = c.post("/api/ads/daily/start").json()["ymid"]
            c.post("/api/ads/daily/watched", json={"ymid": y, "reward_event_type": "valued"})
            r = c.get(f"/api/ads/adsgram/reward?userid={tid}&secret={sec}").json()
            assert r["counted"] and r["ymid"] == y
            assert c.get(f"/api/ads/adsgram/reward?userid={tid}&secret={sec}").json()["reason"] == "no_open_show"   # once
            assert c.get("/api/ads/daily/gate").json()["ok"] is True
            assert c.get(f"/api/ads/adsgram/reward?userid=1&secret={sec}").json()["reason"] == "unknown_user"
        finally:
            keep = {k: orig.get(k) for k in ("enabled", "monetag_zone_id", "daily_ads_required", "min_gap_sec", "verify_postback",
                                             "require_valued", "adsgram_enabled", "adsgram_block_id", "ads_order") if k in orig}
            keep.setdefault("adsgram_enabled", False); keep.setdefault("adsgram_block_id", ""); keep.setdefault("ads_order", "monetag_first")
            c.put("/api/admin/ads", json=keep)
            for coll in ("users",):
                c.portal.call(db[coll].delete_many, {"id": uid})
            for coll in ("ad_sessions", "ad_views"):
                c.portal.call(db[coll].delete_many, {"user_id": uid})


def test_inactive_adsgram_block_is_skipped_for_players():
    """AdsGram answered «Block … is not active»: for 2 hours players are not sent to AdsGram (Monetag at once,
    no AdsGram error window); only that exact answer pauses it; the admin can switch it back on."""
    c, db, state = _setup()
    with c:
        orig = c.get("/api/admin/ads").json()
        orig_rt = c.portal.call(db.admin_settings.find_one, {"type": "ads_runtime"}, {"_id": 0})
        try:
            state["user"] = SimpleNamespace(id="u-ag")
            c.put("/api/admin/ads", json={"enabled": True, "monetag_zone_id": "123", "daily_ads_required": 1,
                                          "adsgram_enabled": True, "adsgram_block_id": "56550", "ads_order": "adsgram_first"})
            c.post("/api/admin/ads/adsgram-resume")
            assert c.get("/api/ads/config").json()["adsgram"]["enabled"] is True
            assert c.post("/api/ads/adsgram-inactive", json={"description": "user closed"}).json()["ok"] is False
            assert c.get("/api/ads/config").json()["adsgram"]["enabled"] is True
            r = c.post("/api/ads/adsgram-inactive", json={"description": "Block 56550 is not active. Change status…"}).json()
            assert r["ok"] is True
            cfg = c.get("/api/ads/config").json()
            assert cfg["adsgram"]["enabled"] is False and cfg["monetag"] is True
            a = c.get("/api/admin/ads").json()
            assert a["adsgram_paused_until"] and "not active" in a["adsgram_paused_reason"]
            c.post("/api/admin/ads/adsgram-resume")
            assert c.get("/api/ads/config").json()["adsgram"]["enabled"] is True
        finally:
            keys = ("enabled", "monetag_zone_id", "daily_ads_required", "adsgram_enabled", "adsgram_block_id", "ads_order")
            c.put("/api/admin/ads", json={k: orig.get(k) for k in keys if k in orig})
            c.portal.call(db.admin_settings.delete_one, {"type": "ads_runtime"})
            if orig_rt:
                c.portal.call(db.admin_settings.insert_one, {**orig_rt, "type": "ads_runtime"})
