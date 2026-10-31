"""GRAM City — market analytics («Аналитика») + production chain.

Journal `market_trades` — one entry per resource deal, written at the moment of the deal:
    {id, resource, tier, units, total_city, price_city (per unit), source, buyer_id, buyer_name,
     seller_id, seller_name, linked, ref, ts, hour}
    source:  p2p        — player ↔ player on the market (an admin buyout is shown the same way, under its nickname)
             city_sell  — a player bought a lot of the City Market (the state sells)
             city_buy   — the City Market bought a player's lot (the state buys)
             tender     — a daily tender delivery
             supply     — supply-contract deliveries (one entry per contract per hour, summed)
    linked:  buyer and seller share a device (one person with two accounts) — such deals are listed in the
             history but NOT counted in volumes, prices and trends, so trends cannot be pumped by self-trading.
The first start fills the journal from the old transactions (market purchases and tender deliveries).

Endpoints (players):
    GET /api/analytics/overview?period=24h|7d|30d   — every resource: volume, deals, average / last price,
        price change vs the previous period, open listings (supply), demand ratio, state price, producers;
        trends (rising / falling / most demanded) and totals.
    GET /api/analytics/resource/{id}?period=…       — price & volume series, last deals with nicknames,
        current listings by price level, state price, who produces / consumes it.
    GET /api/economy/chain                           — production chain (what makes what) from the per-level consumption the economy tick uses.
Prices are in $CITY (1 TON = 1000 $CITY). Results are cached for 60 s.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

CITY_MARKET_ID = "CITY_MARKET"
PERIODS = {"24h": (timedelta(hours=24), 3600), "7d": (timedelta(days=7), 6 * 3600), "30d": (timedelta(days=30), 86400)}
_cache: Dict[str, Any] = {}
TTL = 60.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat()


def _parse(s: Any) -> Optional[datetime]:
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _res_cfg() -> Dict[str, Dict[str, Any]]:
    from business_config import RESOURCE_TYPES
    return {k: v for k, v in RESOURCE_TYPES.items() if not k.endswith("_tutorial")}


def _tier(resource: str) -> int:
    return int((_res_cfg().get(resource) or {}).get("tier", 1) or 1)


async def _linked(db, a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b or a == b or CITY_MARKET_ID in (a, b):
        return False
    try:
        import market_maker
        cache: Dict[str, str] = {}
        return (await market_maker.device_group(db, a, cache)) == (await market_maker.device_group(db, b, cache))
    except Exception:
        return False


async def record_trade(db, *, resource: str, units: float, total_ton: float, source: str,
                       buyer_id: Optional[str] = None, buyer_name: str = "", seller_id: Optional[str] = None,
                       seller_name: str = "", ref: Optional[str] = None, ts: Optional[datetime] = None) -> None:
    """One deal. Never breaks the caller."""
    try:
        units = float(units or 0)
        total_city = round(float(total_ton or 0) * 1000.0, 4)
        if units <= 0 or total_city <= 0 or not resource or resource.endswith("_tutorial"):
            return
        ts = ts or _now()
        await db.market_trades.insert_one({
            "id": str(uuid.uuid4()), "resource": resource, "tier": _tier(resource), "units": units,
            "total_city": total_city, "price_city": round(total_city / units, 6), "source": source,
            "buyer_id": buyer_id, "buyer_name": buyer_name or "", "seller_id": seller_id, "seller_name": seller_name or "",
            "linked": await _linked(db, buyer_id, seller_id), "ref": ref,
            "ts": _iso(ts), "hour": _iso(ts.replace(minute=0, second=0, microsecond=0)),
        })
    except Exception as e:
        logger.warning(f"market_trades record {resource}: {e}")


async def record_supply(db, *, contract_id: str, resource: str, units: float, total_city: float,
                        buyer_id: Optional[str], seller_id: Optional[str], buyer_name: str = "", seller_name: str = "") -> None:
    """Supply contracts deliver every minute — summed into one entry per contract per hour."""
    try:
        if float(units or 0) <= 0 or float(total_city or 0) <= 0:
            return
        now = _now()
        hour = _iso(now.replace(minute=0, second=0, microsecond=0))
        key = f"supply-{contract_id}-{hour}"
        await db.market_trades.update_one(
            {"id": key},
            {"$inc": {"units": float(units), "total_city": float(total_city)},
             "$set": {"ts": _iso(now)},
             "$setOnInsert": {"id": key, "resource": resource, "tier": _tier(resource), "source": "supply",
                              "buyer_id": buyer_id, "buyer_name": buyer_name or "", "seller_id": seller_id,
                              "seller_name": seller_name or "", "linked": False, "ref": contract_id, "hour": hour}},
            upsert=True)
    except Exception as e:
        logger.warning(f"market_trades supply {resource}: {e}")


async def ensure_indexes(db) -> None:
    for keys in ([("ts", -1)], [("resource", 1), ("ts", -1)], [("id", 1)]):
        try:
            await db.market_trades.create_index(keys)
        except Exception as e:
            logger.warning(f"market_trades index {keys}: {e}")


async def backfill(db) -> int:
    """Once: fill the journal from the old transactions (market purchases + tender deliveries)."""
    flag = await db.game_settings.find_one({"type": "market_trades_backfill"}, {"_id": 0})
    if flag:
        return 0
    await db.game_settings.update_one({"type": "market_trades_backfill"},
                                      {"$set": {"type": "market_trades_backfill", "started_at": _iso(_now())}}, upsert=True)
    rows: List[Dict[str, Any]] = []
    txs = await db.transactions.find({"tx_type": "market_purchase", "resource_type": {"$exists": True}},
                                     {"_id": 0}).to_list(200000)
    ids = set()
    for t in txs:
        for k in ("buyer_id", "seller_id"):
            if t.get(k):
                ids.add(t[k])
    names = {u["id"]: u.get("username") or "" for u in
             await db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "username": 1}).to_list(len(ids) + 1)}
    for t in txs:
        res, units, tot = t.get("resource_type"), float(t.get("resource_amount") or 0), float(t.get("amount_ton") or 0)
        if not res or units <= 0 or tot <= 0:
            continue
        src = "city_buy" if t.get("is_city_market") else ("city_sell" if t.get("seller_id") == CITY_MARKET_ID else "p2p")
        bid, sid = t.get("buyer_id"), t.get("seller_id")
        ts = _parse(t.get("created_at")) or _now()
        rows.append({"id": f"bf-{t.get('id')}", "resource": res, "tier": _tier(res), "units": units,
                     "total_city": round(tot * 1000, 4), "price_city": round(tot * 1000 / units, 6), "source": src,
                     "buyer_id": bid, "buyer_name": t.get("buyer_username") or names.get(bid, ""),
                     "seller_id": sid, "seller_name": names.get(sid, ""), "linked": False, "ref": t.get("listing_id"),
                     "ts": _iso(ts), "hour": _iso(ts.replace(minute=0, second=0, microsecond=0))})
    tenders = await db.transactions.find({"type": "contract_payment_in", "gross_city": {"$exists": True},
                                          "resource_type": {"$exists": True}}, {"_id": 0}).to_list(200000)
    for t in tenders:
        res, units, gross = t.get("resource_type"), float(t.get("resource_amount") or 0), float(t.get("gross_city") or 0)
        if not res or units <= 0 or gross <= 0:
            continue
        ts = _parse(t.get("created_at")) or _now()
        rows.append({"id": f"bf-{t.get('id')}", "resource": res, "tier": _tier(res), "units": units,
                     "total_city": round(gross, 4), "price_city": round(gross / units, 6), "source": "tender",
                     "buyer_id": t.get("buyer_id"), "buyer_name": t.get("buyer_username") or "",
                     "seller_id": t.get("seller_id"), "seller_name": t.get("seller_username") or "", "linked": False,
                     "ref": t.get("contract_id"), "ts": _iso(ts), "hour": _iso(ts.replace(minute=0, second=0, microsecond=0))})
    for i in range(0, len(rows), 1000):
        try:
            await db.market_trades.insert_many(rows[i:i + 1000], ordered=False)
        except Exception as e:
            logger.warning(f"market_trades backfill batch: {e}")
    await db.game_settings.update_one({"type": "market_trades_backfill"}, {"$set": {"done_at": _iso(_now()), "rows": len(rows)}})
    logger.info(f"market_trades backfill: {len(rows)} deals")
    return len(rows)


# ───────────────────────────── reports ─────────────────────────────
def _chain() -> Dict[str, Any]:
    """What every business really consumes — the per-level consumption the economy tick uses
    (business_config.get_consumption_breakdown), not the legacy `consumes` ratios. Values = units/day at level 1."""
    from business_config import BUSINESSES, get_consumption_breakdown
    res = _res_cfg()
    biz = []
    for code, b in BUSINESSES.items():
        if not b.get("produces"):
            continue
        cons: Dict[str, float] = {}
        for lvl in range(0, 11):
            for r, v in (get_consumption_breakdown(code, lvl) or {}).items():
                cons.setdefault(r, v)
        lvl1 = get_consumption_breakdown(code, 1) or {}
        cons = {r: lvl1.get(r, v) for r, v in cons.items()}
        biz.append({"code": code, "tier": int(b.get("tier") or 1), "produces": b.get("produces"), "consumes": cons})
    return {"businesses": biz,
            "resources": {k: {"tier": int(v.get("tier") or 1), "icon": v.get("icon"), "base_city": v.get("base_price")} for k, v in res.items()}}


async def _state_prices(db) -> Dict[str, Dict[str, Any]]:
    try:
        import market_maker
        cfg = await market_maker.get_config(db)
        out = {}
        for rid in _res_cfg():
            buy, sell = market_maker.prices_city(cfg, rid)
            out[rid] = {"buy_city": buy, "sell_city": sell, "buys": rid in (cfg.get("buy_resources") or [])}
        return out
    except Exception as e:
        logger.debug(f"state prices: {e}")
        return {}


async def _listings(db) -> Dict[str, Dict[str, Any]]:
    rows = await db.market_listings.find({"status": "active", "tutorial": {"$ne": True}},
                                         {"_id": 0, "resource_type": 1, "amount": 1, "price_per_unit": 1}).to_list(20000)
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        o = out.setdefault(r.get("resource_type"), {"lots": 0, "units": 0.0, "min_city": None})
        o["lots"] += 1
        o["units"] += float(r.get("amount") or 0)
        p = float(r.get("price_per_unit") or 0) * 1000
        o["min_city"] = p if o["min_city"] is None else min(o["min_city"], p)
    return out


async def _producers(db) -> Dict[str, int]:
    from business_config import BUSINESSES
    out: Dict[str, int] = {}
    try:
        for code, b in BUSINESSES.items():
            if b.get("produces"):
                n = await db.businesses.count_documents({"business_type": code, "is_trial": {"$ne": True}})
                out[b["produces"]] = out.get(b["produces"], 0) + n
    except Exception:
        pass
    return out


def _agg(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    units = sum(float(r["units"]) for r in rows)
    total = sum(float(r["total_city"]) for r in rows)
    rows_sorted = sorted(rows, key=lambda r: r["ts"])
    return {"units": round(units, 2), "volume_city": round(total, 2), "deals": len(rows),
            "avg_city": round(total / units, 4) if units else None,
            "last_city": round(float(rows_sorted[-1]["total_city"]) / float(rows_sorted[-1]["units"]), 4) if rows_sorted else None}


async def overview(db, period: str = "24h") -> Dict[str, Any]:
    period = period if period in PERIODS else "24h"
    key = f"ov:{period}"
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL:
        return hit[1]
    span = PERIODS[period][0]
    now = _now()
    since, prev_since = now - span, now - 2 * span
    rows = await db.market_trades.find({"ts": {"$gte": _iso(prev_since)}, "linked": {"$ne": True}},
                                       {"_id": 0, "resource": 1, "units": 1, "total_city": 1, "ts": 1}).to_list(500000)
    cur: Dict[str, List[Dict[str, Any]]] = {}
    prev: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        (cur if r["ts"] >= _iso(since) else prev).setdefault(r["resource"], []).append(r)
    state, lst, prod = await _state_prices(db), await _listings(db), await _producers(db)
    out = []
    for rid, cfg in _res_cfg().items():
        a, b = _agg(cur.get(rid, [])), _agg(prev.get(rid, []))
        change = None
        if a["avg_city"] and b["avg_city"]:
            change = round((a["avg_city"] - b["avg_city"]) / b["avg_city"] * 100, 1)
        vol_change = None
        if b["volume_city"]:
            vol_change = round((a["volume_city"] - b["volume_city"]) / b["volume_city"] * 100, 1)
        supply = lst.get(rid, {"lots": 0, "units": 0.0, "min_city": None})
        demand = round(a["units"] / (a["units"] + supply["units"]) * 100, 1) if (a["units"] + supply["units"]) > 0 else None
        out.append({"resource": rid, "tier": int(cfg.get("tier") or 1), **a, "price_change_pct": change,
                    "volume_change_pct": vol_change, "prev_avg_city": b["avg_city"], "listed_units": round(supply["units"], 2),
                    "listed_lots": supply["lots"], "min_listed_city": supply["min_city"], "demand_pct": demand,
                    "state": state.get(rid), "base_city": cfg.get("base_price"), "producers": prod.get(rid, 0)})
    traded = [x for x in out if x["deals"]]
    data = {
        "period": period, "since": _iso(since), "resources": out,
        "totals": {"volume_city": round(sum(x["volume_city"] for x in out), 2), "deals": sum(x["deals"] for x in out),
                   "prev_volume_city": round(sum(float(r["total_city"]) for v in prev.values() for r in v), 2),
                   "listed_lots": sum(x["listed_lots"] for x in out)},
        "trends": {
            "rising": [x["resource"] for x in sorted([x for x in traded if (x["price_change_pct"] or 0) > 0], key=lambda x: -x["price_change_pct"])[:3]],
            "falling": [x["resource"] for x in sorted([x for x in traded if (x["price_change_pct"] or 0) < 0], key=lambda x: x["price_change_pct"])[:3]],
            "demand": [x["resource"] for x in sorted([x for x in traded if x["demand_pct"] is not None], key=lambda x: (-x["demand_pct"], -x["volume_city"]))[:3]],
            "volume": [x["resource"] for x in sorted(traded, key=lambda x: -x["volume_city"])[:3]],
        },
    }
    _cache[key] = (time.monotonic(), data)
    return data


async def resource_detail(db, resource: str, period: str = "7d") -> Dict[str, Any]:
    if resource not in _res_cfg():
        raise HTTPException(status_code=404, detail="unknown_resource")
    period = period if period in PERIODS else "7d"
    key = f"rd:{resource}:{period}"
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL:
        return hit[1]
    span, step = PERIODS[period]
    now = _now()
    since = now - span
    rows = await db.market_trades.find({"resource": resource, "ts": {"$gte": _iso(since)}}, {"_id": 0}).sort("ts", -1).to_list(100000)
    counted = [r for r in rows if not r.get("linked")]
    start = datetime.fromtimestamp((int(since.timestamp()) // step + 1) * step, tz=timezone.utc)
    buckets: Dict[int, List[Dict[str, Any]]] = {}
    for r in counted:
        d = _parse(r["ts"])
        if d:
            buckets.setdefault(int(d.timestamp()) // step * step, []).append(r)
    series = []
    t = start
    while t <= now:
        k = int(t.timestamp())
        b = buckets.get(k, [])
        units = sum(float(x["units"]) for x in b)
        total = sum(float(x["total_city"]) for x in b)
        prices = [float(x["total_city"]) / float(x["units"]) for x in b if float(x["units"]) > 0]
        series.append({"t": _iso(t), "units": round(units, 2), "volume_city": round(total, 2), "deals": len(b),
                       "avg_city": round(total / units, 4) if units else None,
                       "min_city": round(min(prices), 4) if prices else None, "max_city": round(max(prices), 4) if prices else None})
        t += timedelta(seconds=step)
    book: Dict[float, Dict[str, Any]] = {}
    for l in await db.market_listings.find({"status": "active", "tutorial": {"$ne": True}, "resource_type": resource},
                                           {"_id": 0, "amount": 1, "price_per_unit": 1}).to_list(5000):
        p = round(float(l.get("price_per_unit") or 0) * 1000, 4)
        o = book.setdefault(p, {"price_city": p, "units": 0.0, "lots": 0})
        o["units"] += float(l.get("amount") or 0)
        o["lots"] += 1
    ch = _chain()
    state = (await _state_prices(db)).get(resource)
    deals = [{k: r.get(k) for k in ("ts", "units", "price_city", "total_city", "source", "buyer_name", "seller_name", "linked")}
             for r in rows[:60]]
    data = {
        "resource": resource, "tier": _tier(resource), "period": period, "step_sec": step, "series": series,
        "summary": _agg(counted), "deals": deals, "book": sorted(book.values(), key=lambda x: x["price_city"])[:25],
        "state": state, "base_city": (_res_cfg().get(resource) or {}).get("base_price"),
        "producers": (await _producers(db)).get(resource, 0),
        "made_by": [b["code"] for b in ch["businesses"] if b["produces"] == resource],
        "used_by": [b["code"] for b in ch["businesses"] if resource in b["consumes"]],
    }
    _cache[key] = (time.monotonic(), data)
    return data


def create_analytics_router(db, get_current_user) -> APIRouter:
    r = APIRouter(tags=["analytics"])

    @r.get("/api/analytics/overview")
    async def a_overview(period: str = "24h", current_user=Depends(get_current_user)):
        return await overview(db, period)

    @r.get("/api/analytics/resource/{resource}")
    async def a_resource(resource: str, period: str = "7d", current_user=Depends(get_current_user)):
        return await resource_detail(db, resource, period)

    @r.get("/api/economy/chain")
    async def a_chain():
        return _chain()

    return r
