"""Daily spoilage of the goods in a player's warehouse (one rule; replaces the old 00:00 «−10 % of everything» decay and
the 00:30 «−50 % of the overflow» spoilage).

Once a day (21:00 MSK by default, admin «Порча склада»):
  • the goods that fit the warehouse lose `in_pct` (10 %),
  • the goods above its limit (the overflow) lose `over_pct` (20 %),
  • at least `min_units` (1) unit in total is lost per day when the warehouse is not empty.
Every resource in the warehouse loses the SAME share (loss / everything), so nothing is singled out; amounts may become
fractional (85.5 is shown as 85). The warehouse is measured as the player sees it («Склад X / Y»: tier 2 / 3 take more
space, resources put on the market take space too) — but lots on the market never spoil, only the warehouse goods do.
Not spoiled: tutorial rewards that can't be sold (`<res>_tutorial`) and players under a warehouse protection
(the comeback bonus / the «Склад не портится» booster: users.decay_protected_until).

The player is told in Telegram + in the app; the text is written once in Russian and translated by LibreTranslate into
the player's language — that translation is kept 30 minutes (the numbers change every day, it is never reused).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))
SETTINGS_TYPE = "warehouse_spoilage"
DEFAULTS = {"enabled": True, "in_pct": 10.0, "over_pct": 20.0, "min_units": 1.0, "hour_msk": 21, "minute_msk": 0}
TRANSLATION_TTL_MIN = 30


async def get_settings(db) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    try:
        doc = await db.game_settings.find_one({"type": SETTINGS_TYPE}, {"_id": 0}) or {}
        for k in DEFAULTS:
            if k in doc and doc[k] is not None:
                out[k] = doc[k]
    except Exception:
        pass
    return out


def plan(resources: Dict[str, Any], capacity: float, listed: float, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What spoils for one player (pure). None when nothing does.
    resources — users.resources; capacity — the whole warehouse; listed — the space taken by their active lots."""
    from business_config import get_warehouse_weight
    goods: Dict[str, float] = {}
    for res, v in (resources or {}).items():
        if str(res).endswith("_tutorial"):
            continue
        try:
            n = float(v or 0)
        except (TypeError, ValueError):
            continue
        if n > 0:
            goods[res] = n
    if not goods:
        return None
    weight = {r: float(get_warehouse_weight(r) or 1) for r in goods}
    used = sum(goods[r] * weight[r] for r in goods)                 # weighted space of the warehouse goods
    room = max(0.0, float(capacity) - float(listed))                 # what is left for them besides the lots
    within = min(used, room)
    over = max(0.0, used - room)
    loss_w = within * float(cfg["in_pct"]) / 100.0 + over * float(cfg["over_pct"]) / 100.0
    share = min(1.0, loss_w / used) if used > 0 else 0.0
    units = sum(goods.values())
    if units * share < float(cfg["min_units"]):                      # at least 1 unit a day in total
        share = min(1.0, float(cfg["min_units"]) / units)
    if share <= 0:
        return None
    dec = {r: round(goods[r] * share, 6) for r in goods}
    lost_units = sum(dec.values())
    # how the loss splits between the «normal» part and the overflow part (for the message)
    over_share = (over * float(cfg["over_pct"])) / (loss_w * 100.0) if loss_w > 0 else 0.0
    used_after = (used - sum(dec[r] * weight[r] for r in dec)) + float(listed)
    return {"dec": dec, "lost_units": lost_units, "lost_over": lost_units * over_share,
            "lost_in": lost_units * (1 - over_share), "overflow": over > 0,
            "used_after": used_after, "capacity": float(capacity)}


def _fmt(x: float) -> str:
    x = round(float(x), 1)
    return f"{x:g}"


def message_ru(p: Dict[str, Any], cfg: Dict[str, Any]) -> tuple:
    title = "📦 Склад: часть товаров испортилась"
    used, cap = int(p["used_after"]), int(p["capacity"])
    if p["overflow"]:
        body = (f"За сутки испортилось {_fmt(p['lost_units'])} ед. товаров: {_fmt(p['lost_in'])} ед. — обычная порча "
                f"(−{_fmt(cfg['in_pct'])}%), {_fmt(p['lost_over'])} ед. — из-за переполнения склада (−{_fmt(cfg['over_pct'])}% "
                f"с излишка).\nСейчас на складе {used} / {cap}. Продайте лишнее или расширьте склад.")
    else:
        body = (f"За сутки испортилось {_fmt(p['lost_units'])} ед. товаров (−{_fmt(cfg['in_pct'])}% в сутки).\n"
                f"Сейчас на складе {used} / {cap}. Продавайте товары, пока они не испортились.")
    return title, body


