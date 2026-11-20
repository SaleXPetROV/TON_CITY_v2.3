"""Блэкаут острова: needs, gifts, a district lit (rewards, heroes), a lost district (penalty, refund)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import blackout as bk  # noqa: E402


def run(c):
    return asyncio.run(c)


async def _drain():
    for _ in range(50):
        if not bk._BG:
            return
        await asyncio.gather(*list(bk._BG), return_exceptions=True)


async def _db(players=3):
    db = AsyncMongoMockClient()["t"]
    for i in range(players):
        await db.users.insert_one({"id": f"u{i}", "username": f"p{i}", "language": "ru", "bonus_balance": 0.0,
                                   "resources": {r: 10_000 for r in bk.TIER1 + bk.TIER2}})
        await db.businesses.insert_one({"id": f"b{i}", "owner": f"u{i}", "level": 1, "district_id": 2})
    await bk.save_settings(db, {"enabled": True})
    return db


def test_needs_scale_with_players():
    s = dict(bk.DEFAULTS)
    small = bk.plan_needs(1, s, 7)
    big = bk.plan_needs(100, s, 7)
    assert set(small) == {"1", "2", "3", "4"}
    assert all(len(v) == 3 for v in small.values())
    assert any(r in bk.TIER2 for r in small["1"])                      # the Core needs one tier-2 resource
    assert all(set(big[d]) == set(small[d]) for d in small)            # same seed → same resources
    assert sum(big["2"].values()) > sum(small["2"].values()) * 10       # 100 players need much more
    assert min(small["3"].values()) >= int(s["min_units"] * 0.85)


def test_gift_light_and_rewards():
    async def go():
        db = await _db()
        ev = await bk.start(db, by="test", hours=2)
        await _drain()
        assert (await db.notifications.count_documents({"type": "blackout"})) == 3   # everyone was told
        need = ev["districts"]["2"]["need"]
        res = list(need)
        # p0 gives a part, the amount is capped by what is still needed
        r = await bk.contribute(db, {"id": "u0", "username": "p0"}, 2, res[0], need[res[0]] + 500)
        assert r["qty"] == need[res[0]] and not r["lit"]
        u0 = await db.users.find_one({"id": "u0"})
        assert u0["resources"][res[0]] == 10_000 - need[res[0]]
        try:
            await bk.contribute(db, {"id": "u1", "username": "p1"}, 2, res[0], 5)
            assert False, "filled resource accepted"
        except bk.BlackoutError as e:
            assert str(e) == "filled"
        try:
            await bk.contribute(db, {"id": "u1", "username": "p1"}, 2, "nft" if "nft" not in need else "chips", 5)
            assert False
        except bk.BlackoutError as e:
            assert str(e) == "not_needed"
        await bk.contribute(db, {"id": "u1", "username": "p1"}, 2, res[1], need[res[1]])
        r = await bk.contribute(db, {"id": "u2", "username": "p2"}, 2, res[2], need[res[2]])
        assert r["lit"]
        await _drain()
        e = await db.blackout_events.find_one({"id": ev["id"]})
        d2 = e["districts"]["2"]
        assert d2["lit_at"] and len(d2["heroes"]) == 3 and d2["bonus_until"]
        # rewards: 120% of the value of the gift, as bonus $CITY
        p0 = await db.blackout_players.find_one({"event_id": ev["id"], "user_id": "u0"})
        want = round(need[res[0]] * bk.value_of(res[0]) * 1.2, 2)
        assert abs(p0["reward"] - want) < 0.05
        u0 = await db.users.find_one({"id": "u0"})
        assert abs(u0["bonus_balance"] * 1000 - want) < 0.5
        try:
            await bk.contribute(db, {"id": "u0", "username": "p0"}, 2, res[0], 1)
            assert False
        except bk.BlackoutError as e:
            assert str(e) == "already_lit"
        # lit district shines: +5% for its businesses
        assert (await bk.district_multipliers(db)).get(2) == 1.05
        towers = await bk.heroes_map(db)
        assert towers["2"]["names"][0] in {"p0", "p1", "p2"}
        st = await bk.state(db, {"id": "u0"})
        assert st["active"]["districts"]["2"]["pct"] == 100.0 and st["me"]["points"] > 0
        assert st["feed"] and st["board"]
    run(go())


def test_time_over_penalty_and_refund():
    async def go():
        db = await _db()
        ev = await bk.start(db, by="test", hours=1)
        await _drain()
        need = ev["districts"]["3"]["need"]
        r0 = list(need)[0]
        await bk.contribute(db, {"id": "u0", "username": "p0"}, 3, r0, 20)
        await db.blackout_events.update_one({"id": ev["id"]}, {"$set": {"ends_at": "2000-01-01T00:00:00+00:00"}})
        bk.invalidate_mult()
        assert await bk.tick(db) == "ended"
        await _drain()
        e = await db.blackout_events.find_one({"id": ev["id"]})
        assert e["status"] == "ended" and e["districts"]["3"]["dark_until"]
        p0 = await db.blackout_players.find_one({"event_id": ev["id"], "user_id": "u0"})
        assert abs(p0["refund"] - round(20 * bk.value_of(r0) * 0.6, 2)) < 0.05
        m = await bk.district_multipliers(db)
        assert m.get(3) == 0.9 and m.get(1) == 0.9
        assert await bk.current(db) is None
        try:
            await bk.contribute(db, {"id": "u0", "username": "p0"}, 3, r0, 1)
            assert False
        except bk.BlackoutError as e:
            assert str(e) == "no_event"
    run(go())


def test_auto_schedule():
    async def go():
        db = await _db()
        s = await bk.save_settings(db, {"auto": True, "interval_days": 3})
        assert s["enabled"] and s["auto"]
        assert s["next_at"]
        assert await bk.tick(db) is None                  # not due yet
        await db.admin_settings.update_one({"type": "blackout"}, {"$set": {"next_at": "2000-01-01T00:00:00+00:00"}})
        assert await bk.tick(db) == "started"
        await _drain()
        assert (await bk.get_settings(db))["next_at"] is None
        try:
            await bk.start(db)
            assert False
        except ValueError:
            pass
    run(go())


def test_switched_off_and_admin_needs():
    async def go():
        db = await _db()
        await bk.save_settings(db, {"enabled": False, "auto": True})
        assert (await bk.get_settings(db))["auto"] is False          # off means off
        try:
            await bk.start(db)
            assert False
        except ValueError:
            pass
        st = await bk.state(db, {"id": "u0"})
        assert st["enabled"] is False and st["active"] is None
        await bk.save_settings(db, {"enabled": True})
        # the admin's own amounts
        try:
            bk.clean_needs({"1": {"gold": 5}, "2": {"energy": 1}, "3": {"energy": 1}, "4": {"energy": 1}})
            assert False
        except ValueError:
            pass
        needs = {"1": {"energy": 30, "chips": 2}, "2": {"scrap": 40}, "3": {"quartz": 10, "cu": 10}, "4": {"traffic": 5}}
        ev = await bk.start(db, by="t", hours=3, needs=needs)
        await _drain()
        assert ev["districts"]["2"]["need"] == {"scrap": 40}
        await bk.contribute(db, {"id": "u0", "username": "p0"}, 2, "scrap", 25)
        # the admin lowers district 2 to 20: already covered → lights up at once
        await bk.set_needs(db, {"2": {"scrap": 20}})
        await _drain()
        e = await bk.current(db)
        assert e["districts"]["2"]["lit_at"]
        await bk.set_needs(db, {"4": {"traffic": 50, "energy": 10}})
        e = await bk.current(db)
        assert e["districts"]["4"]["need"] == {"traffic": 50, "energy": 10} and e["districts"]["4"]["got"] == {"traffic": 0, "energy": 0}
        # switching the event off ends the running one without a penalty
        await bk.save_settings(db, {"enabled": False})
        await _drain()
        assert await bk.current(db) is None
        assert await bk.district_multipliers(db) == {}
    run(go())
