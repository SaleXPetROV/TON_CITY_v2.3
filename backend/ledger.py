"""GRAM City — platform ledger: every amount the platform (admin) RECEIVES or PAYS OUT, one entry per event.

The admin «Доходы» tab is built from this journal (not from the old mixed counters in admin_stats.treasury):
how much and for what was received, per kind and per period, in TON (1 TON = 1000 $CITY).

Entry (collection `platform_ledger`):
    {id, kind, dir: "in" | "out", ton,          # the amount, TON (always > 0)
     real_ton,                                   # the part paid with REAL money (the rest = the player's bonus balance)
     user_id, ref, note, external,               # external = paid outside the game (a Founder Pass deal added by the admin)
     day (MSK), created_at}

Rules
  • «in»  — money that ends up with the platform: lot sales, building, upgrades, repairs, sale taxes, fees, …
  • «out» — money the platform pays to players in REAL balance: Founder Pass payouts, referral rewards paid by the
    platform, resources the state buys, credits issued, …  (rewards to the BONUS balance are not money and are
    not listed as expenses; they appear in the «paid with bonus» part of the incomes when spent.)
  • A payment split bonus + real: `ton` is the full amount, `real_ton` the real part — the admin sees both.
Recording never breaks the caller (errors are logged).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# kind → (direction, Russian label for the admin, group)
KINDS: Dict[str, tuple] = {
    # ── incomes ──
    "land_sale":            ("in", "Продажа участков с бизнесом (город)", "Земля и бизнесы"),
    "business_build":       ("in", "Постройка бизнесов", "Земля и бизнесы"),
    "zero_business":        ("in", "Выкуп бизнесов уровня 0 (аренда-застолбление)", "Земля и бизнесы"),
    "business_upgrade":     ("in", "Улучшение бизнесов", "Земля и бизнесы"),
    "repair":               ("in", "Ремонт бизнесов", "Земля и бизнесы"),
    "demolish":             ("in", "Снос бизнесов", "Земля и бизнесы"),
    "seized_business":      ("in", "Продажа изъятых бизнесов (доля государства)", "Земля и бизнесы"),
    "land_market_tax":      ("in", "Налог с продажи бизнесов между игроками", "Налоги и комиссии"),
    "resale_tax":           ("in", "Комиссия перепродажи участков", "Налоги и комиссии"),
    "market_tax":           ("in", "Налог с продажи ресурсов на рынке", "Налоги и комиссии"),
    "trade_tax":            ("in", "Налог с оборота (сделки между игроками)", "Налоги и комиссии"),
    "rental_commission":    ("in", "Комиссия аренды бизнесов", "Налоги и комиссии"),
    "warehouse_rent_tax":   ("in", "Налог с аренды складов", "Налоги и комиссии"),
    "tender_tax":           ("in", "Налог с тендерных поставок", "Налоги и комиссии"),
    "tender_penalty":       ("in", "Штрафы за разрыв тендеров (доля государства)", "Налоги и комиссии"),
    "withdrawal_fee":       ("in", "Комиссия за вывод", "Вывод"),
    "city_pass_premium":    ("in", "City Pass Premium", "Покупки"),
    "alliance_create":      ("in", "Создание альянсов", "Покупки"),
    "credit_repaid":        ("in", "Возврат кредитов (тело + проценты)", "Кредиты"),
    "founder_pass_sale":    ("in", "Founder Pass — продажа долей", "Founder Pass"),
    "founder_payout_back":  ("in", "Founder Pass — корректировка (возврат выплаты)", "Founder Pass"),
    "other_in":             ("in", "Прочие поступления", "Прочее"),
    # ── expenses (real money paid to players) ──
    "founder_payout":       ("out", "Выплаты по Founder Pass", "Founder Pass"),
    "referral_activation":  ("out", "Бонусы за активацию рефералов", "Рефералы и партнёры"),
    "partner_commission":   ("out", "Комиссии B2B-партнёрам", "Рефералы и партнёры"),
    "state_purchase":       ("out", "Покупка ресурсов государством", "Государство"),
    "credit_issued":        ("out", "Выдача кредитов", "Кредиты"),
    "admin_credit":         ("out", "Начисления администрации на реальный баланс", "Прочее"),
    "other_out":            ("out", "Прочие выплаты", "Прочее"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day(d: Optional[datetime] = None) -> str:
    return (d or _now()).astimezone(timezone(timedelta(hours=3))).date().isoformat()


async def record(db, kind: str, ton: float, *, real_ton: Optional[float] = None, real: Optional[bool] = None,
                 user_id: Optional[str] = None, ref: Optional[str] = None, note: str = "",
                 external: bool = False) -> None:
    """Add one entry. `ton` — the amount in TON (> 0). `real_ton` — the part paid with real money (default: all of
    it; `real=False` → none of it, e.g. a tax withheld from produced income)."""
    try:
        ton = round(float(ton or 0), 9)
        if ton <= 0:
            return
        if kind not in KINDS:
            kind = "other_in"
        if real_ton is None:
            real_ton = ton if real is not False else 0.0
        real_ton = round(max(0.0, min(ton, float(real_ton))), 9)
        now = _now()
        await db.platform_ledger.insert_one({
            "id": str(uuid.uuid4()), "kind": kind, "dir": KINDS[kind][0], "ton": ton, "real_ton": real_ton,
            "user_id": user_id, "ref": ref, "note": (note or "")[:300], "external": bool(external),
            "day": _day(now), "created_at": now.isoformat(),
        })
    except Exception as e:                                   # the ledger must never break a payment
        logger.warning(f"ledger.record {kind} {ton}: {e}")


def real_part(total: float, from_real: float, amount: float) -> float:
    """Real-money share of `amount` when a payment of `total` was paid `from_real` with real balance."""
    try:
        total = float(total or 0)
        return amount if total <= 0 else amount * max(0.0, min(1.0, float(from_real or 0) / total))
    except (TypeError, ValueError):
        return amount


def record_bg(db, kind: str, ton: float, **kw) -> None:
    """Fire-and-forget version for synchronous call sites."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(record(db, kind, ton, **kw))


