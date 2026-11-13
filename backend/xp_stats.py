"""Admin «XP игроков»: how much XP the players collect per day / week / month — and the most.

Source: City Pass progress (`city_pass_progress.daily.<YYYY-MM-DD>` — the MSK game day), written by city_pass.add_xp:
    daily.<day>.xp      every XP of that day (quests, sales, daily bonus, games …)
    daily.<day>.arcade  the XP of the games
A player may have progress documents of several seasons: the days are summed over them (a day belongs to one season).

GET /api/admin/xp-stats?period=day|yesterday|week|month&source=all|games
    period  day = today (MSK), yesterday, week = the last 7 days, month = the last 30 days (today included)
    → {period, days, source, players, total, avg, median, max: {user_id, username, xp}, top: [...20],
       series: [{day, total, players, max}], per_player_day: {avg, max}}
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

MSK = timezone(timedelta(hours=3))
PERIODS = {"day": (0, 1), "yesterday": (1, 1), "week": (0, 7), "month": (0, 30)}


def _days(period: str, today=None) -> List[str]:
    back, n = PERIODS[period]
    today = today or datetime.now(timezone.utc).astimezone(MSK).date()
    last = today - timedelta(days=back)
    return [(last - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


async def xp_stats(db, period: str = "day", source: str = "all", today=None) -> Dict[str, Any]:
    if period not in PERIODS:
        raise HTTPException(status_code=400, detail="period: day | yesterday | week | month")
    field = "arcade" if source == "games" else "xp"
    days = _days(period, today)
    proj = {"_id": 0, "user_id": 1, **{f"daily.{d}.{field}": 1 for d in days}}
    per_user: Dict[str, int] = {}
    per_day: Dict[str, Dict[str, int]] = {d: {} for d in days}
    async for p in db.city_pass_progress.find({"user_id": {"$nin": [None, ""]}}, proj):
        uid = p["user_id"]
        daily = p.get("daily") or {}
        for d in days:
            v = int(((daily.get(d) or {}).get(field)) or 0)
            if v > 0:
                per_user[uid] = per_user.get(uid, 0) + v
                per_day[d][uid] = per_day[d].get(uid, 0) + v
    vals = sorted(per_user.values())
    top_ids = sorted(per_user, key=lambda u: -per_user[u])[:20]
    names: Dict[str, str] = {}
    if top_ids:
        async for u in db.users.find({"id": {"$in": top_ids}}, {"_id": 0, "id": 1, "username": 1, "email": 1}):
            names[u["id"]] = u.get("username") or u.get("email") or u["id"]
    top = [{"user_id": u, "username": names.get(u, u), "xp": per_user[u]} for u in top_ids]
    series = [{"day": d, "total": sum(per_day[d].values()), "players": len(per_day[d]),
               "max": max(per_day[d].values()) if per_day[d] else 0} for d in days]
    day_vals = [v for d in days for v in per_day[d].values()]
    return {
        "period": period, "days": days, "source": source, "players": len(vals), "total": sum(vals),
        "avg": round(sum(vals) / len(vals), 1) if vals else 0,
        "median": statistics.median(vals) if vals else 0,
        "max": top[0] if top else None, "top": top, "series": series,
        # one player in ONE day (the best day of the period)
        "per_player_day": {"avg": round(sum(day_vals) / len(day_vals), 1) if day_vals else 0,
                           "max": max(day_vals) if day_vals else 0},
    }


def create_xp_stats_router(db, get_current_admin) -> APIRouter:
    r = APIRouter()

    @r.get("/api/admin/xp-stats")
    async def get_stats(period: str = "day", source: str = "all", _=Depends(get_current_admin)):
        return await xp_stats(db, period, "games" if source == "games" else "all")

    return r
