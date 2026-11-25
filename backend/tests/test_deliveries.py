"""Доставка по контрактам: the road between two lots, a truck that drives and unloads, a dark road slows it ×1.5, the
paid speed-up goes to the treasury, cargo that doesn't fit waits at the gate, the map shows the road only to the two
sides, contract-fed auto-shift, the one-time cleanup of the oligarchs / supply routes."""
import asyncio
import json
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import deliveries as dl  # noqa: E402

LAY = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "city_layout_v1.json")))


def run(c):
    return asyncio.run(c)


def _slot(district, i=0):
    return [s for s in LAY["slots"] if s["district"] == district][i]


async def _db():
    db = AsyncMongoMockClient()["t"]
    a, b = _slot(4, 3), _slot(3, 5)
    await db.users.insert_one({"id": "sel", "username": "miner", "language": "en", "balance_ton": 0.0, "bonus_balance": 0.0, "resources": {}})
    await db.users.insert_one({"id": "buy", "username": "maker", "language": "ru", "balance_ton": 10.0, "bonus_balance": 0.0, "resources": {}})
    await db.businesses.insert_one({"id": "bs", "owner": "sel", "business_type": "quartz_mine", "level": 3, "x": a["x"], "y": a["y"]})
    await db.businesses.insert_one({"id": "bb", "owner": "buy", "business_type": "chips_factory", "level": 1, "x": b["x"], "y": b["y"]})
    contract = {"id": "c1", "resource_type": "quartz", "seller_id": "sel", "buyer_id": "buy", "seller_username": "miner",
                "buyer_username": "maker", "daily_amount": 120}
    return db, contract


def test_every_lot_has_a_road():
    for s in LAY["slots"][:: 7]:
        assert dl._gates(s["x"], s["y"], s["w"], s["h"]), s


def test_the_road_follows_the_streets_without_zigzags():
    # the shortest road with the fewest turns: across the island it is a couple of straight legs, never a staircase
    r = dl.road_between((35, 10, 2, 2), (1, 13, 2, 2))
    assert r["tiles"] == 34 and len(r["corners"]) <= 3
    for a_, b_ in zip(r["corners"], r["corners"][1:]):
        assert a_[0] == b_[0] or a_[1] == b_[1]


def test_truck_drives_slower_in_the_dark_and_unloads():
    async def go():
        db, c = await _db()
        sh = await dl.dispatch(db, c, 120)
        assert sh["status"] == "in_transit" and sh["tiles"] > 5 and dl._unpack(sh["corners"]) and 4 in sh["districts"] and 3 in sh["districts"]
        s = await dl.get_settings(db)
        assert sh["minutes"] == dl.minutes_for(sh["tiles"], s) and sh["pos"] == 0 and sh["pos_n"] == sh["tiles"]
        # not there yet
        assert (await dl.tick(db))["arrived"] == 0
        assert not (await db.users.find_one({"id": "buy"}))["resources"].get("quartz")
        # the lit city: halfway after half the time, arrival unchanged
        t0 = dl._dt(sh["departed_at"])
        half = t0 + timedelta(minutes=sh["minutes"] / 2)
        d = dl._drive({**sh, "tick_at": dl._iso(t0)}, set(), 1.5, half)
        assert abs(d["pos"] - sh["tiles"] / 2) < 0.05 and abs((d["arrives_at"] - dl._dt(sh["arrives_at"])).total_seconds()) < 2
        # every district dark: the whole trip takes ×1.5, the truck still moves (a third of the way at half the time)
        all_dark = set(range(1, 10))
        d = dl._drive({**sh, "tick_at": dl._iso(t0)}, all_dark, 1.5, half)
        assert abs(d["pos"] - sh["tiles"] / 3) < 0.05 and d["dark"] and d["slow"]
        assert abs((d["arrives_at"] - t0).total_seconds() - sh["minutes"] * 60 * 1.5) < 2 and d["delayed_min"] > 0
        # only the first district dark: slower there, normal speed after it
        first = sh["districts"][0]
        dists = dl._tile_districts(sh)
        n_dark = sum(1 for x in dists if x == first)
        d = dl._drive({**sh, "tick_at": dl._iso(t0)}, {first}, 1.5, t0)
        base = sh["minutes"] * 60 / sh["tiles"]
        assert abs((d["arrives_at"] - t0).total_seconds() - base * (sh["tiles"] + 0.5 * n_dark)) < 2
        # through the scheduler: a blackout darkens the first district → the truck keeps going, arrival moves later
        import blackout
        orig = blackout.current

        async def dark(_db):
            return {"districts": {str(first): {"lit_at": None}}}
        blackout.current = dark
        try:
            await db.shipments.update_one({"id": sh["id"]}, {"$set": {"tick_at": dl._iso(dl._now() - timedelta(minutes=2))}})
            before = dl._dt(sh["arrives_at"])
            r = await dl.tick(db)
            after = await db.shipments.find_one({"id": sh["id"]})
            assert r["slow"] == 1 and after["slow"] and dl._dt(after["arrives_at"]) > before and after["pos"] > 0
        finally:
            blackout.current = orig
        # the road is behind it → it unloads into the buyer's warehouse
        await db.shipments.update_one({"id": sh["id"]}, {"$set": {"pos": float(sh["tiles"])}})
        r = await dl.tick(db)
        assert r["arrived"] == 1
        assert (await db.users.find_one({"id": "buy"}))["resources"]["quartz"] == 120
        assert (await db.shipments.find_one({"id": sh["id"]}))["status"] == "delivered"
    run(go())