# ───────────────────────────── report ─────────────────────────────
PERIODS = {"today": 0, "7d": 7, "30d": 30, "90d": 90, "all": None}


async def summary(db, period: str = "30d", date_from: str = "", date_to: str = "") -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if date_from or date_to:
        if date_from:
            q.setdefault("day", {})["$gte"] = date_from
        if date_to:
            q.setdefault("day", {})["$lte"] = date_to
    elif period in PERIODS and PERIODS[period] is not None:
        days = PERIODS[period]
        q["day"] = {"$gte": _day(_now() - timedelta(days=days))} if days else {"$gte": _day()}
    rows = await db.platform_ledger.find(q, {"_id": 0, "kind": 1, "dir": 1, "ton": 1, "real_ton": 1, "day": 1,
                                             "external": 1}).to_list(500000)
    by: Dict[str, Dict[str, Any]] = {}
    days: Dict[str, Dict[str, float]] = {}
    for r in rows:
        k = r.get("kind") or "other_in"
        b = by.setdefault(k, {"kind": k, "dir": KINDS.get(k, ("in",))[0], "label": KINDS.get(k, ("", k))[1],
                              "group": KINDS.get(k, ("", "", "Прочее"))[2], "ton": 0.0, "real_ton": 0.0, "count": 0})
        b["ton"] += float(r.get("ton") or 0)
        b["real_ton"] += float(r.get("real_ton") or 0)
        b["count"] += 1
        d = days.setdefault(r.get("day") or "", {"in": 0.0, "out": 0.0, "in_real": 0.0})
        if b["dir"] == "in":
            d["in"] += float(r.get("ton") or 0)
            d["in_real"] += float(r.get("real_ton") or 0)
        else:
            d["out"] += float(r.get("ton") or 0)
    items = sorted(by.values(), key=lambda x: (x["dir"] != "in", -x["ton"]))
    for x in items:
        x["ton"] = round(x["ton"], 6)
        x["real_ton"] = round(x["real_ton"], 6)
    inc = [x for x in items if x["dir"] == "in"]
    out = [x for x in items if x["dir"] == "out"]
    t_in = sum(x["ton"] for x in inc)
    t_in_real = sum(x["real_ton"] for x in inc)
    t_out = sum(x["ton"] for x in out)
    first = await db.platform_ledger.find({}, {"_id": 0, "created_at": 1}).sort("created_at", 1).limit(1).to_list(1)
    return {
        "period": period, "income": inc, "expense": out,
        "totals": {"income_ton": round(t_in, 6), "income_real_ton": round(t_in_real, 6),
                   "income_bonus_ton": round(t_in - t_in_real, 6), "expense_ton": round(t_out, 6),
                   "net_ton": round(t_in - t_out, 6), "net_real_ton": round(t_in_real - t_out, 6)},
        "daily": [{"day": k, **{kk: round(vv, 6) for kk, vv in v.items()}} for k, v in sorted(days.items())],
        "kinds": {k: {"dir": v[0], "label": v[1], "group": v[2]} for k, v in KINDS.items()},
        "since": first[0]["created_at"] if first else None,
    }


async def entries(db, kind: str = "", limit: int = 200, before: str = "") -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if kind:
        q["kind"] = kind
    if before:
        q["created_at"] = {"$lt": before}
    rows = await db.platform_ledger.find(q, {"_id": 0}).sort("created_at", -1).limit(max(1, min(1000, limit))).to_list(1000)
    ids = list({r["user_id"] for r in rows if r.get("user_id")})
    names = {u["id"]: u.get("username") or u.get("display_name") or "" for u in
             await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "username": 1, "display_name": 1}).to_list(len(ids) + 1)}
    for r in rows:
        r["label"] = KINDS.get(r.get("kind"), ("", r.get("kind")))[1]
        r["username"] = names.get(r.get("user_id"), "")
    return rows


async def ensure_indexes(db) -> None:
    for keys in ([("day", 1), ("kind", 1)], [("created_at", -1)], [("kind", 1), ("created_at", -1)]):
        try:
            await db.platform_ledger.create_index(keys)
        except Exception as e:
            logger.warning(f"ledger index {keys}: {e}")


def create_ledger_router(db, get_current_admin):
    """Admin «Доходы»: GET /api/admin/ledger/summary, GET /api/admin/ledger/entries."""
    from fastapi import APIRouter, Depends
    r = APIRouter(prefix="/api/admin/ledger", tags=["admin-ledger"])

    @r.get("/summary")
    async def ledger_summary(period: str = "30d", date_from: str = "", date_to: str = "",
                             current_user=Depends(get_current_admin)):
        return await summary(db, period, date_from, date_to)

    @r.get("/entries")
    async def ledger_entries(kind: str = "", limit: int = 200, before: str = "",
                             current_user=Depends(get_current_admin)):
        return {"items": await entries(db, kind, limit, before)}

    return r
