"""Spot order book: whole units, cents, escrow, price–time priority, maker's price, IOC market orders, cancel."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import HTTPException  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import spot_market as sm  # noqa: E402

RES = "quartz"


class _CU:
    def __init__(self, uid):
        self.id = uid


async def _setup():
    db = AsyncMongoMockClient()["t"]
    for uid, bal in (("b1", 100.0), ("b2", 100.0), ("s1", 10.0), ("s2", 10.0)):
        await db.users.insert_one({"id": uid, "username": uid, "balance_ton": bal, "bonus_balance": 0.0,
                                   "resources": {RES: 1000}})
        await db.businesses.insert_one({"id": f"biz-{uid}", "owner": uid, "business_type": "quartz_mine", "level": 1})
    settled = []

    async def settle(lot, buyer, buyer_id, bf, units, total_ton, upd, stock_after, **kw):
        # what server._settle_market_purchase does that matters here: units to the buyer, money to the seller
        await db.users.update_one({"id": buyer_id}, {"$inc": {f"resources.{lot['resource_type']}": units}})
        await db.users.update_one({"id": lot["seller_id"]}, {"$inc": {"balance_ton": total_ton}})
        await sm.record_trade(db, lot, buyer_id, units, total_ton)
        settled.append((lot["seller_id"], buyer_id, units, round(total_ton, 9)))
        return {"seller_tax": 0.0}

    async def list_resource(req, cu):
        n = int(req.amount)
        r = await db.users.update_one({"id": cu.id, f"resources.{req.resource_type}": {"$gte": n}}, {"$inc": {f"resources.{req.resource_type}": -n}})
        if not r.modified_count:
            raise HTTPException(status_code=400, detail="not_enough")
        lot = {"id": f"lot-{len(settled)}-{cu.id}-{req.price_per_unit}-{n}", "seller_id": cu.id, "resource_type": req.resource_type,
               "amount": n, "price_per_unit": req.price_per_unit, "status": "active", "created_at": sm._iso()}
        await asyncio.sleep(0.002)
        await db.market_listings.insert_one(dict(lot))
        return {"listing": lot}

    async def cancel_listing(lid, cu):
        l = await db.market_listings.find_one_and_update({"id": lid, "status": "active"}, {"$set": {"status": "cancelled"}})
        await db.users.update_one({"id": cu.id}, {"$inc": {f"resources.{l['resource_type']}": l["amount"]}})
        return {"status": "cancelled", "returned": l["amount"]}

    async def debit(match, amount):
        r = await db.users.update_one({**match, "balance_ton": {"$gte": amount}}, {"$inc": {"balance_ton": -amount}})
        return {"ok": bool(r.modified_count), "from_real": amount, "from_bonus": 0.0}

    async def tat(u):
        return float((await db.users.find_one({"id": u["id"]}))["balance_ton"])

    async def insufficient(u, need):
        return HTTPException(status_code=400, detail="insufficient")

    async def free(u):
        return 10 ** 6

    async def keys(uid):
        return [uid]

    async def none(*a):
        return None

    async def tax(*a):
        return 0.15

    sm.init(db, settle=settle, list_resource=list_resource, listing_req=lambda **kw: type("R", (), kw), cancel_listing=cancel_listing,
            free_warehouse=free, tat_live=tat, insufficient=insufficient, debit=debit,
            businesses_query=lambda k: {"owner": {"$in": list(k)}}, owner_keys=keys, no_business_cap=30,
            attribute_biz=none, tax_rate=tax, system_price=none)
    return db, settled


def _o(**kw):
    return sm.OrderIn(resource_id=RES, **kw)


async def _u(db, uid):
    return await db.users.find_one({"id": uid}, {"_id": 0})


def test_cents_and_whole_units():
    assert sm.to_cents("3.6") == 360 and sm.to_cents("0.005") == 1 and sm.cents_str(1234) == "12.34"
    assert sm.cents_to_ton(360) == 0.0036 and sm.ton_to_cents(0.0036) == 360
    try:
        sm.OrderIn(resource_id=RES, side="buy", amount=0)
        raise AssertionError("zero amount accepted")
    except Exception:
        pass


def test_price_time_priority_and_the_makers_price():
    async def go():
        db, settled = await _setup()
        # two sellers at 4.00 (s1 first), one at 3.90
        await sm.place_sell(await _u(db, "s1"), _CU("s1"), _o(side="sell", amount=50, price="4.00"))
        await sm.place_sell(await _u(db, "s2"), _CU("s2"), _o(side="sell", amount=50, price="4.00"))
        await sm.place_sell(await _u(db, "s2"), _CU("s2"), _o(side="sell", amount=10, price="3.90"))
        b = await sm.book(RES)
        assert b["asks"][0] == {"price": "3.90", "price_cents": 390, "amount": 10} and b["asks"][1]["amount"] == 100
        # a buyer with a limit of 5.00 takes 30: 10 @ 3.90 (cheapest), then 20 @ 4.00 from s1 (older), pays the lots' prices
        r = await sm.place_buy(await _u(db, "b1"), _o(side="buy", amount=30, price="5.00"))
        assert r["filled"] == 30 and r["status"] == "filled"
        assert [(x[0], x[2]) for x in settled] == [("s2", 10), ("s1", 20)]
        b1 = await _u(db, "b1")
        assert abs(b1["balance_ton"] - (100 - (10 * 0.0039 + 20 * 0.0040))) < 1e-9          # the 5.00 limit's surplus came back
        assert not await db.market_orders.find_one({"status": "active"})                      # filled → closed, escrow empty
    asyncio.run(go())


def test_a_limit_buy_waits_with_frozen_money_and_a_seller_meets_it():
    async def go():
        db, settled = await _setup()
        r = await sm.place_buy(await _u(db, "b1"), _o(side="buy", amount=100, price="3.00"))
        assert r["status"] == "open" and r["rest"] == 100
        assert abs((await _u(db, "b1"))["balance_ton"] - (100 - 0.3)) < 1e-9                  # 100 × 3.00 $CITY frozen
        await sm.place_buy(await _u(db, "b2"), _o(side="buy", amount=40, price="3.20"))      # higher price → first
        # a seller asks 2.50 for 120: 40 to b2 at 3.20, then 80 to b1 at 3.00 (the buyers' prices)
        r = await sm.place_sell(await _u(db, "s1"), _CU("s1"), _o(side="sell", amount=120, price="2.50"))
        assert r["filled"] == 120 and r["rest"] == 0
        assert settled[0][1:] == ("b2", 40, round(40 * 0.0032, 9)) and settled[1][1:] == ("b1", 80, round(80 * 0.0030, 9))
        mine = await sm.my_orders(await _u(db, "b1"))
        assert len(mine) == 1 and mine[0]["remaining_amount"] == 20 and mine[0]["filled_amount"] == 80
        assert mine[0]["progress_percent"] == 80.0 and mine[0]["total_locked_value"] == "60.00"
        # cancel: the frozen rest (20 × 3.00) comes back
        before = (await _u(db, "b1"))["balance_ton"]
        await sm.cancel(await _u(db, "b1"), _CU("b1"), mine[0]["order_id"])
        assert abs((await _u(db, "b1"))["balance_ton"] - before - 0.06) < 1e-9
        assert await sm.my_orders(await _u(db, "b1")) == []
    asyncio.run(go())


def test_market_orders_fill_what_the_book_has_and_keep_nothing():
    async def go():
        db, settled = await _setup()
        await sm.place_sell(await _u(db, "s1"), _CU("s1"), _o(side="sell", amount=30, price="4.00"))
        await sm.place_sell(await _u(db, "s2"), _CU("s2"), _o(side="sell", amount=30, price="4.50"))
        r = await sm.place_buy(await _u(db, "b1"), _o(side="buy", order_type="market", amount=100))
        assert r["filled"] == 60 and r["order_id"] is None                                       # from the lowest price up
        assert (await sm.book(RES))["asks"] == []
        # a market sell meets the bids, the unsold rest goes back to the warehouse
        await sm.place_buy(await _u(db, "b2"), _o(side="buy", amount=25, price="2.00"))
        have = (await _u(db, "s1"))["resources"][RES]
        r = await sm.place_sell(await _u(db, "s1"), _CU("s1"), _o(side="sell", order_type="market", amount=40))
        assert r["filled"] == 25
        assert (await _u(db, "s1"))["resources"][RES] == have - 25
        assert not await db.market_listings.find_one({"status": {"$in": ["active", "matching"]}})
    asyncio.run(go())


def test_no_self_trade_and_the_tape():
    async def go():
        db, settled = await _setup()
        await sm.place_sell(await _u(db, "s1"), _CU("s1"), _o(side="sell", amount=10, price="4.00"))
        await sm.place_buy(await _u(db, "s1"), _o(side="buy", amount=10, price="5.00"))       # own lot is skipped
        assert settled == []
        await sm.place_buy(await _u(db, "b1"), _o(side="buy", amount=10, price="5.00"))
        b = await sm.book(RES)
        assert b["last"] == "4.00" and b["best_bid"] == "5.00"                                 # s1's own bid still waits
        t = await sm.my_trades(await _u(db, "b1"))
        assert t[0]["side"] == "buy" and t[0]["amount"] == 10 and t[0]["price_per_item"] == "4.00"
    asyncio.run(go())
