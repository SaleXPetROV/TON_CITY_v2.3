"""Окупаемость при идеальных условиях.

Players asked to see how fast a business pays for itself. «Ideal conditions» are said out loud next to the number:
  • the business works round the clock — 3 shifts of 8 h a day, never idle, the warehouse never full;
  • durability stays at 50 % or more (full output, repair at the normal price);
  • every unit of raw material is bought and every unit of output is sold at today's market price (the price table
    the market and the admin use), the seller's sale tax of the output's tier is paid;
  • no buffs, no patron, no events.

A day = output × price × (1 − sale tax) − Σ raw material × price − repair of a day's wear.
Payback (days) = what the business cost / profit of a day. An upgrade: its cost / the extra profit of a day it adds.
Everything is in TON inside and goes out in $CITY as well (1 TON = 1000 $CITY)."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from business_config import (BUSINESS_KEY_MAP, BUSINESSES, RESOURCE_TYPES, UPGRADE_COSTS_TABLE, get_consumption_breakdown,
                             get_daily_wear, get_production, repair_cost_per_pct_city)

CITY = 1000.0
_TAX_DEFAULT = {1: 0.15, 2: 0.23, 3: 0.30}


def _mapped(btype: str) -> str:
    return BUSINESS_KEY_MAP.get(btype, btype)


async def market_prices_ton(db) -> Dict[str, float]:
    """Today's price of one unit of every resource, TON (the table the market uses; base prices if none)."""
    doc = await db.market_prices.find_one({"type": "current"}, {"_id": 0, "prices": 1})
    if not doc:
        doc = await db.admin_settings.find_one({"type": "market_prices"}, {"_id": 0, "prices": 1})
    stored = (doc or {}).get("prices") or {}
    out = {}
    for r, meta in RESOURCE_TYPES.items():
        base = float(meta.get("base_price", 0.01) or 0.01)
        try:
            v = float(stored.get(r, base) or base)
        except (TypeError, ValueError):
            v = base
        out[r] = v / CITY
    return out


async def sale_tax_rates(db) -> Dict[int, float]:
    t = await db.admin_settings.find_one({"type": "tax_settings"}, {"_id": 0}) or {}
    return {1: float(t.get("small_business_tax", 15)) / 100, 2: float(t.get("medium_business_tax", 23)) / 100,
            3: float(t.get("large_business_tax", 30)) / 100} if t else dict(_TAX_DEFAULT)


def ideal_day(btype: str, level: int, prices: Dict[str, float], taxes: Dict[int, float]) -> Dict[str, Any]:
    """One day of a business in ideal conditions (TON)."""
    m = _mapped(btype)
    cfg = BUSINESSES.get(m) or BUSINESSES.get(btype) or {}
    lvl = max(1, int(level or 1))
    out_res = cfg.get("produces")
    qty = float(get_production(m, lvl) or 0)
    out_tier = int((RESOURCE_TYPES.get(out_res) or {}).get("tier", cfg.get("tier", 1)) or 1)
    tax = float(taxes.get(out_tier, _TAX_DEFAULT.get(out_tier, 0.15)))
    price = float(prices.get(out_res, 0.0))
    gross = qty * price
    inputs = []
    raw = 0.0
    for r, q in (get_consumption_breakdown(m, lvl) or {}).items():
        q = float(q or 0)
        if q <= 0:
            continue
        t = q * float(prices.get(r, 0.0))
        raw += t
        inputs.append({"resource": r, "qty": q, "price_city": round(float(prices.get(r, 0.0)) * CITY, 2), "city": round(t * CITY, 2)})
    wear_pct = float(get_daily_wear(m, lvl) or 0) * 100.0                 # % of durability a day of 3 shifts wears
    per_pct = float(repair_cost_per_pct_city(m, cfg.get("tier", 1), lvl) or 0)
    repair = wear_pct * per_pct / CITY
    profit = gross * (1 - tax) - raw - repair
    return {"level": lvl, "resource": out_res, "qty": qty, "price_city": round(price * CITY, 2),
            "gross_city": round(gross * CITY, 2), "tax_rate": tax, "tax_city": round(gross * tax * CITY, 2),
            "inputs": inputs, "inputs_city": round(raw * CITY, 2),
            "repair_pct": round(wear_pct, 2), "repair_city": round(repair * CITY, 2),
            "profit_city": round(profit * CITY, 2)}


