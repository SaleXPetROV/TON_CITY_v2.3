"""Presale gate — presale is the single source of truth for map purchases.

A plot on the map may be bought / staked (Level-0) ONLY when it belongs to the
currently ACTIVE presale allowlist (`selected_plots`). If there is no active
presale, or the active presale has no selected plots, or the plot is not in the
allowlist, the purchase is blocked everywhere and the admin's custom button text
is shown in place of the "Купить" button.

Admins bypass the gate so they can always test / manage the map.
"""


async def get_presale_doc(db):
    return await db.admin_settings.find_one({"type": "presale"}, {"_id": 0})


def presale_button_text(doc) -> str:
    """Global custom replacement text for the Buy button (stored as-is, no i18n).
    Empty string => frontend falls back to the default 'Купить' label."""
    return ((doc or {}).get("buy_button_text") or "").strip()


def _allowlist(doc, map_id):
    """Set of (x, y) coords buyable via the active presale for this map.
    Returns None when there is no active presale at all (=> block everywhere)."""
    if not doc or not doc.get("active"):
        return None
    if (doc.get("map_id") or "ton_island") != (map_id or "ton_island"):
        return set()
    return {(p.get("x"), p.get("y")) for p in (doc.get("selected_plots") or [])}


async def presale_allows(db, map_id, x, y, is_admin: bool = False):
    """Return (allowed: bool, button_text: str).

    Admins are always allowed. For everyone else the plot must be in the active
    presale allowlist. An empty / absent presale blocks all purchases."""
    doc = await get_presale_doc(db)
    btn = presale_button_text(doc)
    if is_admin:
        return True, btn
    allow = _allowlist(doc, map_id)
    if not allow:
        return False, btn
    return ((x, y) in allow), btn


async def _count_free_plots(db, map_id: str = "ton_island") -> int:
    from datetime import datetime, timezone
    doc = await get_presale_doc(db)
    if not doc or not doc.get("active") or (doc.get("map_id") or "ton_island") != map_id:
        return 0
    opens = doc.get("opens_at")
    if opens:
        try:
            dt = datetime.fromisoformat(str(opens).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < dt:
                return 0                                   # the countdown is still running: nothing can be taken yet
        except Exception:
            pass
    plots = doc.get("selected_plots") or []
    if not plots:
        return 0
    isl = await db.islands.find_one({"id": map_id}, {"_id": 0, "cells.x": 1, "cells.y": 1, "cells.district": 1,
                                                     "cells.zone": 1, "cells.pre_business": 1, "cells.is_empty": 1})
    cells = {(c.get("x"), c.get("y")): c for c in ((isl or {}).get("cells") or [])}
    sold = set()
    async for p in db.plots.find({"island_id": map_id, "owner": {"$type": "string"}}, {"_id": 0, "x": 1, "y": 1}):
        sold.add((p.get("x"), p.get("y")))
    sched = ((await db.admin_settings.find_one({"type": "trading_schedule"}, {"_id": 0}) or {}).get("zones") or {})
    from city_districts import district_unlocked
    now = datetime.now(timezone.utc)
    n = 0
    for p in plots:
        xy = (p.get("x"), p.get("y"))
        c = cells.get(xy)
        if xy in sold or (cells and not c):
            continue
        if c is not None:
            if c.get("is_empty") or not c.get("pre_business"):
                continue
            if p.get("business_type") and c.get("pre_business") != p.get("business_type"):
                continue                                   # chosen on an older layout of the map
            if not await district_unlocked(db, c):
                continue
            zo = sched.get(c.get("zone"))
            if zo:
                try:
                    zd = datetime.fromisoformat(str(zo).replace("Z", "+00:00"))
                    if (zd if zd.tzinfo else zd.replace(tzinfo=timezone.utc)) > now:
                        continue
                except Exception:
                    pass
        n += 1
    return n


async def free_plots_open(db, map_id: str = "ton_island") -> int:
    """How many plots of the active presale a newcomer can take right now (free level-0 business for 3 days):
    the same rules as /island/buy — active presale, countdown over, plot not owned, still the same business on the
    map, district not closed, zone trading open. Cached 15 s (the guide asks often)."""
    from core.ttl_cache import cached
    return await cached(f"presale:free_open:{map_id}:{id(db)}", 15, lambda: _count_free_plots(db, map_id), owner=db)
