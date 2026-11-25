"""The 3-day plan on the «Задания» page (routes/guide.py /plan): the goals, the timer, the reward only in time."""
from datetime import datetime, timedelta, timezone

import pytest
mongomock_motor = pytest.importorskip("mongomock_motor")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.dependencies import get_current_user  # noqa: E402
from core.models import User  # noqa: E402
from routes.guide import create_guide_router  # noqa: E402


def _client(db):
    app = FastAPI()
    app.include_router(create_guide_router(db))
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="u1@x.io", username="u1")
    return TestClient(app)


def _iso(dt):
    return dt.isoformat()


def _world(started_ago_h=1, level=1, repaired=True, sold=True):
    import asyncio
    db = mongomock_motor.AsyncMongoMockClient()["plan"]
    now = datetime.now(timezone.utc)

    async def go():
        await db.users.insert_one({"id": "u1", "email": "u1@x.io", "username": "u1", "resources": {},
                                   "plan3": {"started_at": _iso(now - timedelta(hours=started_ago_h))}})
        await db.businesses.insert_one({"id": "b1", "owner": "u1", "business_type": "quartz_mine", "level": level,
                                        "shift_started_at": _iso(now - timedelta(hours=2))})
        if repaired:
            await db.transactions.insert_one({"tx_type": "repair", "user_id": "u1"})
        if sold:
            await db.market_listings.insert_one({"id": "l1", "seller_id": "u1", "status": "sold"})
    asyncio.run(go())
    return db


def test_plan_counts_the_goals_and_gives_the_reward_in_time():
    db = _world()
    c = _client(db)
    p = c.get("/api/guide/plan").json()
    assert p["show"] and p["all_done"] and p["can_claim"] and p["done"] == 5
    r = c.post("/api/guide/plan/claim", json={"choice": "gold_bill"}).json()
    assert r["ok"] and not r["already"]
    assert c.get("/api/guide/plan").json() == {"show": False, "claimed": True}


def test_plan_not_done_cannot_be_claimed_and_hides_after_3_days():
    db = _world(level=0, repaired=False)
    c = _client(db)
    p = c.get("/api/guide/plan").json()
    assert p["show"] and not p["all_done"] and p["done"] == 3
    assert c.post("/api/guide/plan/claim", json={"choice": "gold_bill"}).status_code == 400
    db2 = _world(started_ago_h=80)                                   # everything done — but after the 3 days
    c2 = _client(db2)
    p2 = c2.get("/api/guide/plan").json()
    assert p2["show"] is False and p2["can_claim"] is False
    assert c2.post("/api/guide/plan/claim", json={"choice": "gold_bill"}).status_code == 400


def test_intro_and_page_hints_are_remembered_and_restart_resets_them():
    db = _world()
    c = _client(db)
    assert c.get("/api/guide").json()["state"]["intro_seen"] is False
    c.post("/api/guide/intro-seen")
    c.post("/api/guide/tour-seen", json={"key": "/trading"})
    st = c.get("/api/guide").json()["state"]
    assert st["intro_seen"] and st["tours_seen"] == ["/trading"]
    c.post("/api/guide/restart")
    st = c.get("/api/guide").json()["state"]
    assert not st["intro_seen"] and st["tours_seen"] == []
