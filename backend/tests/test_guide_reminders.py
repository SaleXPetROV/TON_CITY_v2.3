"""The guide's first-days reminders: 3 a day at most, the right players, once per day."""
import asyncio
from datetime import datetime, timezone, timedelta

import mongomock_motor
import pytest

import guide_reminders as gr


def run(c):
    return asyncio.get_event_loop().run_until_complete(c) if False else asyncio.run(c)


@pytest.fixture
def sent(monkeypatch):
    out = []
    import smart_notify

    async def fake_send(user, kind, vars_, ref=None):
        out.append((user["id"], kind, vars_))
        return {"sent": True}
    monkeypatch.setattr(smart_notify, "send", fake_send)
    return out


def test_daily_cap_is_three():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["g"]
        await db.users.insert_one({"id": "u"})
        got = [await gr._slot(db, "u", "2026-11-11") for _ in range(5)]
        assert got == [True, True, True, False, False]
        assert await gr._slot(db, "u", "2026-11-12")            # a new day — new slots
    run(go())


def test_spoil_warning_only_over_half_full(sent):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["g"]
        await db.users.insert_many([{"id": "full", "resources": {"energy": 300}}, {"id": "low", "resources": {"energy": 20}}])
        await db.businesses.insert_many([{"id": "b1", "owner": "full", "storage": {"capacity": 360}},
                                         {"id": "b2", "owner": "low", "storage": {"capacity": 360}}])
        n = await gr.spoil_warning(db, "2026-11-11")
        assert n == 1 and sent[0][0] == "full" and sent[0][1] == "guide_spoil" and sent[0][2]["units"] == 30
    run(go())


def test_keep_business_on_day_two(sent):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["g"]
        now = datetime.now(timezone.utc)
        await db.users.insert_many([{"id": "a", "balance_ton": 1.0, "language": "ru"}, {"id": "b"}])
        await db.businesses.insert_many([
            {"id": "x", "owner": "a", "business_type": "helios", "level": 0, "is_zero_business": True, "zero_map_price": 6.5,
             "created_at": (now - timedelta(hours=20)).isoformat(), "expires_at": (now + timedelta(hours=52)).isoformat()},
            {"id": "y", "owner": "b", "business_type": "helios", "level": 0, "is_zero_business": True,
             "created_at": (now - timedelta(hours=2)).isoformat()}])          # claimed today — not yet
        n = await gr.keep_business(db, "2026-11-11")
        assert n == 1 and sent[0][1] == "guide_keep" and sent[0][2]["need"] == "5 500"
    run(go())