def test_speedup_goes_to_the_treasury_once():
    async def go():
        db, c = await _db()
        sh = await dl.dispatch(db, c, 120)
        s = await dl.get_settings(db)
        price = dl.speedup_price(sh, s)
        assert price and price >= s["speedup_min_fee"]
        try:
            await dl.speedup(db, {"id": "stranger"}, sh["id"])
            raise AssertionError("a stranger sped it up")
        except dl.DeliveryError as e:
            assert e.code == "not_found"
        r = await dl.speedup(db, {"id": "buy"}, sh["id"])
        assert r["status"] == "delivered" and abs(r["paid_city"] - price) < 1
        u = await db.users.find_one({"id": "buy"})
        assert u["resources"]["quartz"] == 120 and abs((10.0 - u["balance_ton"]) * 1000 - r["paid_city"]) < 0.01
        tr = await db.admin_stats.find_one({"type": "treasury"})
        assert abs(tr["delivery_speedup_ton"] * 1000 - r["paid_city"]) < 0.01
        try:
            await dl.speedup(db, {"id": "buy"}, sh["id"])           # already there: no second payment
            raise AssertionError("paid twice")
        except dl.DeliveryError as e:
            assert e.code == "cannot"
    run(go())


def test_cargo_waits_at_the_gate_and_the_map_shows_the_road_only_to_the_two_sides():
    async def go():
        db, c = await _db()
        sh = await dl.dispatch(db, c, 120)
        from core import warehouse as wh
        orig = wh.room_for

        async def room(_db, _u, _r):
            return 50
        wh.room_for = room
        try:
            await db.shipments.update_one({"id": sh["id"]}, {"$set": {"pos": float(sh["tiles"])}})
            r = await dl.tick(db)
            assert r["waiting"] == 1
            w = await db.shipments.find_one({"id": sh["id"]})
            assert w["status"] == "waiting_room" and w["qty_left"] == 70
            assert (await db.users.find_one({"id": "buy"}))["resources"]["quartz"] == 50
        finally:
            wh.room_for = orig
        sh2 = await dl.dispatch(db, {**c, "id": "c2"}, 10)
        m_buyer = await dl.map_data(db, {"id": "buy"})
        m_other = await dl.map_data(db, {"id": "someone"})
        assert [x["id"] for x in m_buyer["mine"]] == [sh2["id"]] and m_buyer["mine"][0]["side"] == "in"
        assert not m_other["mine"] and [x["id"] for x in m_other["others"]] == [sh2["id"]] and "side" not in m_other["others"][0]
    run(go())


def test_contract_fed_auto_shift_and_cleanup():
    async def go():
        db, c = await _db()
        await db.tender_contracts.insert_one({"id": "k1", "status": "ACTIVE", "buyer_id": "buy", "resource_type": "quartz", "daily_amount": 10 ** 6})
        assert "bb" not in await dl.contract_fed_business_ids(db)      # repair kits are not covered
        await db.tender_contracts.insert_one({"id": "k2", "status": "ACTIVE", "buyer_id": "buy", "resource_type": "repair_kits", "daily_amount": 10 ** 6})
        assert "bb" in await dl.contract_fed_business_ids(db)
        await db.users.insert_one({"id": "npc-baron_kvant", "is_npc": True})
        await db.market_listings.insert_one({"id": "l1", "seller_id": "npc-baron_kvant", "status": "active"})
        await db.chat_messages.insert_one({"id": "m1", "sender_id": "npc-baron_kvant"})
        await db.notifications.insert_one({"id": "n1", "type": "supply_route", "payload": {"open_path": "/supply"}})
        await db.notifications.insert_one({"id": "n2", "type": "tender", "payload": {"open_path": "/trading"}})
        out = await dl.retire_legacy(db)
        assert out["npc_users"] == 1 and out["npc_lots"] == 1 and out["npc_chat"] == 1 and out["notices"] == 1
        assert await db.notifications.count_documents({}) == 1
        assert await dl.retire_legacy(db) == {}                          # once
    run(go())


def test_contract_clearing_puts_the_goods_on_the_road():
    async def go():
        db, c = await _db()
        import routes.tenders as tn
        old = tn.db
        tn.db = db
        try:
            await db.users.update_one({"id": "sel"}, {"$set": {"resources.quartz": 500}})
            contract = {**c, "price_per_unit": 3.0, "tax_rate": 0.15, "status": "ACTIVE", "tier": 1, "payment_hour": 0}
            await db.tender_contracts.insert_one(dict(contract))
            await tn._process_tick(contract)
            sel = await db.users.find_one({"id": "sel"})
            buy = await db.users.find_one({"id": "buy"})
            assert sel["resources"]["quartz"] == 380 and sel["balance_ton"] > 0      # goods left, money came
            assert not buy["resources"].get("quartz")                                 # …but nothing arrived yet
            sh = await db.shipments.find_one({"contract_id": "c1"})
            assert sh and sh["status"] == "in_transit" and sh["qty"] == 120
            assert (await db.tender_contracts.find_one({"id": "c1"}))["last_shipment_id"] == sh["id"]
        finally:
            tn.db = old
    run(go())
