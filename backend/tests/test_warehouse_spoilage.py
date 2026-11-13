"""Daily warehouse spoilage (backend/warehouse_spoilage.py) + the level-0 claim with a full warehouse
(zero_business.grant_zero_consumption / clawback_lease_bonus).

    cd backend && python -m pytest tests/test_warehouse_spoilage.py -q
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
import warehouse_spoilage as ws  # noqa: E402

CFG = dict(ws.DEFAULTS)


def run(c):
    return asyncio.run(c)


# ───────────── plan (pure) ─────────────
def test_overflow_loses_20_and_the_rest_10():
    p = ws.plan({"energy": 95}, 50, 0, CFG)          # 50 fit → −5, 45 over → −9
    assert round(p["dec"]["energy"], 6) == 14
    assert p["overflow"] is True
    assert round(p["lost_in"], 6) == 5 and round(p["lost_over"], 6) == 9


def test_inside_the_limit_10_percent_every_day_same_share_for_all():
    p = ws.plan({"energy": 60, "biomass": 40}, 200, 0, CFG)
    assert round(p["dec"]["energy"], 6) == 6 and round(p["dec"]["biomass"], 6) == 4
    assert p["overflow"] is False


def test_at_least_one_unit_a_day():
    p = ws.plan({"energy": 5}, 50, 0, CFG)
    assert round(p["lost_units"], 6) == 1


def test_lots_take_space_but_do_not_spoil():
    p = ws.plan({"energy": 40}, 50, 30, CFG)          # room 20 → 20 fit (−2), 20 over (−4)
    assert round(p["dec"]["energy"], 6) == 6
    assert round(p["used_after"], 6) == 34 + 30


def test_tutorial_rewards_never_spoil():
    assert ws.plan({"neuro_core_tutorial": 1}, 50, 0, CFG) is None
    assert ws.plan({}, 50, 0, CFG) is None


def test_message_ru_mentions_overflow_only_when_there_is_one():
    t, b = ws.message_ru(ws.plan({"energy": 95}, 50, 0, CFG), CFG)
    assert "переполнения" in b and "−20%" in b
    t, b = ws.message_ru(ws.plan({"energy": 30}, 50, 0, CFG), CFG)
    assert "переполнения" not in b and "−10%" in b


# ───────────── run ─────────────
async def _db():
    db = mongomock_motor.AsyncMongoMockClient()["spoil"]
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    await db.users.insert_many([
        {"id": "u1", "email": "u1@x.io", "resources": {"energy": 95}},
        {"id": "u2", "email": "u2@x.io", "resources": {"energy": 95}, "decay_protected_until": future},
        {"id": "u3", "email": "u3@x.io", "resources": {"neuro_core_tutorial": 1}},
    ])
    return db


def test_run_spoils_notifies_with_30_min_translation_and_skips_protected(monkeypatch):
    sent = []

    async def fake_notify(db, user, **kw):
        sent.append((user["id"], kw))
    import core.notify
    monkeypatch.setattr(core.notify, "notify_user", fake_notify)

    async def go():
        db = await _db()
        st = await ws.run(db, force=True)
        u = {d["id"]: d async for d in db.users.find({}, {"_id": 0})}
        return st, u
    st, u = run(go())
    assert st["players"] == 1 and st["protected"] == 1
    assert round(u["u1"]["resources"]["energy"], 6) == 81
    assert u["u2"]["resources"]["energy"] == 95
    assert u["u3"]["resources"]["neuro_core_tutorial"] == 1
    assert [s[0] for s in sent] == ["u1"]
    assert sent[0][1]["translation_ttl_min"] == 30 and sent[0][1]["type_key"] == "warehouse_spoilage"


def test_run_once_a_day_and_not_before_the_hour(monkeypatch):
    async def fake_notify(db, user, **kw):
        return None
    import core.notify
    monkeypatch.setattr(core.notify, "notify_user", fake_notify)

    async def go():
        db = await _db()
        await db.game_settings.insert_one({"type": ws.SETTINGS_TYPE, "hour_msk": 0, "minute_msk": 0})
        a = await ws.run(db)
        b = await ws.run(db)
        await db.game_settings.update_one({"type": ws.SETTINGS_TYPE}, {"$set": {"hour_msk": 23, "minute_msk": 59}})
        await db.game_settings.delete_many({"type": "warehouse_spoilage_runs"})
        now_msk = datetime.now(timezone.utc).astimezone(ws.MSK)
        c = await ws.run(db)
        return a, b, c, now_msk
    a, b, c, now_msk = run(go())
    assert a.get("players") == 1
    assert b == {"skipped": "done_today"}
    if (now_msk.hour, now_msk.minute) < (23, 59):
        assert c == {"skipped": "not_yet"}


# ───────────── level-0 claim with a full warehouse ─────────────
def _t3_type():
    from business_config import BUSINESSES
    for k, v in BUSINESSES.items():
        if int(v.get("tier", 1) or 1) == 3:
            return k
    pytest.skip("no tier-3 business type")


def test_full_warehouse_claim_gives_nothing():
    import zero_business as zb

    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["zb_full"]
        await db.users.insert_one({"id": "u1", "resources": {"energy": 60}, "bonus_balance": 0})   # 60 / 50: full
        await db.businesses.insert_one({"id": "b1", "owner": "u1", "business_type": _t3_type(), "level": 0,
                                        "storage": {"capacity": 500}})                          # the claimed one
        await zb.grant_zero_consumption(db, "u1", _t3_type(), business_id="b1")
        return await db.users.find_one({"id": "u1"}, {"_id": 0}), await db.businesses.find_one({"id": "b1"}, {"_id": 0})
    u, b = run(go())
    assert u["resources"] == {"energy": 60}
    assert float(u.get("bonus_balance", 0)) == 0
    assert not b.get("lease_ton_bonus")


def test_free_warehouse_claim_gives_the_bonus_and_clawback_takes_the_whole_bonus_balance():
    import zero_business as zb

    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["zb_free"]
        await db.users.insert_one({"id": "u1", "resources": {}, "bonus_balance": 3})
        await db.businesses.insert_one({"id": "b1", "owner": "u1", "business_type": _t3_type(), "level": 0,
                                        "storage": {"capacity": 500}})
        await zb.grant_zero_consumption(db, "u1", _t3_type(), business_id="b1")
        u = await db.users.find_one({"id": "u1"}, {"_id": 0})
        b = await db.businesses.find_one({"id": "b1"}, {"_id": 0})
        took = await zb.clawback_lease_bonus(db, "u1", b)
        u2 = await db.users.find_one({"id": "u1"}, {"_id": 0})
        return u, b, took, u2
    u, b, took, u2 = run(go())
    assert float(u["bonus_balance"]) == 3 + zb.LEASE_TON_BONUS
    assert float(b["lease_ton_bonus"]) == zb.LEASE_TON_BONUS
    assert took == 3 + zb.LEASE_TON_BONUS and float(u2["bonus_balance"]) == 0
