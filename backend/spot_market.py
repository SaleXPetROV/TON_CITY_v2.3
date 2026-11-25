"""Spot order book for resources (Торговля → стакан, как на криптобирже).

Owner's specification (15 Nov):
  • amounts are WHOLE units (int); prices and totals are $CITY to the hundredth — kept as fixed point: integer cents
    of $CITY (`price_cents`) plus the decimal string (`price_per_item` "12.34"); arithmetic in `Decimal`.
    (Decimal128 is not stored: the test database — FerretDB — cannot keep it; integer cents are exactly as precise.)
  • escrow: a SELL order takes the units off the seller's warehouse at once; a BUY order freezes price × amount $CITY;
    a cancel gives back what is left.
  • price–time priority (FIFO): asks by price ascending, bids by price descending, equal prices — the older first.
    A trade is made at the price of the order that was already in the book (maker's price); a buyer whose limit was
    higher gets the difference back at once.
  • market order: fills against the book from the best price on until the amount (or the money / the warehouse) runs
    out; what is not filled is not kept (IOC). Limit order: fills what crosses, the rest stays in the book (GTC).

How it sits in the game (nothing of the old economy is lost):
  • a SELL order IS a lot of the players' market (`market_listings`): the City Market, its 48-h return, the guide's
    first sale, the analytics and «В продаже» on the map keep reading lots as before. A lot gets the order's fields
    (`initial_amount`, `price_cents`, `price_per_item`, `side`).
  • a BUY order lives in `market_orders` (side "buy") with its frozen money (`escrow_ton`, of it `escrow_bonus_ton`).
  • every fill is settled by the same code as «Купить лот» (server._settle_market_purchase): the seller's tier tax and
    buffs, bonus/real payout by his business level, credit repayment, tax haven, referral split, treasury, history,
    quests, notices.
  • `trade_history` — the tape of every trade (price, amount, both sides): the last price, the 24-h change.
  • race safety: one resource's book is matched by one request at a time (a lock document in `market_locks`, with
    expiry, works across several server processes); every take of units / money is a conditional atomic update, so
    a lot or an order can never be taken twice. (MongoDB transactions need a replica set; the test base has none —
    the lock + conditional updates give the same guarantee here.)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CITY_PER_TON = 1000
CENTS_PER_TON = 100_000                  # 1 TON = 1000 $CITY = 100 000 cents of $CITY
MAX_BUY_ORDERS = 10                      # active buy orders per player
LOCK_TTL_S = 10
_D = {}                                  # dependencies from server.py (init)
_db = None
_local_locks: Dict[str, asyncio.Lock] = {}


def init(db, **deps) -> None:
    global _db
    _db = db
    _D.update(deps)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat()


# ───────────────────────────── money: integer cents of $CITY ─────────────────────────────
def to_cents(city: Any) -> int:
    """A $CITY price typed by a player → integer cents (to the hundredth, half up)."""
    try:
        d = Decimal(str(city)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        raise HTTPException(status_code=400, detail="bad_price")
    return int(d * 100)


def cents_str(c: int) -> str:
    return str((Decimal(int(c)) / 100).quantize(Decimal("0.01")))


def cents_to_ton(c: int) -> float:
    return float(Decimal(int(c)) / CENTS_PER_TON)


def ton_to_cents(t: float) -> int:
    return int((Decimal(str(t)) * CENTS_PER_TON).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def lot_cents(l: Dict[str, Any]) -> int:
    """The price of a lot (a sell order) in cents; old lots keep their price in TON per unit."""
    if l.get("price_cents") is not None:
        return int(l["price_cents"])
    return ton_to_cents(float(l.get("price_per_unit") or 0))


# ───────────────────────────── the book lock ─────────────────────────────
class _BookLock:
    """One request matches one resource's book at a time — in this process (asyncio.Lock) and across processes
    (a document in `market_locks` that expires by itself if a process dies holding it)."""

    def __init__(self, resource: str):
        self.r = resource
        self.token = uuid.uuid4().hex

    async def __aenter__(self):
        self.local = _local_locks.setdefault(self.r, asyncio.Lock())
        await self.local.acquire()
        deadline = _now() + timedelta(seconds=LOCK_TTL_S)
        while True:
            now = _now()
            try:
                got = await _db.market_locks.find_one_and_update(
                    {"_id": self.r, "until": {"$lt": _iso(now)}},
                    {"$set": {"until": _iso(now + timedelta(seconds=LOCK_TTL_S)), "token": self.token}})
                if got is not None:
                    return self
                if not await _db.market_locks.find_one({"_id": self.r}):
                    await _db.market_locks.insert_one({"_id": self.r, "until": _iso(now + timedelta(seconds=LOCK_TTL_S)),
                                                       "token": self.token})
                    return self
            except Exception as e:  # noqa: BLE001  (a duplicate insert = somebody else got it first)
                logger.debug(f"book lock {self.r}: {e}")
            if _now() > deadline:
                self.local.release()
                raise HTTPException(status_code=503, detail="market_busy")
            await asyncio.sleep(0.05)

    async def __aexit__(self, *exc):
        try:
            await _db.market_locks.update_one({"_id": self.r, "token": self.token}, {"$set": {"until": _iso(_now() - timedelta(seconds=1))}})
        finally:
            self.local.release()


# ───────────────────────────── the tape ─────────────────────────────
async def record_trade(db, listing: Dict[str, Any], buyer_id: str, units: int, total_ton: float) -> None:
    """One trade on the tape (`trade_history`). Called by every P2P sale and every City Market purchase."""
    units = int(units or 0)
    if units <= 0 or listing.get("tutorial"):
        return
    total_c = ton_to_cents(total_ton)
    price_c = int((Decimal(total_c) / units).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    await db.trade_history.insert_one({
        "id": str(uuid.uuid4()), "resource_id": listing.get("resource_type"), "buyer_id": buyer_id,
        "seller_id": listing.get("seller_id"), "amount": units, "price_cents": price_c, "price_per_item": cents_str(price_c),
        "total_cents": total_c, "total_price": cents_str(total_c), "sell_order_id": listing.get("id"),
        "buy_order_id": listing.get("_buy_order_id"), "executed_at": _iso()})


# ───────────────────────────── reads ─────────────────────────────
def _ask_query(resource: str) -> Dict[str, Any]:
    return {"resource_type": resource, "status": "active", "amount": {"$gt": 0}, "tutorial": {"$ne": True}}


def _bid_query(resource: str) -> Dict[str, Any]:
    return {"resource_id": resource, "side": "buy", "status": "active", "remaining_amount": {"$gt": 0}}


async def _asks(resource: str, limit: int = 500) -> List[Dict[str, Any]]:
    rows = await _db.market_listings.find(_ask_query(resource), {"_id": 0}).limit(limit).to_list(limit)
    rows.sort(key=lambda l: (lot_cents(l), str(l.get("created_at") or "")))
    return rows


async def _bids(resource: str, limit: int = 500) -> List[Dict[str, Any]]:
    rows = await _db.market_orders.find(_bid_query(resource), {"_id": 0}).limit(limit).to_list(limit)
    rows.sort(key=lambda o: (-int(o["price_cents"]), str(o.get("created_at") or "")))
    return rows


def _bucket(c: int, step_c: int, up: bool) -> int:
    if step_c <= 1:
        return c
    q = c // step_c * step_c
    return q + step_c if (up and q < c) else q


async def book(resource: str, step: str = "0.01", depth: int = 20) -> Dict[str, Any]:
    """The aggregated book: asks (price ascending) and bids (price descending) by price level of `step` $CITY,
    the mid price, the last trade and its 24-h change, the buy/sell share of the money in the book."""
    step_c = max(1, to_cents(step))
    asks, bids = await _asks(resource), await _bids(resource)
    lv_a: Dict[int, int] = {}
    for l in asks:
        k = _bucket(lot_cents(l), step_c, up=True)
        lv_a[k] = lv_a.get(k, 0) + int(l.get("amount") or 0)
    lv_b: Dict[int, int] = {}
    for o in bids:
        k = _bucket(int(o["price_cents"]), step_c, up=False)
        lv_b[k] = lv_b.get(k, 0) + int(o.get("remaining_amount") or 0)
    A = sorted(lv_a.items())[:depth]
    B = sorted(lv_b.items(), key=lambda x: -x[0])[:depth]
    best_a = lot_cents(asks[0]) if asks else None
    best_b = int(bids[0]["price_cents"]) if bids else None
    last = await _db.trade_history.find_one({"resource_id": resource}, {"_id": 0}, sort=[("executed_at", -1)])
    day_ago = await _db.trade_history.find_one({"resource_id": resource, "executed_at": {"$lte": _iso(_now() - timedelta(hours=24))}},
                                               {"_id": 0}, sort=[("executed_at", -1)])
    if best_a is not None and best_b is not None:
        mid = (best_a + best_b) // 2
    else:
        mid = best_a if best_a is not None else best_b if best_b is not None else (last or {}).get("price_cents")
    last_c = (last or {}).get("price_cents")
    ch = None
    if last_c and day_ago and day_ago.get("price_cents"):
        ch = round((last_c - day_ago["price_cents"]) / day_ago["price_cents"] * 100, 2)
    val_a = sum(lot_cents(l) * int(l.get("amount") or 0) for l in asks)
    val_b = sum(int(o["price_cents"]) * int(o.get("remaining_amount") or 0) for o in bids)
    tot = val_a + val_b
    return {"resource_id": resource, "step": cents_str(step_c),
            "asks": [{"price": cents_str(p), "price_cents": p, "amount": a} for p, a in A],
            "bids": [{"price": cents_str(p), "price_cents": p, "amount": a} for p, a in B],
            "best_ask": cents_str(best_a) if best_a is not None else None, "best_bid": cents_str(best_b) if best_b is not None else None,
            "mid": cents_str(mid) if mid is not None else None, "last": cents_str(last_c) if last_c else None,
            "change_24h": ch, "buy_share": round(val_b / tot * 100) if tot else 50, "sell_share": round(val_a / tot * 100) if tot else 50,
            "server_now": _iso()}


def _order_view(o: Dict[str, Any], side: str) -> Dict[str, Any]:
    if side == "sell":
        price_c = lot_cents(o)
        rem = int(o.get("amount") or 0)
        init = max(int(o.get("initial_amount") or rem), rem)
        oid, res = o["id"], o.get("resource_type")
        locked = {"kind": "resource", "amount": rem, "value": cents_str(price_c * rem)}
        otype = o.get("order_type", "limit")
    else:
        price_c = int(o["price_cents"])
        rem = int(o.get("remaining_amount") or 0)
        init = int(o.get("initial_amount") or rem)
        oid, res = o["id"], o.get("resource_id")
        locked = {"kind": "city", "amount": round(float(o.get("escrow_ton") or 0) * CITY_PER_TON, 2), "value": cents_str(price_c * rem)}
        otype = o.get("order_type", "limit")
    filled = max(0, init - rem)
    return {"order_id": oid, "resource_id": res, "side": side, "order_type": otype, "price_per_item": cents_str(price_c),
            "price_cents": price_c, "initial_amount": init, "remaining_amount": rem, "filled_amount": filled,
            "progress_percent": round(filled / init * 100, 1) if init else 0.0,
            "total_locked_value": cents_str(price_c * rem), "locked": locked, "status": "active",
            "created_at": o.get("created_at"), "can_cancel": rem > 0}


async def my_orders(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    uid = user["id"]
    sells = await _db.market_listings.find({"seller_id": uid, "status": "active", "tutorial": {"$ne": True}}, {"_id": 0}).to_list(200)
    buys = await _db.market_orders.find({"user_id": uid, "side": "buy", "status": "active"}, {"_id": 0}).to_list(200)
    out = [_order_view(o, "sell") for o in sells] + [_order_view(o, "buy") for o in buys]
    # «Выкуп городом через N мин» on my sell orders (they are lots): market_maker.seller_hints, as on the old lot cards
    if sells:
        try:
            import market_maker
            hints = await market_maker.seller_hints(_db, user, sells)
            now = _now()
            for o in out:
                h = hints.get(o["order_id"]) if o["side"] == "sell" else None
                if not h:
                    continue
                if h.get("state") == "wait" and h.get("eta_min") is not None:
                    secs = h.get("eta_sec") if h.get("eta_sec") is not None else int(h["eta_min"]) * 60
                    h["eta_at"] = _iso(now + timedelta(seconds=int(secs)))
                o["city_buyout"] = h
        except Exception as e:  # noqa: BLE001
            logger.debug(f"spot city buyout hints: {e}")
    out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return out


# ───────────────────────────── money of a buy order ─────────────────────────────
async def _take_escrow(order_id: str, ton: float) -> Optional[Dict[str, float]]:
    """Use `ton` of a buy order's frozen money; returns {real, bonus} of it (the order's own bonus share)."""
    o = await _db.market_orders.find_one({"id": order_id}, {"_id": 0, "escrow_ton": 1, "escrow_bonus_ton": 1})
    if not o:
        return None
    esc, bon = float(o.get("escrow_ton") or 0), float(o.get("escrow_bonus_ton") or 0)
    ton = min(ton, esc)
    b = round(bon * (ton / esc), 9) if esc > 0 else 0.0
    r = await _db.market_orders.update_one({"id": order_id, "escrow_ton": {"$gte": ton - 1e-9}},
                                           {"$inc": {"escrow_ton": -ton, "escrow_bonus_ton": -b}})
    if not r.modified_count:
        return None
    return {"real": round(ton - b, 9), "bonus": b}


async def _refund(user_id: str, part: Dict[str, float]) -> None:
    inc = {}
    if part.get("real", 0) > 0:
        inc["balance_ton"] = round(part["real"], 9)
    if part.get("bonus", 0) > 0:
        inc["bonus_balance"] = round(part["bonus"], 9)
    if inc:
        await _db.users.update_one({"id": user_id}, {"$inc": inc})


# ───────────────────────────── one fill ─────────────────────────────
async def _fill(lot: Dict[str, Any], buyer: Dict[str, Any], units: int, price_c: int, paid: Dict[str, float],
                buy_order_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Take `units` from the lot (atomically) and settle the sale at `price_c` with money already taken from the
    buyer (`paid` = {real, bonus}). Returns the trade or None (the lot changed meanwhile — the caller gives the money
    back)."""
    from pymongo import ReturnDocument
    after = await _db.market_listings.find_one_and_update(
        {"id": lot["id"], "status": {"$in": ["active", "matching"]}, "amount": {"$gte": units}}, {"$inc": {"amount": -units}},
        return_document=ReturnDocument.AFTER)
    if not after:
        return None
    total_ton = cents_to_ton(price_c * units)
    sale_lot = {**lot, "price_per_unit": cents_to_ton(price_c), "_buy_order_id": buy_order_id}
    buyer_filter = {"id": buyer["id"]}
    upd = {"ok": True, "from_real": paid.get("real", 0.0), "from_bonus": paid.get("bonus", 0.0)}
    settled = await _D["settle"](sale_lot, buyer, buyer["id"], buyer_filter, int(units), total_ton, upd, None,
                                 buyer_wallet=buyer.get("wallet_address"), listing_id=lot["id"])
    if after.get("amount", 0) <= 0:
        await _db.market_listings.update_one({"id": lot["id"], "amount": {"$lte": 0}, "status": {"$in": ["active", "matching"]}},
                                             {"$set": {"status": "sold", "sold_at": _iso()}})
    elif after.get("price_per_unit") is not None:
        await _db.market_listings.update_one({"id": lot["id"]}, {"$set": {"total_price": round(int(after["amount"]) * float(after["price_per_unit"]), 9)}})
    return {"units": int(units), "price_cents": price_c, "total_cents": price_c * int(units), "seller_id": lot.get("seller_id"),
            "tax_ton": settled.get("seller_tax"), "lot_id": lot["id"]}


