"""1×2 businesses: tuning per view (1×2 / 2×1) and orientation per place of the map (slot_views)."""
import os
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def _client():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    import city_sprites
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    app = FastAPI()
    app.include_router(city_sprites.create_city_sprites_router(db, lambda: {"id": "admin"}))
    return TestClient(app)


def _slot(t, w, h):
    import json
    lay = json.load(open(os.path.join(_BACKEND_DIR, "data", "city_layout_v1.json")))
    return next(s for s in lay["slots"] if s["business_type"] == t and s["w"] == w and s["h"] == h)


def test_slot_view_and_alt_tuning():
    c = _client()
    with c:
        s = _slot("cyber_cafe", 2, 1)
        sid = s["slot_id"]
        r = c.put("/api/admin/city-sprites/slot-view", json={"slot_id": sid, "view": "main", "mirror": True})
        assert r.status_code == 200 and r.json()["slot_views"][str(sid)] == {"view": "main", "mirror": True}
        pub = c.get("/api/city-sprites/tuning").json()
        assert pub["slot_views"][str(sid)]["mirror"] is True
        # «auto» without mirror = the default → the place setting is removed
        r = c.put("/api/admin/city-sprites/slot-view", json={"slot_id": sid, "view": "auto", "mirror": False})
        assert str(sid) not in r.json()["slot_views"]
        # only the three 1×2 businesses can be turned
        helios = _slot("helios", 1, 1)["slot_id"]
        assert c.put("/api/admin/city-sprites/slot-view", json={"slot_id": helios, "view": "main"}).status_code == 400
        assert c.put("/api/admin/city-sprites/slot-view", json={"slot_id": 999999, "view": "main"}).status_code == 404
        # the 2×1 view keeps its own tuning, the main one is untouched
        before = (c.get("/api/city-sprites/tuning").json()["tuning"].get("vr_club") or {}).get("2")
        r = c.put("/api/admin/city-sprites/tuning", json={"type": "vr_club", "stage": "2", "view": "alt", "scale": 1.2, "dx": 0.1})
        d = r.json()
        assert d["tuning_alt"]["vr_club"]["2"]["scale"] == 1.2
        assert (d["tuning"].get("vr_club") or {}).get("2") == before
        assert c.put("/api/admin/city-sprites/tuning", json={"type": "helios", "stage": "1", "view": "alt"}).status_code == 400
        r = c.delete("/api/admin/city-sprites/tuning/vr_club/2", params={"view": "alt"})
        assert "2" not in (r.json()["tuning_alt"].get("vr_club") or {})
