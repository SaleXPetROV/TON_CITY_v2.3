"""Admin → «Данные» → «Игроки»: the players list, 100 per page, with filters and sorting.

GET /api/admin/players/search?query=&skip=0&limit=100&sort=new&<filters>

Filters (all optional, combined with AND):
  balance_min / balance_max          real balance, TON
  bonus_min / bonus_max              bonus balance, TON
  businesses_min / businesses_max    number of businesses (tutorial businesses are not counted)
  xp_min / xp_max, income_min / income_max, turnover_min / turnover_max
  reg_from / reg_to                  registration date (YYYY-MM-DD, inclusive)
  login_from / login_to              last login date
  method                             registration method (email / telegram / wallet / google …)
  language                           interface language
  status        blocked | active | withdraw_blocked | admin | demo
  telegram / wallet / email / referrer / alliance / investor     yes | no
Sort: new · old · balance_desc · balance_asc · bonus_desc · businesses_desc · income_desc · xp_desc · login_desc

Dates are stored both as datetimes and as ISO strings in older accounts, so a date filter matches both forms.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

SORTS: Dict[str, Tuple[str, int]] = {
    "new": ("created_at", -1), "old": ("created_at", 1),
    "balance_desc": ("balance_ton", -1), "balance_asc": ("balance_ton", 1),
    "bonus_desc": ("bonus_balance", -1), "income_desc": ("total_income", -1),
    "turnover_desc": ("total_turnover", -1), "xp_desc": ("xp", -1), "login_desc": ("last_login", -1),
}
NUM_FIELDS = {"balance": "balance_ton", "bonus": "bonus_balance", "xp": "xp",
              "income": "total_income", "turnover": "total_turnover"}
YES = ("yes", "1", "true")
NO = ("no", "0", "false")


def _num(v: Any) -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def _date(v: Any, end: bool = False) -> Optional[datetime]:
    s = str(v or "").strip()
    if not s:
        return None
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return d + timedelta(days=1) if end else d


def _date_cond(field: str, start: Optional[datetime], end: Optional[datetime]) -> Optional[Dict[str, Any]]:
    """Matches a datetime field and the same field stored as an ISO string."""
    if not start and not end:
        return None
    dt: Dict[str, Any] = {}
    st: Dict[str, Any] = {}
    if start:
        dt["$gte"] = start.replace(tzinfo=None)
        st["$gte"] = start.isoformat()[:10]
    if end:
        dt["$lt"] = end.replace(tzinfo=None)
        st["$lt"] = end.isoformat()[:10]
    return {"$or": [{field: dt}, {field: st}]}


def _flag(conds: List[Dict[str, Any]], value: str, present: Dict[str, Any], absent: Dict[str, Any]) -> None:
    v = (value or "").strip().lower()
    if v in YES:
        conds.append(present)
    elif v in NO:
        conds.append(absent)


def _filled(field: str) -> Dict[str, Any]:
    return {field: {"$exists": True, "$nin": [None, "", 0]}}


def _empty(field: str) -> Dict[str, Any]:
    return {"$or": [{field: {"$exists": False}}, {field: {"$in": [None, "", 0]}}]}


def build_filter(p: Dict[str, Any], now_iso: str = "") -> List[Dict[str, Any]]:
    """Mongo conditions for everything stored on the user document (business counts are applied separately)."""
    conds: List[Dict[str, Any]] = []
    q = str(p.get("query") or "").strip()
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        ors: List[Dict[str, Any]] = [{"id": rx}, {"wallet_address": rx}, {"username": rx}, {"display_name": rx}, {"email": rx}]
        if q.isdigit():
            ors.append({"telegram_id": int(q)})
        ors.append({"telegram_username": rx})
        conds.append({"$or": ors})
    for key, field in NUM_FIELDS.items():
        lo, hi = _num(p.get(f"{key}_min")), _num(p.get(f"{key}_max"))
        rng: Dict[str, Any] = {}
        if lo is not None:
            rng["$gte"] = lo
        if hi is not None:
            rng["$lte"] = hi
        if rng:
            # a missing field counts as 0
            if (lo is None or lo <= 0) and (hi is None or hi >= 0):
                conds.append({"$or": [{field: rng}, {field: {"$exists": False}}, {field: None}]})
            else:
                conds.append({field: rng})
    for field, a, b in (("created_at", "reg_from", "reg_to"), ("last_login", "login_from", "login_to")):
        c = _date_cond(field, _date(p.get(a)), _date(p.get(b), end=True))
        if c:
            conds.append(c)
    method = str(p.get("method") or "").strip()
    if method:
        conds.append({"registration_method": method})
    lang = str(p.get("language") or "").strip()
    if lang:
        conds.append({"language": lang})
    st = str(p.get("status") or "").strip()
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    if st == "blocked":
        conds.append({"$or": [{"is_blocked": True}, {"is_banned": True}]})
    elif st == "active":
        conds.append({"is_blocked": {"$ne": True}})
        conds.append({"is_banned": {"$ne": True}})
    elif st == "withdraw_blocked":
        conds.append({"withdrawal_blocked_until": {"$gt": now_iso}})
    elif st == "admin":
        conds.append({"is_admin": True})
    elif st == "demo":
        conds.append({"is_demo": True})
    _flag(conds, p.get("telegram"), _filled("telegram_id"), _empty("telegram_id"))
    _flag(conds, p.get("wallet"), _filled("wallet_address"), _empty("wallet_address"))
    _flag(conds, p.get("email"), _filled("email"), _empty("email"))
    _flag(conds, p.get("referrer"), _filled("referrerId"), _empty("referrerId"))
    _flag(conds, p.get("alliance"), _filled("alliance_id"), _empty("alliance_id"))
    _flag(conds, p.get("investor"), {"is_active_investor": True}, {"is_active_investor": {"$ne": True}})
    return conds


async def business_counts(db) -> Dict[str, int]:
    rows = await db.businesses.aggregate([
        {"$match": {"tutorial": {"$ne": True}}},
        {"$group": {"_id": "$owner", "n": {"$sum": 1}}},
    ]).to_list(None)
    return {str(r["_id"]): int(r["n"]) for r in rows if r.get("_id")}


LIST_PROJECTION = {"_id": 0, "id": 1, "username": 1, "display_name": 1, "email": 1, "wallet_address": 1,
                   "telegram_id": 1, "telegram_username": 1, "balance_ton": 1, "bonus_balance": 1, "is_banned": 1,
                   "is_blocked": 1, "is_admin": 1, "is_demo": 1, "created_at": 1, "last_login": 1, "level": 1,
                   "xp": 1, "total_income": 1, "registration_method": 1, "language": 1, "referrerId": 1,
                   "alliance_tag": 1, "withdrawal_blocked_until": 1, "is_active_investor": 1}


async def search_players(db, p: Dict[str, Any]) -> Dict[str, Any]:
    skip = max(0, int(_num(p.get("skip")) or 0))
    limit = int(_num(p.get("limit")) or 100)
    limit = max(1, min(500, limit))
    sort = str(p.get("sort") or "new")
    conds = build_filter(p)

    bmin, bmax = _num(p.get("businesses_min")), _num(p.get("businesses_max"))
    need_counts = bmin is not None or bmax is not None or sort == "businesses_desc"
    counts = await business_counts(db) if need_counts else None
    if counts is not None and (bmin is not None or bmax is not None):
        lo = bmin if bmin is not None else 0
        hi = bmax if bmax is not None else float("inf")
        if lo > 0:
            conds.append({"id": {"$in": [uid for uid, n in counts.items() if lo <= n <= hi]}})
        elif hi != float("inf"):
            conds.append({"id": {"$nin": [uid for uid, n in counts.items() if n > hi]}})

    flt: Dict[str, Any] = {"$and": conds} if conds else {}
    total = await db.users.count_documents(flt)

    if sort == "businesses_desc":
        ids = await db.users.find(flt, {"_id": 0, "id": 1}).to_list(None)
        order = sorted((d.get("id") for d in ids if d.get("id")), key=lambda u: -(counts or {}).get(u, 0))
        page_ids = order[skip:skip + limit]
        docs = await db.users.find({"id": {"$in": page_ids}}, LIST_PROJECTION).to_list(None)
        pos = {u: i for i, u in enumerate(page_ids)}
        docs.sort(key=lambda d: pos.get(d.get("id"), 0))
    else:
        field, direction = SORTS.get(sort, SORTS["new"])
        docs = await db.users.find(flt, LIST_PROJECTION).sort([(field, direction), ("id", 1)]).skip(skip).limit(limit).to_list(limit)

    if counts is None and docs:
        page = [d.get("id") for d in docs if d.get("id")]
        rows = await db.businesses.aggregate([
            {"$match": {"owner": {"$in": page}, "tutorial": {"$ne": True}}},
            {"$group": {"_id": "$owner", "n": {"$sum": 1}}},
        ]).to_list(None)
        counts = {str(r["_id"]): int(r["n"]) for r in rows}
    for d in docs:
        d["businesses_count"] = (counts or {}).get(d.get("id"), 0)
        for k in ("created_at", "last_login"):
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()
    return {"players": docs, "total": total, "skip": skip, "limit": limit,
            "has_more": skip + len(docs) < total}


async def filter_options(db) -> Dict[str, List[str]]:
    """Values for the «Способ регистрации» and «Язык» selects."""
    out: Dict[str, List[str]] = {}
    for key, field in (("methods", "registration_method"), ("languages", "language")):
        try:
            vals = await db.users.distinct(field)
        except Exception:
            vals = []
        out[key] = sorted(str(v) for v in vals if v not in (None, ""))
    return out
