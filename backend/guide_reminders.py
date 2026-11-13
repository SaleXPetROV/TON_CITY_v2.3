"""The guide's reminders of the first days (after the guide). Sent through smart_notify (in-app + Telegram, the
player's language, quiet hours, the «Первые дни» switch in settings). At most 3 of them a day per player.

  • 20:30 MSK — the warehouse is more than half full: «Через 30 минут порча — продайте лишнее»
  • day 2, from 10:00 MSK — a level-0 business: «Сохраните бизнес навсегда: не хватает N $CITY»
  • 12:00 MSK — owners of level 1+ businesses below the activity rule (bought < 40 and sold < 100 in 10 days),
    at most every 3 days: «купите ещё N или продайте ещё M»
(24 h / 12 h / 2 h before a lease ends — zero_lease.py, ZERO_LEASE_WARN_THRESHOLDS.)

`tick(db)` is called every 10 minutes; each reminder runs once per MSK day (collection guide_reminder_runs).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)
MSK = timezone(timedelta(hours=3))
DAILY_CAP = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts):
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _once(db, day: str, kind: str) -> bool:
    """True the first time this reminder runs today."""
    r = await db.guide_reminder_runs.update_one({"day": day, "kind": kind}, {"$setOnInsert": {"at": _now().isoformat()}}, upsert=True)
    return bool(getattr(r, "upserted_id", None))


async def _slot(db, uid: str, day: str) -> bool:
    """Take one of the player's 3 guide reminders of the day."""
    r = await db.users.update_one({"id": uid, "guide_daily.day": day, "guide_daily.count": {"$lt": DAILY_CAP}},
                                  {"$inc": {"guide_daily.count": 1}})
    if r.modified_count:
        return True
    r = await db.users.update_one({"id": uid, "guide_daily.day": {"$ne": day}}, {"$set": {"guide_daily": {"day": day, "count": 1}}})
    return bool(r.modified_count)


async def _send(db, user: Dict[str, Any], kind: str, vars_: Dict[str, Any], day: str, ref: str) -> bool:
    import smart_notify
    if not await _slot(db, user["id"], day):
        return False
    await smart_notify.send(user, kind, vars_, ref=ref)
    return True


async def _owner_bizs(db, user):
    from core.helpers import resolve_owner_keys, owner_businesses_query
    keys = await resolve_owner_keys(db, user.get("id"))
    return await db.businesses.find({**owner_businesses_query(keys), "tutorial": {"$ne": True}, "is_seized": {"$ne": True}},
                                    {"_id": 0}).to_list(50)


async def spoil_warning(db, day: str) -> int:
    from core import warehouse as wh
    sent = 0
    async for u in db.users.find({"resources": {"$exists": True, "$ne": {}}, "is_blocked": {"$ne": True}}, {"_id": 0}).limit(20000):
        try:
            bizs = await _owner_bizs(db, u)
            if not bizs:
                continue
            cap = wh.total_capacity(bizs)
            used = wh.used_by_resources(u.get("resources"))
            if cap <= 0 or used / cap <= 0.5:
                continue
            units = int(sum(int(float(v or 0)) for k, v in (u.get("resources") or {}).items() if not str(k).endswith("_tutorial")) * 0.10)
            if units <= 0:
                continue
            if await _send(db, u, "guide_spoil", {"pct": int(round(used / cap * 100)), "units": units}, day, f"spoil:{day}"):
                sent += 1
        except Exception as e:
            logger.debug(f"guide spoil {u.get('id')}: {e}")
    return sent


async def keep_business(db, day: str) -> int:
    from business_config import BUSINESSES
    now = _now()
    sent = 0
    async for b in db.businesses.find({"is_zero_business": True, "level": 0, "is_seized": {"$ne": True}}, {"_id": 0}).limit(20000):
        created = _parse(b.get("created_at") or b.get("claimed_at"))
        if not created or not (timedelta(hours=16) <= now - created <= timedelta(hours=44)):
            continue                                      # «day 2»: the morning after the claim
        u = await db.users.find_one({"$or": [{"id": b.get("owner")}, {"wallet_address": b.get("owner")}]}, {"_id": 0})
        if not u:
            continue
        cfg = BUSINESSES.get(b.get("business_type")) or {}
        cost = round(float(b.get("zero_map_price") or cfg.get("base_cost_ton") or 0) * 1000, 2)
        need = max(0.0, cost - float(u.get("balance_ton") or 0) * 1000)
        name = (cfg.get("name") or {}).get(u.get("language") or "en") or (cfg.get("name") or {}).get("en") or b.get("business_type")
        exp = _parse(b.get("expires_at"))
        ends = exp.astimezone(MSK).strftime("%d.%m %H:%M") + " MSK" if exp else "—"
        if await _send(db, u, "guide_keep", {"name": name, "cost": f"{cost:,.0f}".replace(",", " "), "need": f"{need:,.0f}".replace(",", " "), "ends": ends}, day, f"keep:{b.get('id')}"):
            sent += 1
    return sent


async def activity_rule(db, day: str) -> int:
    import inactivity as ia
    active, buy_map, sell_map = await ia.compute_active_user_ids(db)
    now = _now()
    sent, seen = 0, set()
    async for b in db.businesses.find({"level": {"$gte": 1}, "is_seized": {"$ne": True}, "tutorial": {"$ne": True}}, {"_id": 0, "owner": 1}).limit(50000):
        ok = b.get("owner")
        if not ok or ok in seen:
            continue
        seen.add(ok)
        u = await db.users.find_one({"$or": [{"id": ok}, {"wallet_address": ok}]}, {"_id": 0})
        if not u or u.get("is_admin"):
            continue
        ids = {u.get(k) for k in ("id", "wallet_address", "email")} - {None, ""}
        if ids & active:
            continue
        last = _parse(u.get("guide_activity_warned_at"))
        if last and now - last < timedelta(days=3):
            continue
        bought = int(sum(buy_map.get(i, 0) for i in ids)); sold = int(sum(sell_map.get(i, 0) for i in ids))
        v = {"bought": bought, "bmin": ia.MARKET_BUY_MIN, "sold": sold, "smin": ia.MARKET_SELL_MIN,
             "bneed": max(0, ia.MARKET_BUY_MIN - bought), "sneed": max(0, ia.MARKET_SELL_MIN - sold)}
        if await _send(db, u, "guide_activity", v, day, f"activity:{day}"):
            await db.users.update_one({"id": u["id"]}, {"$set": {"guide_activity_warned_at": now.isoformat()}})
            sent += 1
    return sent


async def tick(db) -> Dict[str, int]:
    """Every 10 minutes: run whatever is due now (each once per MSK day)."""
    msk = _now().astimezone(MSK)
    day = msk.strftime("%Y-%m-%d")
    hm = msk.hour * 60 + msk.minute
    out: Dict[str, int] = {}
    if 20 * 60 + 30 <= hm < 20 * 60 + 55 and await _once(db, day, "spoil"):
        out["spoil"] = await spoil_warning(db, day)
    if 10 * 60 <= hm < 13 * 60 and await _once(db, day, "keep"):
        out["keep"] = await keep_business(db, day)
    if 12 * 60 <= hm < 15 * 60 and await _once(db, day, "activity"):
        out["activity"] = await activity_rule(db, day)
    if out:
        logger.info(f"guide reminders: {out}")
    return out