def _due(now_msk: datetime, cfg: Dict[str, Any]) -> bool:
    return (now_msk.hour, now_msk.minute) >= (int(cfg["hour_msk"]), int(cfg["minute_msk"]))


async def run(db, force: bool = False) -> Dict[str, Any]:
    """The daily pass. Called every few minutes by the scheduler: runs once a day at the configured MSK time."""
    cfg = await get_settings(db)
    if not cfg.get("enabled", True) and not force:
        return {"skipped": "disabled"}
    now = datetime.now(timezone.utc)
    day = now.astimezone(MSK).date().isoformat()
    if not force:
        if not _due(now.astimezone(MSK), cfg):
            return {"skipped": "not_yet"}
        # claim today's run (one leader, one run a day)
        r = await db.game_settings.update_one(
            {"type": "warehouse_spoilage_runs", "$or": [{"last_day": {"$ne": day}}, {"last_day": {"$exists": False}}]},
            {"$set": {"type": "warehouse_spoilage_runs", "last_day": day, "started_at": now.isoformat()}})
        if not getattr(r, "modified_count", 0):
            if await db.game_settings.find_one({"type": "warehouse_spoilage_runs"}, {"_id": 0, "last_day": 1}):
                return {"skipped": "done_today"}
            await db.game_settings.insert_one({"type": "warehouse_spoilage_runs", "last_day": day, "started_at": now.isoformat()})

    from core import warehouse as _wh
    try:
        from comeback import decay_protected
    except Exception:
        decay_protected = lambda _u: False  # noqa: E731
    from core.notify import notify_user
    stats = {"players": 0, "protected": 0, "units": 0.0}
    async for user in db.users.find({"resources": {"$exists": True}}, {"_id": 0}):
        uid = user.get("id")
        if not uid or not user.get("resources"):
            continue
        if decay_protected(user):
            stats["protected"] += 1
            continue
        try:
            businesses = await _wh.user_businesses(db, user)
            capacity = _wh.total_capacity(businesses, await _wh.buff_map_for(db, businesses))
            listed = await _wh.listed_used(db, user)
            p = plan(user.get("resources"), capacity, listed, cfg)
            if not p:
                continue
            # $inc of the loss (never $set of a map read a moment ago): production / purchases meanwhile are kept
            await db.users.update_one({"id": uid}, {"$inc": {f"resources.{r}": -v for r, v in p["dec"].items() if v > 0}})
            stats["players"] += 1
            stats["units"] += p["lost_units"]
            title, body = message_ru(p, cfg)
            await notify_user(db, user, title=title, message=body, type_key="warehouse_spoilage", priority="warning",
                              payload={"lost_units": round(p["lost_units"], 2), "open_path": "/trading"},
                              translation_ttl_min=TRANSLATION_TTL_MIN)
        except Exception as e:  # one player's failure never stops the pass
            logger.warning(f"warehouse spoilage failed for {uid}: {e}")
    try:
        await db.system_events.insert_one({"type": "warehouse_spoilage", "timestamp": now.isoformat(), **stats})
    except Exception:
        pass
    logger.info(f"📦 warehouse spoilage: {stats}")
    return stats


def create_admin_router(db, get_current_admin):
    from fastapi import APIRouter, Depends, HTTPException

    router = APIRouter(prefix="/api/admin/warehouse-spoilage", tags=["admin-warehouse"])

    @router.get("")
    async def get_(admin=Depends(get_current_admin)):
        last = await db.system_events.find({"type": "warehouse_spoilage"}, {"_id": 0}).sort("timestamp", -1).limit(1).to_list(1)
        return {**(await get_settings(db)), "last_run": last[0] if last else None}

    @router.put("")
    async def put_(body: Dict[str, Any], admin=Depends(get_current_admin)):
        patch = {k: body[k] for k in DEFAULTS if k in body}
        try:
            for k in ("in_pct", "over_pct"):
                if k in patch:
                    patch[k] = float(patch[k])
                    if not 0 <= patch[k] <= 100:
                        raise ValueError
            if "min_units" in patch:
                patch["min_units"] = max(0.0, float(patch["min_units"]))
            if "hour_msk" in patch:
                patch["hour_msk"] = int(patch["hour_msk"])
                if not 0 <= patch["hour_msk"] <= 23:
                    raise ValueError
            if "minute_msk" in patch:
                patch["minute_msk"] = int(patch["minute_msk"])
                if not 0 <= patch["minute_msk"] <= 59:
                    raise ValueError
            if "enabled" in patch:
                patch["enabled"] = bool(patch["enabled"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Проверьте значения: проценты 0–100, час 0–23, минуты 0–59")
        await db.game_settings.update_one({"type": SETTINGS_TYPE}, {"$set": {**patch, "type": SETTINGS_TYPE}}, upsert=True)
        return await get_settings(db)

    return router
