"""Market lots: edit (as if relisted), atomic cancel, the City Market buys tier 1 by tens, stuck tails go back,
and «will the city buy my lot?» hints.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


def run(c):
    return asyncio.run(c)


def ago(m):
    return (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()


class U:
    def __init__(self, id):
        self.id, self.username, self.display_name, self.email, self.wallet_address = id, id, id, None, None


async def world(monkeypatch, energy=30, biz=True):
    import server
    db = mongomock_motor.AsyncMongoMockClient()["lots"]
    monkeypatch.setattr(server, "db", db)
    await db.users.insert_many([
        {"id": "u1", "username": "u1", "language": "ru", "resources": {"energy": energy, "neuro_core": 5}},
        {"id": "u2", "username": "u2", "language": "en", "resources": {}},
    ])
    await db.market_listings.insert_one({"id": "L1", "seller_id": "u1", "seller_username": "u1", "resource_type": "energy",
                                         "amount": 20, "price_per_unit": 0.003, "total_price": 0.06, "status": "active",
                                         "created_at": ago(120)})
    if biz:   # a real business: no 30-unit cap on a lot
        await db.businesses.insert_one({"id": "B1", "owner": "u1", "business_type": "solar_panel", "level": 1})
    return server, db


def test_edit_grows_the_lot_from_the_warehouse_and_relists_it(monkeypatch):
    async def go():
        server, db = await world(monkeypatch)
        r = await server.edit_listing("L1", server.ListingEditRequest(amount=40), current_user=U("u1"))
        assert r["taken_from_warehouse"] == 20 and r["old_amount"] == 20
        new = r["listing"]
        assert new["id"] != "L1" and new["amount"] == 40 and new["status"] == "active"
        assert new["price_per_unit"] == 0.003 and new["edited_from"] == "L1"
        assert new["created_at"] > ago(1)                                  # listed anew → the city's wait restarts
        assert (await db.market_listings.find_one({"id": "L1"}))["status"] == "replaced"
        assert (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 10
        assert await db.market_listings.count_documents({"seller_id": "u1", "status": "active"}) == 1   # same slot
        assert await db.transactions.count_documents({"tx_type": "lot_edit", "user_id": "u1"}) == 1
    run(go())


def test_no_business_lot_is_capped_at_30(monkeypatch):
    async def go():
        server, db = await world(monkeypatch, energy=30, biz=False)
        with pytest.raises(Exception) as e:
            await server.edit_listing("L1", server.ListingEditRequest(amount=40), current_user=U("u1"))
        assert e.value.status_code == 400 and "30" in e.value.detail and "Без бизнеса" in e.value.detail
        r = await server.edit_listing("L1", server.ListingEditRequest(amount=30), current_user=U("u1"))
        assert r["listing"]["amount"] == 30
        # a new lot: same cap
        with pytest.raises(Exception) as e:
            await server.list_resource_for_sale(server.ResourceListingRequest(resource_type="energy", amount=40,
                                                price_per_unit=0.003), current_user=U("u1"))
        assert e.value.status_code == 400 and "Без бизнеса" in e.value.detail
    run(go())


def test_edit_shrinks_the_lot_and_changes_the_price(monkeypatch):
    async def go():
        server, db = await world(monkeypatch)
        r = await server.edit_listing("L1", server.ListingEditRequest(amount=10, price_per_unit=0.0025), current_user=U("u1"))
        assert r["returned_to_warehouse"] == 10 and r["listing"]["price_per_unit"] == 0.0025
        assert (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 40
    run(go())


def test_edit_refuses_more_than_lot_plus_warehouse_and_below_min_lot(monkeypatch):
    async def go():
        server, db = await world(monkeypatch, energy=30)
        with pytest.raises(Exception) as e:
            await server.edit_listing("L1", server.ListingEditRequest(amount=60), current_user=U("u1"))
        assert "50" in e.value.detail and "Не хватает" in e.value.detail       # 20 in the lot + 30 in the warehouse
        # tier 1: any number of units since v2.3 (it used to be at least 10)
        await server.edit_listing("L1", server.ListingEditRequest(amount=7), current_user=U("u1"))
        assert (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 43    # 13 went back to the warehouse
        new = await db.market_listings.find_one({"seller_id": "u1", "status": "active"})
        assert new and new["amount"] == 7
        with pytest.raises(Exception) as e:
            await server.edit_listing(new["id"], server.ListingEditRequest(amount=20), current_user=U("u2"))
        assert e.value.status_code == 403
    run(go())


def test_edit_counts_a_purchase_that_happened_a_moment_before(monkeypatch):
    """A buyer took 10 between the check and the swap: 10 were left, so 30 come from the warehouse for 40."""
    async def go():
        server, db = await world(monkeypatch, energy=30)
        cls = type(db.market_listings)
        real = cls.find_one_and_update

        async def racing(self, q, upd, **kw):
            if q.get("id") == "L1" and upd.get("$set", {}).get("status") == "replaced":
                await db.market_listings.update_one({"id": "L1"}, {"$inc": {"amount": -10}})
            return await real(self, q, upd, **kw)
        monkeypatch.setattr(cls, "find_one_and_update", racing)
        r = await server.edit_listing("L1", server.ListingEditRequest(amount=40), current_user=U("u1"))
        assert r["old_amount"] == 10 and r["taken_from_warehouse"] == 30
        assert (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 0
    run(go())


def test_edit_of_a_sold_lot_and_double_cancel_are_refused(monkeypatch):
    async def go():
        server, db = await world(monkeypatch)
        r = await server.cancel_listing("L1", current_user=U("u1"))
        assert r["returned"] == 20 and (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 50
        with pytest.raises(Exception) as e:
            await server.edit_listing("L1", server.ListingEditRequest(amount=20), current_user=U("u1"))
        assert e.value.status_code == 409 and "продан или снят" in e.value.detail
        with pytest.raises(Exception):
            await server.cancel_listing("L1", current_user=U("u1"))
        assert (await db.users.find_one({"id": "u1"}))["resources"]["energy"] == 50     # returned once
    run(go())


def test_tier1_is_traded_per_unit_so_no_tails_are_returned(monkeypatch):
    """Tier 1 used to trade only in tens; a 37-unit lot or a 7-unit rest can now be bought by anyone — nothing to fix."""
    async def go():
        import market_maker as mm
        db = mongomock_motor.AsyncMongoMockClient()["mm"]
        await db.users.insert_one({"id": "s", "username": "s", "language": "en", "resources": {}})
        await db.market_listings.insert_many([
            {"id": "A", "seller_id": "s", "resource_type": "energy", "amount": 37, "price_per_unit": 0.001,
             "status": "active", "created_at": ago(100)},
            {"id": "B", "seller_id": "s", "resource_type": "energy", "amount": 7, "price_per_unit": 0.001,
             "status": "active", "created_at": ago(100)}])
        assert await mm.fix_tier1_tails(db) == 0
        a, b = [await db.market_listings.find_one({"id": i}) for i in "AB"]
        assert a["amount"] == 37 and b["amount"] == 7 and b["status"] == "active"
        assert mm.is_tier1("energy") and not mm.is_tier1("neuro_core") and mm.TIER1_MIN_LOT == 1   # any number of units since v2.3
    run(go())


def test_hints_say_when_the_city_buys_or_why_not(monkeypatch):
    async def go():
        import market_maker as mm
        db = mongomock_motor.AsyncMongoMockClient()["hints"]
        seller = {"id": "s", "username": "s"}
        await db.users.insert_one(dict(seller))

        async def target(_db, _u):
            return "real"
        monkeypatch.setattr(mm, "payout_target", target)
        cfg = dict(mm.DEFAULT_CONFIG, real_buy_enabled=True, daily_budget_ton=5.0)

        async def get_cfg(_db):
            return cfg
        monkeypatch.setattr(mm, "get_config", get_cfg)
        buy_city, _ = mm.prices_city(cfg, "energy")
        cheap = buy_city / 1000 * 0.9
        lots = [{"id": "old", "resource_type": "energy", "amount": 20, "price_per_unit": cheap, "created_at": ago(40)},
                {"id": "new", "resource_type": "energy", "amount": 20, "price_per_unit": cheap, "created_at": ago(10)},
                {"id": "dear", "resource_type": "energy", "amount": 20, "price_per_unit": buy_city / 1000 * 2, "created_at": ago(40)},
                {"id": "t3", "resource_type": "neuro_core", "amount": 2, "price_per_unit": 1.0, "created_at": ago(40)}]
        h = await mm.seller_hints(db, seller, lots)
        assert h["old"] == {"state": "soon"}
        assert h["new"]["state"] == "wait" and 19 <= h["new"]["eta_min"] <= 21
        assert h["dear"]["state"] == "never" and h["dear"]["code"] == "price" and h["dear"]["price_city"] == round(buy_city, 2)
        assert h["t3"] == {"state": "never", "code": "resource"}
        cfg["real_buy_enabled"] = False
        assert (await mm.seller_hints(db, seller, lots[:1]))["old"]["code"] == "real_off"
    run(go())