def _days(cost_ton: float, profit_city: float) -> Optional[float]:
    if cost_ton <= 0:
        return 0.0
    if profit_city <= 0:
        return None                                   # never pays back at today's prices
    return round(cost_ton * CITY / profit_city, 1)


def upgrade_cost_ton(btype: str, to_level: int, prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """$CITY + the resource (at today's price) of one upgrade step to `to_level` (2…10)."""
    m = _mapped(btype)
    costs = UPGRADE_COSTS_TABLE.get(m) or UPGRADE_COSTS_TABLE.get(btype) or {}
    step = costs.get(to_level) or costs.get(str(to_level))
    if not step:
        return None
    city = float(step.get("city") or 0)
    res, qty = step.get("resource"), float(step.get("qty") or 0)
    res_ton = qty * float(prices.get(res, 0.0)) if res else 0.0
    return {"city": city, "resource": res, "qty": qty, "resource_city": round(res_ton * CITY, 2),
            "total_ton": city / CITY + res_ton}


async def for_type(db, btype: str, level: int = 1, invest_ton: Optional[float] = None) -> Dict[str, Any]:
    """Payback of a business of this type and level bought for `invest_ton` (a lot on the map, a lot for sale),
    and of its next upgrade."""
    prices, taxes = await market_prices_ton(db), await sale_tax_rates(db)
    lvl = max(1, min(10, int(level or 1)))
    day = ideal_day(btype, lvl, prices, taxes)
    out = {"business_type": btype, "level": lvl, "day": day, "invest_city": None, "days": None,
           "conditions": "ideal"}
    if invest_ton is not None:
        out["invest_city"] = round(float(invest_ton) * CITY, 2)
        out["days"] = _days(float(invest_ton), day["profit_city"])
    if lvl < 10:
        up = upgrade_cost_ton(btype, lvl + 1, prices)
        if up:
            nxt = ideal_day(btype, lvl + 1, prices, taxes)
            extra = round(nxt["profit_city"] - day["profit_city"], 2)
            nx = {"level": lvl + 1, "cost_city": round(up["total_ton"] * CITY, 2), "city": up["city"],
                  "resource": up["resource"], "qty": up["qty"], "resource_city": up["resource_city"],
                  "profit_city": nxt["profit_city"], "extra_city": extra, "days": _days(up["total_ton"], extra), "mode": "extra"}
            if nx["days"] is None:
                # the next level does not add profit by itself (it uses more raw materials, e.g. a casino 1 → 2): its
                # payback is then the whole business on the new level — what it cost + the upgrade, against the
                # profit of a day on that level (the levels after it grow again)
                nx["days"] = _days(float(invest_ton or 0) + up["total_ton"], nxt["profit_city"])
                nx["mode"] = "full"
            out["next"] = nx
    return out


async def for_business(db, business: Dict[str, Any]) -> Dict[str, Any]:
    """My business: what it cost at its level (the fair price of the level: the map price of level 1 + every upgrade
    at today's prices) against its ideal day. A free level-0 business: the buyout to level 1 against level 1."""
    from core.seizure import seizure_price_breakdown
    btype = business.get("business_type")
    try:
        level = int(business.get("level", 1) or 0)
    except (TypeError, ValueError):
        level = 1
    if level <= 0 or business.get("is_zero_business"):
        bd = await seizure_price_breakdown(db, business, 1)
        out = await for_type(db, btype, 1, bd["level1_ton"])
        out["buyout"] = True
        # its next step is the buyout 0 → 1 itself (not 1 → 2): the cost of level 1, the profit of a level-1 day
        out["next"] = {"level": 1, "cost_city": out["invest_city"], "city": out["invest_city"], "resource": None, "qty": 0,
                       "resource_city": 0, "profit_city": out["day"]["profit_city"], "extra_city": out["day"]["profit_city"],
                       "days": out["days"], "mode": "buyout"}
        return out
    bd = await seizure_price_breakdown(db, business, level)
    out = await for_type(db, btype, level, bd["total"])
    out["buyout"] = False
    return out


def fmt_days(d: Optional[float]) -> str:
    if d is None:
        return "—"
    return f"{math.ceil(d)}"