# ───────────────────────────── placing orders ─────────────────────────────
class OrderIn(BaseModel):
    resource_id: str
    side: str = Field(pattern="^(buy|sell)$")
    order_type: str = Field("limit", pattern="^(limit|market)$")
    amount: int = Field(gt=0)
    price: Optional[str] = None            # $CITY per unit, «12.34» (limit orders)


class CancelIn(BaseModel):
    order_id: str


def _check_resource(resource: str) -> None:
    from business_config import RESOURCE_TYPES
    if resource not in RESOURCE_TYPES or resource.endswith("_tutorial"):
        raise HTTPException(status_code=400, detail="unknown_resource")


async def _owns_real_business(user: Dict[str, Any]) -> bool:
    keys = {user.get("id"), user.get("wallet_address"), user.get("email")}
    keys.discard(None)
    if not keys:
        return False
    return await _db.businesses.count_documents({**_D["businesses_query"](keys), "is_trial": {"$ne": True}, "tutorial": {"$ne": True}}) > 0


async def _room_units(user: Dict[str, Any], resource: str, exclude_order: Optional[str] = None) -> int:
    """How many units of `resource` still fit in the player's warehouses: the free room minus what his waiting buy
    orders will bring (each order may be filled any time), whatever the price. `exclude_order`: the order being
    filled right now (its own units are what the room is checked for)."""
    from business_config import get_warehouse_weight
    w = max(1, int(get_warehouse_weight(resource) or 1))
    pending = 0
    async for o in _db.market_orders.find({"user_id": user["id"], "side": "buy", "status": "active"},
                                          {"_id": 0, "id": 1, "resource_id": 1, "remaining_amount": 1}):
        if exclude_order and o.get("id") == exclude_order:
            continue
        pending += max(1, int(get_warehouse_weight(o.get("resource_id")) or 1)) * int(o.get("remaining_amount") or 0)
    return max(0, (int(await _D["free_warehouse"](user)) - pending) // w)


async def place_buy(user: Dict[str, Any], data: OrderIn) -> Dict[str, Any]:
    res, units = data.resource_id, int(data.amount)
    if not await _owns_real_business(user):
        raise HTTPException(status_code=403, detail="no_business_to_buy")
    room = await _room_units(user, res)
    if units > room:
        raise HTTPException(status_code=400, detail=f"no_room:{room}")
    fills: List[Dict[str, Any]] = []
    async with _BookLock(res):
        if data.order_type == "market":
            left = units
            for lot in await _asks(res):
                if left <= 0:
                    break
                if lot.get("seller_id") == user["id"]:
                    continue
                price_c = lot_cents(lot)
                take = min(left, int(lot.get("amount") or 0))
                if take <= 0:
                    continue
                cost = cents_to_ton(price_c * take)
                me = await _db.users.find_one({"id": user["id"]}, {"_id": 0})
                avail = await _D["tat_live"](me)
                if avail + 1e-9 < cost:                         # what the money still covers at this price
                    take = int(Decimal(str(avail)) * CENTS_PER_TON // price_c) if price_c else 0
                    take = min(take, int(lot.get("amount") or 0))
                    if take <= 0:
                        break
                    cost = cents_to_ton(price_c * take)
                deb = await _D["debit"]({"id": user["id"]}, cost)
                if not deb.get("ok"):
                    break
                tr = await _fill(lot, me, take, price_c, {"real": deb.get("from_real", 0.0), "bonus": deb.get("from_bonus", 0.0)}, None)
                if not tr:
                    await _refund(user["id"], {"real": deb.get("from_real", 0.0), "bonus": deb.get("from_bonus", 0.0)})
                    continue
                fills.append(tr)
                left -= take
            if not fills:
                raise HTTPException(status_code=400, detail="nothing_to_buy")
            return _result(None, fills, units)
        # limit: freeze price × amount, take what crosses, the rest waits in the book
        if not data.price:
            raise HTTPException(status_code=400, detail="price_required")
        limit_c = to_cents(data.price)
        if limit_c <= 0:
            raise HTTPException(status_code=400, detail="bad_price")
        if await _db.market_orders.count_documents({"user_id": user["id"], "side": "buy", "status": "active"}) >= MAX_BUY_ORDERS:
            raise HTTPException(status_code=400, detail=f"buy_orders_limit:{MAX_BUY_ORDERS}")
        need = cents_to_ton(limit_c * units)
        me = await _db.users.find_one({"id": user["id"]}, {"_id": 0})
        if (await _D["tat_live"](me)) + 1e-9 < need:
            raise await _D["insufficient"](me, need)
        deb = await _D["debit"]({"id": user["id"]}, need)
        if not deb.get("ok"):
            raise await _D["insufficient"](me, need)
        order = {"id": str(uuid.uuid4()), "user_id": user["id"], "username": user.get("username") or "",
                 "resource_id": res, "side": "buy", "order_type": "limit", "price_cents": limit_c,
                 "price_per_item": cents_str(limit_c), "initial_amount": units, "remaining_amount": units,
                 "escrow_ton": round(need, 9), "escrow_bonus_ton": round(float(deb.get("from_bonus", 0.0)), 9),
                 "status": "active", "created_at": _iso()}
        await _db.market_orders.insert_one(dict(order))
        left = units
        for lot in await _asks(res):
            if left <= 0:
                break
            price_c = lot_cents(lot)
            if price_c > limit_c:
                break
            if lot.get("seller_id") == user["id"]:
                continue
            take = min(left, int(lot.get("amount") or 0))
            if take <= 0:
                continue
            part = await _take_escrow(order["id"], cents_to_ton(limit_c * take))
            if not part:
                break
            # the trade is at the lot's price: the difference to the buyer's limit goes back to him at once
            share = cents_to_ton(price_c * take) / cents_to_ton(limit_c * take) if limit_c else 1.0
            paid = {"real": round(part["real"] * share, 9), "bonus": round(part["bonus"] * share, 9)}
            back = {"real": round(part["real"] - paid["real"], 9), "bonus": round(part["bonus"] - paid["bonus"], 9)}
            me = await _db.users.find_one({"id": user["id"]}, {"_id": 0})
            tr = await _fill(lot, me, take, price_c, paid, order["id"])
            if not tr:
                await _db.market_orders.update_one({"id": order["id"]}, {"$inc": {"escrow_ton": part["real"] + part["bonus"],
                                                                               "escrow_bonus_ton": part["bonus"]}})
                continue
            await _refund(user["id"], back)
            await _db.market_orders.update_one({"id": order["id"]}, {"$inc": {"remaining_amount": -take}})
            fills.append(tr)
            left -= take
        if left <= 0:
            await _close_buy(order["id"], "filled")
        return _result(order["id"], fills, units, rest=left)


async def _close_buy(order_id: str, status: str) -> None:
    """Close a buy order and give back whatever money is still frozen in it."""
    from pymongo import ReturnDocument
    o = await _db.market_orders.find_one_and_update({"id": order_id, "status": "active"},
                                                    {"$set": {"status": status, "closed_at": _iso()}},
                                                    return_document=ReturnDocument.BEFORE)
    if not o:
        return
    esc, bon = float(o.get("escrow_ton") or 0), float(o.get("escrow_bonus_ton") or 0)
    if esc > 1e-12:
        r = await _db.market_orders.update_one({"id": order_id, "escrow_ton": esc}, {"$set": {"escrow_ton": 0.0, "escrow_bonus_ton": 0.0}})
        if r.modified_count:
            await _refund(o["user_id"], {"real": max(0.0, esc - bon), "bonus": max(0.0, bon)})


async def place_sell(user: Dict[str, Any], current_user: Any, data: OrderIn) -> Dict[str, Any]:
    res, units = data.resource_id, int(data.amount)
    import zero_business as _zb
    keys = await _D["owner_keys"](user["id"])
    zero = await _zb.has_zero_business(_db, keys)
    fills: List[Dict[str, Any]] = []
    async with _BookLock(res):
        if data.order_type == "market":
            if not await _owns_real_business(user) and units > _D["no_business_cap"]:
                raise HTTPException(status_code=400, detail=f"no_business_cap:{_D['no_business_cap']}")
            r = await _db.users.update_one({"id": user["id"], f"resources.{res}": {"$gte": units}}, {"$inc": {f"resources.{res}": -units}})
            if not r.modified_count:
                raise HTTPException(status_code=400, detail="not_enough_resource")
            lot = {"id": f"mkt-{uuid.uuid4()}", "seller_id": user["id"], "seller_email": user.get("email"),
                   "seller_username": user.get("username") or "", "business_id": await _D["attribute_biz"](user["id"], res),
                   "resource_type": res, "amount": units, "initial_amount": units, "status": "active", "order_type": "market",
                   "side": "sell", "created_at": _iso(), "price_per_unit": 0.0, "price_cents": 0}
            # a market sell order is a lot only for the instant of the match, in the status «matching»: the book, the
            # City Market and the other buyers never see it; the shared settlement code works on it as on any lot
            lot["status"] = "matching"
            await _db.market_listings.insert_one(dict(lot))
            fills = await _match_lot_against_bids(lot, None, user)
            left = int((await _db.market_listings.find_one({"id": lot["id"]}, {"_id": 0, "amount": 1}) or {}).get("amount") or 0)
            if left > 0:                                         # the City's buy order in the book takes what it can
                fills += await _sell_to_city(lot, user, None)
                left = int((await _db.market_listings.find_one({"id": lot["id"]}, {"_id": 0, "amount": 1}) or {}).get("amount") or 0)
            if left > 0:                                         # nothing more to sell to: the rest goes home
                g = await _db.market_listings.update_one({"id": lot["id"], "status": "matching", "amount": left},
                                                         {"$set": {"status": "cancelled", "cancelled_at": _iso(), "amount": 0}})
                if g.modified_count:
                    await _db.users.update_one({"id": user["id"]}, {"$inc": {f"resources.{res}": left}})
            else:
                await _db.market_listings.update_one({"id": lot["id"]}, {"$set": {"status": "sold", "sold_at": _iso()}})
            if not fills:
                raise HTTPException(status_code=400, detail=f"city_skip:{lot['_city_skip']}" if lot.get("_city_skip") else "nothing_to_sell_to")
            return _result(lot["id"], fills, units, rest=0, extra={"city_skip": lot.get("_city_skip")})
        # limit: the lot goes up with every rule of a player's lot (slots, level 0 = system price, min lot…)
        if not data.price:
            raise HTTPException(status_code=400, detail="price_required")
        price_c = to_cents(data.price)
        if price_c <= 0:
            raise HTTPException(status_code=400, detail="bad_price")
        req = _D["listing_req"](resource_type=res, amount=units, price_per_unit=cents_to_ton(price_c))
        try:
            out = await _D["list_resource"](req, current_user)
        except HTTPException as e:                     # the lot rules speak Russian: give the app a code it translates
            import re as _re
            d = str(e.detail or "")
            m = _re.search(r"Лимит:\s*(\d+)", d)
            if m:
                raise HTTPException(status_code=400, detail=f"sell_slots:{m.group(1)}")
            m = _re.search(r"Доступно:\s*(\d+)", d)
            if m and "Недостаточно ресурсов" in d:
                raise HTTPException(status_code=400, detail=f"not_enough_resource:{m.group(1)}")
            raise
        lot = out["listing"]
        real_c = ton_to_cents(float(lot["price_per_unit"]))          # level 0: the system price replaced the typed one
        await _db.market_listings.update_one({"id": lot["id"]}, {"$set": {"initial_amount": units, "price_cents": real_c,
                                                                           "price_per_item": cents_str(real_c), "side": "sell",
                                                                           "order_type": "limit"}})
        lot.update({"initial_amount": units, "price_cents": real_c})
        fills = await _match_lot_against_bids(lot, real_c, user)
        left = int((await _db.market_listings.find_one({"id": lot["id"]}, {"_id": 0, "amount": 1}) or {}).get("amount") or 0)
        if left > 0:                                             # priced at or below the City's buy order: it buys now
            fills += await _sell_to_city(lot, user, real_c)
            left = int((await _db.market_listings.find_one({"id": lot["id"]}, {"_id": 0, "amount": 1}) or {}).get("amount") or 0)
        return _result(lot["id"], fills, units, rest=left, extra={"credit_estimate": out.get("credit_estimate"),
                                                                    "city_skip": lot.get("_city_skip")})


async def city_bid(user: Dict[str, Any], resource: str) -> Optional[Dict[str, Any]]:
    """The City Market's buy order for this player, as the book shows it: its price per unit and how many units it
    still buys today (market_maker.buy_quote). None — the City does not buy this resource from him now."""
    q = await _city_buy(user, resource)
    if not q or not q.get("on"):
        return None
    return {"price": cents_str(to_cents(q["price_city"])), "price_cents": to_cents(q["price_city"]),
            "amount": int(q.get("units_left") or 0), "price_ton": float(q["price_ton"])}


async def _sell_to_city(lot: Dict[str, Any], seller: Dict[str, Any], limit_c: Optional[int]) -> List[Dict[str, Any]]:
    """A sell order meets the City's buy order (after the players' ones): a market order, or a limit order priced at or
    below the City's price, is bought now at the City's price (it was in the book first) — every rule of the City Market
    (daily volume, stock cap, budget, per-player caps) applies, nothing waits (market_maker.run_buy_side instant)."""
    apply_sale = _D.get("mm_apply_sale")
    cb = await city_bid(seller, lot["resource_type"])
    if not apply_sale or not cb or cb["amount"] <= 0 or (limit_c is not None and limit_c > cb["price_cents"]):
        return []
    import market_maker
    lid = lot["id"]
    before = await _db.market_listings.find_one({"id": lid}, {"_id": 0}) or {}
    n0 = int(before.get("amount") or 0)
    if n0 <= 0:
        return []
    # the City pays its own price: the lot is priced at it for the purchase, its own price comes back for the rest
    await _db.market_listings.update_one({"id": lid}, {"$set": {"price_per_unit": cb["price_ton"], "status": "active"}})
    try:
        await market_maker.run_buy_side(_db, apply_sale, only_listing=lid, instant=True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"spot: sale to the City failed for {lid}: {e}")
    after = await _db.market_listings.find_one({"id": lid}, {"_id": 0}) or {}
    n1 = int(after.get("amount") or 0) if after.get("status") == "active" else 0
    if n1 >= n0 and after.get("status") == "active":
        # nothing bought although the price was the City's: say why (the admin can see it in the logs too)
        try:
            d = await market_maker.run_buy_side(_db, None, dry=True, only_listing=lid, instant=True)
            why = next((x.get("detail") for x in d.get("decisions") or [] if x.get("decision") == "skip"), None)
            logger.warning(f"spot: the City did not buy {lid} ({lot.get('resource_type')}): {why or d.get('skipped')}")
            lot["_city_skip"] = why
        except Exception:  # noqa: BLE001
            pass
    if after.get("status") == "active":
        back = {"price_per_unit": before.get("price_per_unit"), "status": before.get("status") or "active"}
        if before.get("price_per_unit") is not None:
            back["total_price"] = round(n1 * float(before.get("price_per_unit") or 0), 9)
        await _db.market_listings.update_one({"id": lid}, {"$set": back})
    sold = max(0, n0 - n1)
    if not sold:
        return []
    return [{"units": sold, "price_cents": cb["price_cents"], "total_cents": cb["price_cents"] * sold, "seller_id": seller["id"],
             "buyer_id": "CITY_MARKET"}]


async def _match_lot_against_bids(lot: Dict[str, Any], limit_c: Optional[int], seller: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A new sell order meets the waiting buy orders: the highest price first, equal prices — the older first.
    The trade is at the buy order's price (it was in the book first); its frozen money pays."""
    fills = []
    for bid in await _bids(lot["resource_type"]):
        cur = await _db.market_listings.find_one({"id": lot["id"], "status": {"$in": ["active", "matching"]}}, {"_id": 0, "amount": 1})
        left = int((cur or {}).get("amount") or 0)
        if left <= 0:
            break
        bp = int(bid["price_cents"])
        if limit_c is not None and bp < limit_c:
            break
        if bid.get("user_id") == seller["id"]:
            continue
        buyer = await _db.users.find_one({"id": bid["user_id"]}, {"_id": 0})
        if not buyer:
            continue
        room = await _room_units(buyer, lot["resource_type"], exclude_order=bid["id"])
        want = min(left, int(bid.get("remaining_amount") or 0))
        take = min(want, room)
        if take <= 0:
            # the buyer has no room left: his order cannot be filled — it is closed, the money goes back
            await _close_buy(bid["id"], "cancelled_no_room")
            await _notify_no_room(buyer, bid)
            continue
        r = await _db.market_orders.update_one({"id": bid["id"], "status": "active", "remaining_amount": {"$gte": take}},
                                               {"$inc": {"remaining_amount": -take}})
        if not r.modified_count:
            continue
        part = await _take_escrow(bid["id"], cents_to_ton(bp * take))
        if not part:
            await _db.market_orders.update_one({"id": bid["id"]}, {"$inc": {"remaining_amount": take}})
            continue
        tr = await _fill(lot, buyer, take, bp, part, bid["id"])
        if not tr:
            await _db.market_orders.update_one({"id": bid["id"]}, {"$inc": {"remaining_amount": take, "escrow_ton": part["real"] + part["bonus"],
                                                                         "escrow_bonus_ton": part["bonus"]}})
            break
        fills.append(tr)
        o = await _db.market_orders.find_one({"id": bid["id"]}, {"_id": 0, "remaining_amount": 1})
        if int((o or {}).get("remaining_amount") or 0) <= 0:
            await _close_buy(bid["id"], "filled")
        if take < want:                                          # filled what fitted; the rest of the order is closed
            await _close_buy(bid["id"], "cancelled_no_room")
            await _notify_no_room(buyer, bid)
    return fills


async def _notify_no_room(buyer: Dict[str, Any], bid: Dict[str, Any]) -> None:
    try:
        from core.notif_i18n import user_lang
        lang = user_lang(buyer)
        T = {"ru": ("Ордер на покупку закрыт", "На складе нет места для «{r}» — остаток ордера снят, деньги вернулись на баланс."),
             "en": ("Buy order closed", "No room in the warehouse for «{r}» — the rest of the order was removed, the money is back.")}
        t, m = T.get(lang, T["en"])
        from business_config import RESOURCE_TYPES
        name = (RESOURCE_TYPES.get(bid.get("resource_id")) or {}).get("name_ru" if lang == "ru" else "name_en") or bid.get("resource_id")
        await _db.notifications.insert_one({"id": str(uuid.uuid4()), "user_id": buyer["id"], "type": "market_order",
                                            "title": t, "message": m.format(r=name), "read": False, "created_at": _iso(),
                                            "payload": {"open_path": "/trading?tab=spot"}})
    except Exception as e:  # noqa: BLE001
        logger.debug(f"no-room notice: {e}")


def _result(order_id: Optional[str], fills: List[Dict[str, Any]], units: int, rest: int = 0, extra: Optional[Dict] = None) -> Dict[str, Any]:
    done = sum(f["units"] for f in fills)
    total = sum(f["total_cents"] for f in fills)
    out = {"order_id": order_id, "filled": done, "rest": max(0, int(rest)), "requested": units,
           "avg_price": cents_str(int(Decimal(total) / done)) if done else None, "total": cents_str(total),
           "status": "filled" if done >= units else ("partial" if done else "open"), "fills": len(fills)}
    if extra:
        out.update(extra)
    return out


async def cancel(user: Dict[str, Any], current_user: Any, order_id: str) -> Dict[str, Any]:
    o = await _db.market_orders.find_one({"id": order_id}, {"_id": 0})
    if o:
        if o.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="not_your_order")
        if o.get("status") != "active":
            raise HTTPException(status_code=409, detail="order_closed")
        async with _BookLock(o["resource_id"]):
            await _close_buy(order_id, "cancelled")
        return {"status": "cancelled", "order_id": order_id, "side": "buy"}
    lot = await _db.market_listings.find_one({"id": order_id}, {"_id": 0, "resource_type": 1})
    if not lot:
        raise HTTPException(status_code=404, detail="order_not_found")
    async with _BookLock(lot["resource_type"]):
        r = await _D["cancel_listing"](order_id, current_user)
    return {**r, "order_id": order_id, "side": "sell"}


async def _city_buy(me: Dict[str, Any], resource: str) -> Optional[Dict[str, Any]]:
    try:
        import market_maker
        return await market_maker.buy_quote(_db, me, resource)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"spot city buy quote: {e}")
        return None


async def info(user: Dict[str, Any], resource: str) -> Dict[str, Any]:
    """What the order form needs: money and units available, room, tax, level-0 rules, limits."""
    from business_config import RESOURCE_TYPES, get_warehouse_weight
    import market_maker
    import zero_business as _zb
    me = await _db.users.find_one({"id": user["id"]}, {"_id": 0}) or {}
    keys = await _D["owner_keys"](user["id"])
    zero = await _zb.has_zero_business(_db, keys)
    tier = int((RESOURCE_TYPES.get(resource) or {}).get("tier", 1) or 1)
    tax = await _D["tax_rate"](user["id"], tier)
    sys_c = ton_to_cents(await _D["system_price"](resource)) if zero else None
    return {"resource_id": resource, "tier": tier, "available_city": round(float(await _D["tat_live"](me)) * CITY_PER_TON, 2),
            "have": int(float((me.get("resources") or {}).get(resource, 0) or 0)), "room_units": await _room_units(me, resource),
            "weight": int(get_warehouse_weight(resource) or 1), "can_buy": await _owns_real_business(me),
            "tax_rate": tax, "zero_seller": zero, "system_price": cents_str(sys_c) if sys_c else None,
            "min_lot": market_maker.TIER1_MIN_LOT if market_maker.is_tier1(resource) else 1,
            "city_buy": await _city_buy(me, resource), "city_bid": await city_bid(me, resource),
            "buy_orders": {"used": await _db.market_orders.count_documents({"user_id": user["id"], "side": "buy", "status": "active"}),
                           "max": MAX_BUY_ORDERS}}


async def my_trades(user: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    uid = user["id"]
    rows = await _db.trade_history.find({"$or": [{"buyer_id": uid}, {"seller_id": uid}]}, {"_id": 0}).sort("executed_at", -1).limit(limit).to_list(limit)
    for r in rows:
        r["side"] = "buy" if r.get("buyer_id") == uid else "sell"
    return rows


async def tickers() -> Dict[str, Any]:
    """Last price and 24-h change of every resource that traded (for the resource picker)."""
    out: Dict[str, Any] = {}
    since = _iso(_now() - timedelta(hours=24))
    async for t in _db.trade_history.find({}, {"_id": 0, "resource_id": 1, "price_cents": 1, "executed_at": 1}).sort("executed_at", -1).limit(3000):
        r = t["resource_id"]
        cur = out.setdefault(r, {"last": t["price_cents"], "first24": None, "vol24": 0})
        if t["executed_at"] >= since:
            cur["first24"] = t["price_cents"]
    return {r: {"last": cents_str(v["last"]), "change_24h": round((v["last"] - v["first24"]) / v["first24"] * 100, 2) if v["first24"] else None}
            for r, v in out.items()}


async def ensure_indexes(db) -> None:
    try:
        await db.market_orders.create_index([("resource_id", 1), ("side", 1), ("status", 1), ("price_cents", -1), ("created_at", 1)])
        await db.market_orders.create_index([("user_id", 1), ("status", 1)])
        await db.trade_history.create_index([("resource_id", 1), ("executed_at", -1)])
        await db.trade_history.create_index([("buyer_id", 1), ("executed_at", -1)])
        await db.trade_history.create_index([("seller_id", 1), ("executed_at", -1)])
    except Exception as e:  # noqa: BLE001
        logger.debug(f"spot indexes: {e}")


def create_router(get_current_user) -> APIRouter:
    r = APIRouter(prefix="/market", tags=["spot"])

    async def _me(cu) -> Dict[str, Any]:
        u = await _db.users.find_one({"id": cu.id}, {"_id": 0})
        if not u:
            raise HTTPException(status_code=404, detail="user_not_found")
        return u

    @r.post("/order")
    async def post_order(data: OrderIn, current_user=Depends(get_current_user)):
        _check_resource(data.resource_id)
        me = await _me(current_user)
        if data.side == "buy":
            return await place_buy(me, data)
        return await place_sell(me, current_user, data)

    @r.post("/cancel")
    async def post_cancel(data: CancelIn, current_user=Depends(get_current_user)):
        return await cancel(await _me(current_user), current_user, data.order_id)

    @r.get("/book/{resource_id}")
    async def get_book(resource_id: str, step: str = "0.01", depth: int = 20):
        _check_resource(resource_id)
        return await book(resource_id, step, max(1, min(60, int(depth))))

    @r.get("/my-orders/{user_id}")
    async def get_my_orders(user_id: str, current_user=Depends(get_current_user)):
        me = await _me(current_user)
        if user_id not in ("me", me["id"]) and not me.get("is_admin"):
            raise HTTPException(status_code=403, detail="not_your_orders")
        target = me if user_id in ("me", me["id"]) else (await _db.users.find_one({"id": user_id}, {"_id": 0}) or {"id": user_id})
        return {"orders": await my_orders(target)}

    @r.get("/my-trades")
    async def get_my_trades(limit: int = 50, current_user=Depends(get_current_user)):
        return {"trades": await my_trades(await _me(current_user), max(1, min(200, int(limit))))}

    @r.get("/spot-info/{resource_id}")
    async def get_info(resource_id: str, current_user=Depends(get_current_user)):
        _check_resource(resource_id)
        return await info(await _me(current_user), resource_id)

    @r.get("/tickers")
    async def get_tickers():
        return {"tickers": await tickers()}

    return r
