"""GRAM City — Founder Pass (private investor pool) + the player profile card.

The player opens «Профиль игрока» by tapping the profile block (avatar / name /
alliance) on the «Бизнесы» page. If the Founder Pass is visible to him, the
profile shows a «💎 Founder Pass» entry that opens the plans:
    plan = price, share of the project's net profit (%), number of places,
           payout cap = price × cap_pct (default 300 %).
PURCHASE — no application: «Купить» pays the price from the player's REAL balance (balance_ton; the bonus balance
does not count). Not enough money → HTTP 402 {code: "fp_insufficient", missing} and the app opens the top-up
modal with the missing amount (direct TON top-up, then the purchase runs right away). The purchase creates a
HOLDING with the terms frozen at that moment; the admin can also add a share by hand (deal made outside the app).

A player is a FOUNDER (investor) while he has a share with status «active» (payouts go on) or «completed»
(the payout cap is reached — the share stays). users.investor = {since, tier_id, tier_name, active} is kept in sync.
When the admin marks the share «bought_out» (bought back) or «cancelled» the player stops being a founder.
ALL perks of the plan apply — with no time limit — for as long as he is a founder (the best value of his shares;
the plan's CURRENT settings from the admin are used):
    sale_tax_discount_pct      −% of the resource sale tax        (trade_fee_multiplier buff)
    withdraw_fee_discount_pct  −% of the withdrawal fee           (withdrawal_fee_multiplier buff)
    withdraw_speed             "instant" (sent automatically right away) | "h12" (within 12 h) | "standard" (24 h)
    repair_discount_pct        −% of the repair cost              (repair_cost_multiplier)
    welcome_bonus_city         $CITY to the bonus balance once, when the share is created
    city_pass_premium          City Pass Premium for free (taken back when he stops being a founder)
    arcade_extra_attempts      +N paid attempts in every Arcade game
    arcade_xp_bonus_pct        +% XP in the Arcade
    badge                      «💎 Investor» badge in the player profile
PAYOUTS: the admin records a payout → it is credited to the player's REAL balance (balance_ton) with a transaction
«founder_payout» («Выплата Founder Pass от администрации») in his history, a notification, and an expense entry in the
platform ledger («Доходы»). A payout cannot exceed what is left up to the cap.
The buffs are injected into server.get_user_active_buffs_all, so the existing tax / withdrawal math applies them.

Collections: game_settings {type: "founder_pass"}, founder_pass_applications,
founder_pass_holdings. Every plan, number and text is set in the admin
(«Founder Pass» tab); the admin note is written in Russian and translated for
the player's language.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

SETTINGS_TYPE = "founder_pass"
OPEN_STATUSES = ("new", "contacted")
APP_STATUSES = ("new", "contacted", "approved", "rejected", "cancelled")
HOLD_STATUSES = ("active", "completed", "bought_out", "cancelled")
COUNTED_HOLD = ("active", "completed", "bought_out")       # holdings that take a place in a plan
FOUNDER_HOLD = ("active", "completed")                      # holdings that make the player a founder (perks apply)
MAX_OPEN_APPS = 3

PERK_DEFAULTS: Dict[str, Any] = {
    "sale_tax_discount_pct": 0, "withdraw_fee_discount_pct": 0, "repair_discount_pct": 0,
    "welcome_bonus_city": 0, "city_pass_premium": False,
    "arcade_extra_attempts": 0, "arcade_xp_bonus_pct": 0, "badge": True, "withdraw_speed": "standard",
}
WITHDRAW_SPEEDS = ("standard", "h12", "instant")
SPEED_RANK = {s: i for i, s in enumerate(WITHDRAW_SPEEDS)}
PCT_PERKS = ("sale_tax_discount_pct", "withdraw_fee_discount_pct", "repair_discount_pct")

DEFAULT_TIERS: List[Dict[str, Any]] = [
    {"id": "bronze", "name": "BRONZE PASS", "price": 30, "share_pct": 0.1, "slots_total": 30, "slots_taken_manual": 0,
     "badge": "", "active": True,
     "perks": {**PERK_DEFAULTS, "sale_tax_discount_pct": 10, "withdraw_fee_discount_pct": 10, "arcade_extra_attempts": 1,
               "withdraw_speed": "h12"}},
    {"id": "silver", "name": "SILVER PASS", "price": 100, "share_pct": 0.4, "slots_total": 10, "slots_taken_manual": 0,
     "badge": "popular", "active": True,
     "perks": {**PERK_DEFAULTS, "sale_tax_discount_pct": 20, "withdraw_fee_discount_pct": 20, "repair_discount_pct": 10,
               "city_pass_premium": True, "arcade_extra_attempts": 2, "arcade_xp_bonus_pct": 10, "withdraw_speed": "h12"}},
    {"id": "gold", "name": "GOLD FOUNDER", "price": 300, "share_pct": 1.5, "slots_total": 3, "slots_taken_manual": 0,
     "badge": "vip", "active": True,
     "perks": {**PERK_DEFAULTS, "sale_tax_discount_pct": 35, "withdraw_fee_discount_pct": 40, "repair_discount_pct": 25,
               "welcome_bonus_city": 5000, "city_pass_premium": True, "arcade_extra_attempts": 3, "arcade_xp_bonus_pct": 25,
               "withdraw_speed": "instant"}},
]
DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "visibility": "whitelist",        # whitelist | all
    "allowed": [],                    # ids, @usernames, e-mails, Telegram ids
    "contact": "",                    # @manager or https://t.me/... — opened after an application
    "currency": "TON",                # plans are always priced in TON
    "cap_pct": 300,                   # payout cap, % of the price
    "note": "",                       # extra text for players (Russian, auto-translated)
    "tiers": DEFAULT_TIERS,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _num(v: Any, default: float = 0.0, lo: Optional[float] = None, hi: Optional[float] = None) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        x = default
    if x != x:                         # NaN
        x = default
    if lo is not None:
        x = max(lo, x)
    if hi is not None:
        x = min(hi, x)
    return x


def _clean_tier(t: Dict[str, Any], i: int) -> Dict[str, Any]:
    tid = re.sub(r"[^a-z0-9_-]", "", str(t.get("id") or "").lower())[:32] or f"tier{i + 1}"
    badge = str(t.get("badge") or "")
    perks = t.get("perks")
    if perks is None:              # plans saved before perks existed: start from the default plan with the same code
        perks = next((d.get("perks") for d in DEFAULT_TIERS if d["id"] == tid), None)
    return {
        "perks": _clean_perks(perks),
        "id": tid,
        "name": str(t.get("name") or tid.upper()).strip()[:40],
        "price": round(_num(t.get("price"), 0, 0, 10_000_000), 2),
        "share_pct": round(_num(t.get("share_pct"), 0, 0, 100), 4),
        "slots_total": int(_num(t.get("slots_total"), 0, 0, 100_000)),
        "slots_taken_manual": int(_num(t.get("slots_taken_manual"), 0, 0, 100_000)),
        "badge": badge if badge in ("", "popular", "vip") else "",
        "active": bool(t.get("active", True)),
    }


def _clean_perks(p: Any) -> Dict[str, Any]:
    p = p if isinstance(p, dict) else {}
    out = dict(PERK_DEFAULTS)
    for k in PCT_PERKS + ("arcade_xp_bonus_pct",):
        out[k] = round(_num(p.get(k, out[k]), 0, 0, 90 if k in PCT_PERKS else 500), 2)
    out["welcome_bonus_city"] = int(_num(p.get("welcome_bonus_city", 0), 0, 0, 10_000_000))
    out["arcade_extra_attempts"] = int(_num(p.get("arcade_extra_attempts", 0), 0, 0, 20))
    out["city_pass_premium"] = bool(p.get("city_pass_premium", False))
    out["badge"] = bool(p.get("badge", True))
    ws = str(p.get("withdraw_speed") or "standard")
    out["withdraw_speed"] = ws if ws in WITHDRAW_SPEEDS else "standard"
    return out


def _norm_key(s: Any) -> str:
    return str(s or "").strip().lstrip("@").lower()


async def get_settings(db) -> Dict[str, Any]:
    doc = await db.game_settings.find_one({"type": SETTINGS_TYPE}, {"_id": 0}) or {}
    cfg = {**DEFAULTS, **{k: v for k, v in doc.items() if k != "type"}}
    cfg["tiers"] = [_clean_tier(t, i) for i, t in enumerate(cfg.get("tiers") or [])]
    cfg["currency"] = "TON"
    return cfg


async def save_settings(db, patch: Dict[str, Any]) -> Dict[str, Any]:
    cur = await get_settings(db)
    if "enabled" in patch:
        cur["enabled"] = bool(patch["enabled"])
    if "visibility" in patch:
        cur["visibility"] = "all" if patch["visibility"] == "all" else "whitelist"
    if "allowed" in patch:
        raw = patch["allowed"]
        items = raw if isinstance(raw, list) else re.split(r"[\s,;]+", str(raw or ""))
        seen, out = set(), []
        for it in items:
            k = _norm_key(it)
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        cur["allowed"] = out[:5000]
    if "contact" in patch:
        cur["contact"] = str(patch["contact"] or "").strip()[:200]
    cur["currency"] = "TON"
    if "cap_pct" in patch:
        cur["cap_pct"] = int(_num(patch["cap_pct"], 300, 100, 10000))
    if "note" in patch:
        cur["note"] = str(patch["note"] or "")[:1500]
    if "tiers" in patch:
        if not isinstance(patch["tiers"], list):
            raise HTTPException(status_code=400, detail="tiers must be a list")
        tiers = [_clean_tier(t, i) for i, t in enumerate(patch["tiers"][:20]) if isinstance(t, dict)]
        ids = [t["id"] for t in tiers]
        if len(ids) != len(set(ids)):
            raise HTTPException(status_code=400, detail="Код тарифа должен быть уникальным")
        cur["tiers"] = tiers
    await db.game_settings.update_one({"type": SETTINGS_TYPE}, {"$set": {**cur, "type": SETTINGS_TYPE}}, upsert=True)
    return cur


def contact_url(contact: str) -> str:
    c = (contact or "").strip()
    if not c:
        return ""
    if c.startswith("http://") or c.startswith("https://") or c.startswith("tg://"):
        return c
    return f"https://t.me/{c.lstrip('@')}"


def _user_keys(u: Dict[str, Any]) -> set:
    keys = {_norm_key(u.get("id")), _norm_key(u.get("username")), _norm_key(u.get("email")),
            _norm_key(u.get("telegram_id")), _norm_key(u.get("telegram_user_id")), _norm_key(u.get("telegram_username"))}
    keys.discard("")
    return keys


async def _taken(db, tier_id: str) -> int:
    return await db.founder_pass_holdings.count_documents({"tier_id": tier_id, "status": {"$in": list(COUNTED_HOLD)}})


async def _tier_view(db, cfg: Dict[str, Any], t: Dict[str, Any]) -> Dict[str, Any]:
    taken = await _taken(db, t["id"]) + int(t.get("slots_taken_manual") or 0)
    left = max(0, int(t["slots_total"]) - taken)
    return {**{k: t[k] for k in ("id", "name", "price", "share_pct", "slots_total", "badge", "perks")},
            "slots_left": left, "sold_out": left <= 0,
            "max_payout": round(t["price"] * cfg["cap_pct"] / 100.0, 2)}


async def is_visible(db, cfg: Dict[str, Any], user: Dict[str, Any]) -> bool:
    if user.get("is_admin"):
        return True
    if await db.founder_pass_holdings.count_documents({"user_id": user.get("id"), "status": {"$in": list(HOLD_STATUSES)}}, limit=1):
        return True
    if not cfg.get("enabled"):
        return False
    if cfg.get("visibility") == "all":
        return True
    return bool(_user_keys(user) & set(cfg.get("allowed") or []))


def _pub_app(a: Dict[str, Any]) -> Dict[str, Any]:
    return {k: a.get(k) for k in ("id", "tier_id", "tier_name", "price", "currency", "status", "created_at")}


def _pub_hold(h: Dict[str, Any]) -> Dict[str, Any]:
    return {k: h.get(k) for k in ("id", "tier_id", "tier_name", "price", "currency", "share_pct", "cap_pct",
                                   "max_payout", "paid_total", "status", "created_at", "perks")}


async def player_view(db, user: Dict[str, Any], lang: str = "") -> Dict[str, Any]:
    cfg = await get_settings(db)
    if not await is_visible(db, cfg, user):
        return {"visible": False}
    uid = user.get("id")
    tiers = [await _tier_view(db, cfg, t) for t in cfg["tiers"] if t.get("active")]
    holds = await db.founder_pass_holdings.find({"user_id": uid, "status": {"$in": list(HOLD_STATUSES)}}, {"_id": 0}).sort("created_at", -1).to_list(20)
    note = cfg.get("note") or ""
    lang = (lang or "").lower()[:5]
    if note and lang and lang != "ru":
        try:
            from translation_service import translate_cached
            note = await translate_cached(db, note, lang, "ru")
        except Exception:
            pass
    return {
        "visible": True, "enabled": bool(cfg.get("enabled")), "currency": cfg["currency"], "cap_pct": cfg["cap_pct"],
        "tiers": tiers, "note": note, "contact_url": contact_url(cfg.get("contact")),
        "holdings": [_pub_hold(h) for h in holds], "my_perks": await user_perks(db, uid),
        "balance_ton": round(float((await db.users.find_one({"id": uid}, {"_id": 0, "balance_ton": 1}) or {}).get("balance_ton") or 0), 6),
    }


async def buy(db, user: Dict[str, Any], tier_id: str) -> Dict[str, Any]:
    """Buy a share right away, paid from the REAL balance only.
    Not enough money → 402 {code: fp_insufficient, price, balance, missing} (the app opens the top-up modal)."""
    cfg = await get_settings(db)
    if not await is_visible(db, cfg, user) or not cfg.get("enabled"):
        raise HTTPException(status_code=403, detail="fp_closed")
    tier = next((t for t in cfg["tiers"] if t["id"] == tier_id and t.get("active")), None)
    if not tier:
        raise HTTPException(status_code=404, detail="fp_no_tier")
    if (await _tier_view(db, cfg, tier))["sold_out"]:
        raise HTTPException(status_code=400, detail="fp_sold_out")
    uid = user.get("id")
    if await db.founder_pass_holdings.count_documents({"user_id": uid, "tier_id": tier["id"], "status": "active"}, limit=1):
        raise HTTPException(status_code=400, detail="fp_already")
    price = round(float(tier["price"]), 6)
    if price <= 0:
        raise HTTPException(status_code=400, detail="fp_no_tier")
    # one purchase at a time per player (double tap / two devices)
    lock = await db.users.update_one({"id": uid, "fp_buying": {"$ne": True}}, {"$set": {"fp_buying": True}})
    if not lock.modified_count:
        raise HTTPException(status_code=409, detail="fp_busy")
    try:
        paid = await db.users.update_one({"id": uid, "balance_ton": {"$gte": price}}, {"$inc": {"balance_ton": -price}})
        if not paid.modified_count:
            u = await db.users.find_one({"id": uid}, {"_id": 0, "balance_ton": 1}) or {}
            bal = round(float(u.get("balance_ton") or 0), 6)
            raise HTTPException(status_code=402, detail={"code": "fp_insufficient", "price": price, "balance": bal,
                                                         "missing": round(max(0.0, price - bal), 6)})
        hid = _uid()
        # the last place may have been taken a moment ago — check again with our share counted
        await db.founder_pass_holdings.insert_one({"id": hid, "user_id": uid, "tier_id": tier["id"], "status": "reserving",
                                                   "created_at": _now()})
        taken = await db.founder_pass_holdings.count_documents(
            {"tier_id": tier["id"], "status": {"$in": list(COUNTED_HOLD) + ["reserving"]}})
        await db.founder_pass_holdings.delete_one({"id": hid, "status": "reserving"})
        if taken + int(tier.get("slots_taken_manual") or 0) > int(tier["slots_total"]):
            await db.users.update_one({"id": uid}, {"$inc": {"balance_ton": price}})
            raise HTTPException(status_code=400, detail="fp_sold_out")
        doc = await _make_holding(db, cfg, user_id=uid, username=user.get("username") or "", tier=tier, price=price,
                                  admin="purchase", paid_in_app=True, holding_id=hid)
        await db.transactions.insert_one({
            "id": _uid(), "user_id": uid, "type": "founder_pass_purchase", "tx_type": "founder_pass_purchase",
            "amount": -price, "amount_ton": price, "currency": "TON", "status": "completed", "holding_id": hid,
            "description": f"Покупка Founder Pass {tier['name']} ({tier['share_pct']:g}% прибыли)", "created_at": _now()})
    finally:
        await db.users.update_one({"id": uid}, {"$unset": {"fp_buying": ""}})
    try:
        from minigame_rewards import notify_admin
        await notify_admin(db, f"💎 Founder Pass: @{user.get('username') or uid} купил {tier['name']} за {price:g} TON "
                               f"({tier['share_pct']:g}% прибыли). Админка → Founder Pass → Инвесторы.")
    except Exception as e:
        logger.debug("founder pass notify: %s", e)
    nb = await db.users.find_one({"id": uid}, {"_id": 0, "balance_ton": 1, "bonus_balance": 1}) or {}
    return {"ok": True, "holding": _pub_hold(doc), "balance_ton": float(nb.get("balance_ton") or 0),
            "bonus_balance": float(nb.get("bonus_balance") or 0)}


async def sync_investor(db, user_id: str) -> None:
    """users.investor follows the player's shares: {since, tier_id, tier_name, active}."""
    if not user_id:
        return
    holds = await db.founder_pass_holdings.find({"user_id": user_id}, {"_id": 0, "tier_id": 1, "tier_name": 1, "status": 1,
                                                                     "created_at": 1, "price": 1}).to_list(50)
    if not holds:
        await db.users.update_one({"id": user_id}, {"$unset": {"investor": ""}})
        return
    live = [h for h in holds if h.get("status") in FOUNDER_HOLD]
    best = max(live or holds, key=lambda h: float(h.get("price") or 0))
    since = min(h.get("created_at") or _now() for h in holds)
    await db.users.update_one({"id": user_id}, {"$set": {"investor": {
        "since": since, "tier_id": best.get("tier_id"), "tier_name": best.get("tier_name"),
        "active": bool(live), "updated_at": _now()}}})
    invalidate_perks(user_id)


async def _make_holding(db, cfg, *, user_id: str, username: str, tier: Dict[str, Any], price: Optional[float] = None,
                        application_id: str = "", admin: str = "", paid_in_app: bool = False,
                        holding_id: Optional[str] = None) -> Dict[str, Any]:
    p = round(_num(price, tier["price"], 0), 2) if price is not None else tier["price"]
    doc = {"id": holding_id or _uid(), "user_id": user_id, "username": username, "tier_id": tier["id"], "tier_name": tier["name"],
           "price": p, "currency": cfg["currency"], "share_pct": tier["share_pct"], "cap_pct": cfg["cap_pct"],
           "max_payout": round(p * cfg["cap_pct"] / 100.0, 2), "paid_total": 0.0, "payouts": [], "status": "active",
           "perks": _clean_perks(tier.get("perks")),
           "paid_in_app": bool(paid_in_app),
           "application_id": application_id, "created_by": admin, "created_at": _now(), "updated_at": _now()}
    await db.founder_pass_holdings.insert_one(dict(doc))
    await sync_investor(db, user_id)                # the player is a founder from now on
    try:
        import ledger
        await ledger.record(db, "founder_pass_sale", p, user_id=user_id, ref=doc["id"], real=True,
                            external=not paid_in_app,
                            note=(f"{tier['name']} — @{username}" if username else tier["name"])
                                 + (" (оплата с баланса)" if paid_in_app else " (сделка вне игры, добавлено админом)"))
    except Exception as e:
        logger.warning(f"ledger founder_pass_sale: {e}")
    bonus = int((doc["perks"] or {}).get("welcome_bonus_city") or 0)
    if bonus > 0:                                   # one-time welcome bonus to the bonus balance
        await db.users.update_one({"id": user_id}, {"$inc": {"bonus_balance": bonus / 1000.0}})
        await db.transactions.insert_one({
            "id": _uid(), "user_id": user_id, "type": "founder_pass_bonus", "tx_type": "founder_pass_bonus",
            "amount_ton": bonus / 1000.0, "currency": "BONUS", "status": "completed",
            "description": f"Founder Pass {tier['name']}: бонус {bonus} $CITY", "created_at": _now()})
        await db.founder_pass_holdings.update_one({"id": doc["id"]}, {"$set": {"welcome_bonus_paid": bonus}})
    return doc


# ── investor perks ──────────────────────────────────────────────────────────
_perk_cache: Dict[str, Any] = {}
PERK_TTL = 60.0


def invalidate_perks(user_id: Optional[str] = None) -> None:
    if user_id:
        _perk_cache.pop(user_id, None)
    else:
        _perk_cache.clear()


async def user_perks(db, user_id: str) -> Dict[str, Any]:
    """Founder perks of the player — ALL perks, for as long as he is a founder (a share «active» or «completed»);
    the best value over his shares, using the plan's live settings (the snapshot taken with the share if the
    plan was deleted). {} when he is not a founder (never was, or his shares were bought back / cancelled)."""
    import time
    if not user_id:
        return {}
    hit = _perk_cache.get(user_id)
    if hit and time.monotonic() - hit[0] < PERK_TTL:
        return hit[1]
    out: Dict[str, Any] = {}
    holds = await db.founder_pass_holdings.find({"user_id": user_id, "status": {"$in": list(FOUNDER_HOLD)}},
                                                {"_id": 0, "tier_id": 1, "perks": 1, "status": 1}).to_list(50)
    if holds:
        tiers = {t["id"]: t for t in (await get_settings(db))["tiers"]}
        out = dict(PERK_DEFAULTS)
        out["badge"] = False
        out["withdraw_speed"] = "standard"
        for h in holds:
            pk = _clean_perks((tiers.get(h.get("tier_id")) or {}).get("perks") or h.get("perks"))
            for k, v in pk.items():
                if k == "withdraw_speed":
                    out[k] = v if SPEED_RANK.get(v, 0) > SPEED_RANK.get(out[k], 0) else out[k]
                elif isinstance(v, bool):
                    out[k] = out[k] or v
                else:
                    out[k] = max(out[k], v)
        out["investor"] = True
        out["active"] = True
        out["share_active"] = any(h.get("status") == "active" for h in holds)
    _perk_cache[user_id] = (time.monotonic(), out)
    return out


def perk_buffs(perks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Founder Pass perks in the shape of server.get_user_active_buffs_all items."""
    if not perks or not perks.get("active"):
        return []
    out = []
    for key, etype, label in (("sale_tax_discount_pct", "trade_fee_multiplier", "налог с продаж"),
                              ("withdraw_fee_discount_pct", "withdrawal_fee_multiplier", "комиссия вывода"),
                              ("repair_discount_pct", "repair_cost_multiplier", "ремонт")):
        v = float(perks.get(key) or 0)
        if v > 0:
            out.append({"id": f"founder_{key}", "name": f"Founder Pass: −{v:g}% {label}", "icon": "💎",
                        "effect": {"type": etype, "value": round(1 - v / 100.0, 4)}, "source": "founder_pass"})
    return out


def create_founder_pass_router(db, get_current_user, get_current_admin) -> APIRouter:
    root = APIRouter()
    r = APIRouter(prefix="/api/founder-pass", tags=["founder-pass"])
    p = APIRouter(prefix="/api/profile", tags=["profile"])
    a = APIRouter(prefix="/api/admin/founder-pass", tags=["founder-pass-admin"])

    async def _udoc(current_user) -> Dict[str, Any]:
        u = await db.users.find_one({"id": current_user.id}, {"_id": 0, "password": 0, "password_hash": 0}) or {}
        u.setdefault("id", current_user.id)
        u["is_admin"] = bool(getattr(current_user, "is_admin", False) or u.get("is_admin"))
        return u

    # ── player ────────────────────────────────────────────────────────────
    @p.get("/card")
    async def profile_card(current_user=Depends(get_current_user)):
        """The «Профиль игрока» modal: a few stats + whether the Founder Pass entry is shown."""
        u = await _udoc(current_user)
        biz = await db.businesses.count_documents({"owner": current_user.id})
        cfg = await get_settings(db)
        perks = await user_perks(db, current_user.id)
        return {
            "businesses": biz,
            "registered_at": str(u.get("created_at") or ""),
            "balance_ton": float(u.get("balance_ton") or 0),
            "bonus_balance": float(u.get("bonus_balance") or 0),
            "founder_pass": await is_visible(db, cfg, u),
            "investor": bool(perks.get("active") and perks.get("badge")),
        }

    @r.get("")
    async def fp_view(lang: str = "", current_user=Depends(get_current_user)):
        return await player_view(db, await _udoc(current_user), lang)

    @r.post("/buy")
    async def fp_buy(body: Dict[str, Any], current_user=Depends(get_current_user)):
        return await buy(db, await _udoc(current_user), str(body.get("tier_id") or ""))

    # ── admin ─────────────────────────────────────────────────────────────
    @a.get("/settings")
    async def adm_get(current_user=Depends(get_current_admin)):
        cfg = await get_settings(db)
        tiers = []
        for t in cfg["tiers"]:
            tv = await _tier_view(db, cfg, t)
            tiers.append({**t, "holdings": await _taken(db, t["id"]), "slots_left": tv["slots_left"], "max_payout": tv["max_payout"]})
        apps_new = await db.founder_pass_applications.count_documents({"status": {"$in": list(OPEN_STATUSES)}})
        founders = len(await db.founder_pass_holdings.distinct("user_id", {"status": {"$in": list(FOUNDER_HOLD)}}))
        holds = await db.founder_pass_holdings.find({"status": {"$in": list(COUNTED_HOLD)}}, {"_id": 0, "price": 1, "paid_total": 1, "status": 1}).to_list(10000)
        stats = {"open_applications": apps_new, "founders": founders,
                 "active_holdings": sum(1 for h in holds if h.get("status") == "active"),
                 "raised": round(sum(float(h.get("price") or 0) for h in holds), 2),
                 "paid": round(sum(float(h.get("paid_total") or 0) for h in holds), 2)}
        return {**cfg, "tiers": tiers, "stats": stats, "contact_url": contact_url(cfg.get("contact"))}

    @a.put("/settings")
    async def adm_put(body: Dict[str, Any], current_user=Depends(get_current_admin)):
        await save_settings(db, body or {})
        invalidate_perks()
        return await adm_get(current_user)

    @a.get("/applications")
    async def adm_apps(status: str = "", current_user=Depends(get_current_admin)):
        q: Dict[str, Any] = {}
        if status == "open":
            q["status"] = {"$in": list(OPEN_STATUSES)}
        elif status in APP_STATUSES:
            q["status"] = status
        items = await db.founder_pass_applications.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"items": items}

    @a.post("/applications/{app_id}/status")
    async def adm_app_status(app_id: str, body: Dict[str, Any], current_user=Depends(get_current_admin)):
        st = str(body.get("status") or "")
        if st not in ("contacted", "approved", "rejected"):
            raise HTTPException(status_code=400, detail="Неверный статус")
        app = await db.founder_pass_applications.find_one({"id": app_id}, {"_id": 0})
        if not app:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        if app["status"] not in OPEN_STATUSES:
            raise HTTPException(status_code=400, detail="Заявка уже закрыта")
        holding = None
        if st == "approved":
            cfg = await get_settings(db)
            tier = next((t for t in cfg["tiers"] if t["id"] == app["tier_id"]), None)
            if not tier:
                raise HTTPException(status_code=400, detail="Тариф этой заявки удалён")
            if (await _tier_view(db, cfg, tier))["sold_out"]:
                raise HTTPException(status_code=400, detail="В тарифе не осталось мест")
            # the terms the player applied for are kept (price), the cap uses the current cap_pct
            holding = await _make_holding(db, cfg, user_id=app["user_id"], username=app.get("username") or "",
                                          tier=tier, price=app.get("price"), application_id=app_id,
                                          admin=getattr(current_user, "username", "") or current_user.id)
        await db.founder_pass_applications.update_one(
            {"id": app_id}, {"$set": {"status": st, "admin_note": str(body.get("admin_note") or app.get("admin_note") or "")[:500],
                                      "updated_at": _now(), "handled_by": getattr(current_user, "username", "") or current_user.id}})
        return {"ok": True, "holding": holding}

    @a.get("/holdings")
    async def adm_holds(current_user=Depends(get_current_admin)):
        items = await db.founder_pass_holdings.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
        return {"items": items}

    @a.post("/holdings")
    async def adm_add_hold(body: Dict[str, Any], current_user=Depends(get_current_admin)):
        """A deal made outside the app: find the player by id / @username / e-mail / Telegram id."""
        key = _norm_key(body.get("user"))
        if not key:
            raise HTTPException(status_code=400, detail="Укажите игрока")
        u = await db.users.find_one({"$or": [{"id": key}, {"email": key}, {"telegram_id": key},
                                             {"username": {"$regex": f"^{re.escape(key)}$", "$options": "i"}}]},
                                    {"_id": 0, "id": 1, "username": 1})
        if not u and key.isdigit():
            u = await db.users.find_one({"telegram_id": int(key)}, {"_id": 0, "id": 1, "username": 1})
        if not u:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        cfg = await get_settings(db)
        tier = next((t for t in cfg["tiers"] if t["id"] == body.get("tier_id")), None)
        if not tier:
            raise HTTPException(status_code=400, detail="Тариф не найден")
        doc = await _make_holding(db, cfg, user_id=u["id"], username=u.get("username") or "", tier=tier,
                                  price=body.get("price") if body.get("price") not in (None, "") else None,
                                  admin=getattr(current_user, "username", "") or current_user.id)
        return {"ok": True, "holding": doc}

    @a.post("/holdings/{hid}/payout")
    async def adm_payout(hid: str, body: Dict[str, Any], current_user=Depends(get_current_admin)):
        """A payout to the founder: credited to his REAL balance + «founder_payout» in his history + notification +
        expense in the platform ledger. A negative amount is a correction (taken back from his real balance)."""
        amount = round(_num(body.get("amount"), 0), 6)
        if amount == 0:
            raise HTTPException(status_code=400, detail="Укажите сумму")
        h = await db.founder_pass_holdings.find_one({"id": hid}, {"_id": 0})
        if not h:
            raise HTTPException(status_code=404, detail="Доля не найдена")
        paid_before = float(h.get("paid_total") or 0)
        cap = float(h.get("max_payout") or 0)
        if amount > 0:
            if h.get("status") not in FOUNDER_HOLD:
                raise HTTPException(status_code=400, detail="Доля выкуплена или отменена — выплаты по ней не начисляются")
            left = round(cap - paid_before, 6) if cap > 0 else None
            if left is not None and amount > left + 1e-9:
                raise HTTPException(status_code=400, detail=f"Сумма больше остатка до лимита: можно начислить не более {max(0.0, left):g} TON")
        elif -amount > paid_before + 1e-9:
            raise HTTPException(status_code=400, detail=f"Корректировка больше выплаченного ({paid_before:g} TON)")
        uid = h.get("user_id")
        note = str(body.get("note") or "")[:300]
        by = getattr(current_user, "username", "") or getattr(current_user, "email", "") or current_user.id
        if amount > 0:
            await db.users.update_one({"id": uid}, {"$inc": {"balance_ton": amount, "total_income": amount}})
        else:
            took = await db.users.update_one({"id": uid, "balance_ton": {"$gte": -amount}}, {"$inc": {"balance_ton": amount}})
            if not took.modified_count:
                raise HTTPException(status_code=400, detail="На реальном балансе игрока недостаточно средств для корректировки")
        paid = round(max(0.0, paid_before + amount), 6)
        upd: Dict[str, Any] = {"paid_total": paid, "updated_at": _now()}
        if h.get("status") == "active" and cap > 0 and paid >= cap - 1e-9:
            upd["status"] = "completed"
        elif h.get("status") == "completed" and paid < cap - 1e-9:
            upd["status"] = "active"
        tx_id = _uid()
        await db.founder_pass_holdings.update_one({"id": hid}, {"$set": upd, "$push": {"payouts": {
            "amount": amount, "note": note, "at": _now(), "by": by, "tx_id": tx_id}}})
        desc = (f"Выплата Founder Pass от администрации ({h.get('tier_name')})" if amount > 0
                else f"Корректировка выплаты Founder Pass администрацией ({h.get('tier_name')})")
        await db.transactions.insert_one({
            "id": tx_id, "user_id": uid, "type": "founder_payout", "tx_type": "founder_payout",
            "amount": amount, "amount_ton": amount, "currency": "TON", "status": "completed",
            "from_address": "Администрация", "holding_id": hid, "tier_name": h.get("tier_name"),
            "description": desc + (f" — {note}" if note else ""), "admin": by, "created_at": _now()})
        try:
            import ledger
            if amount > 0:
                await ledger.record(db, "founder_payout", amount, user_id=uid, ref=hid, note=f"{h.get('tier_name')} — {note}" if note else h.get("tier_name"))
            else:
                await ledger.record(db, "founder_payout_back", -amount, user_id=uid, ref=hid, note=note)
        except Exception as e:
            logger.warning(f"ledger founder_payout: {e}")
        if amount > 0:
            try:
                from core.notify import notify_user
                await notify_user(db, uid, "💎 Founder Pass",
                                  f"Администрация начислила выплату по Founder Pass {h.get('tier_name')}: "
                                  f"+{amount:g} TON на реальный баланс.", type_key="founder_payout", priority="success")
            except Exception as e:
                logger.debug(f"founder payout notify: {e}")
        await sync_investor(db, uid)
        return {"ok": True, "paid_total": paid, "status": upd.get("status", h.get("status"))}

    @a.post("/holdings/{hid}/status")
    async def adm_hold_status(hid: str, body: Dict[str, Any], current_user=Depends(get_current_admin)):
        st = str(body.get("status") or "")
        if st not in HOLD_STATUSES:
            raise HTTPException(status_code=400, detail="Неверный статус")
        h = await db.founder_pass_holdings.find_one({"id": hid}, {"_id": 0, "user_id": 1})
        r_ = await db.founder_pass_holdings.update_one({"id": hid}, {"$set": {"status": st, "updated_at": _now()}})
        if not r_.matched_count:
            raise HTTPException(status_code=404, detail="Доля не найдена")
        await sync_investor(db, (h or {}).get("user_id"))
        return {"ok": True}

    # ── investors (every player who has / had a share) ─────────────────────
    _SECRET = ("hashed_password", "password", "password_hash", "session_id", "totp_secret", "two_fa_secret",
               "reset_token", "verify_token", "email_enc", "email_lc_hash", "refresh_token")

    async def _investor_rows() -> List[Dict[str, Any]]:
        holds = await db.founder_pass_holdings.find({"status": {"$in": list(HOLD_STATUSES)}}, {"_id": 0, "payouts": 0}).to_list(20000)
        by: Dict[str, Dict[str, Any]] = {}
        for h in holds:
            row = by.setdefault(h["user_id"], {"user_id": h["user_id"], "holdings": [], "invested": 0.0, "paid": 0.0})
            row["holdings"].append({k: h.get(k) for k in ("id", "tier_id", "tier_name", "price", "share_pct", "status",
                                                          "paid_total", "max_payout", "created_at", "paid_in_app")})
            if h.get("status") in COUNTED_HOLD:
                row["invested"] += float(h.get("price") or 0)
            row["paid"] += float(h.get("paid_total") or 0)
        ids = list(by)
        users = {u["id"]: u for u in await db.users.find(
            {"id": {"$in": ids}}, {"_id": 0, "id": 1, "username": 1, "display_name": 1, "email": 1, "email_enc": 1,
                                   "telegram_id": 1, "telegram_username": 1, "balance_ton": 1, "bonus_balance": 1,
                                   "created_at": 1, "last_login": 1, "is_blocked": 1, "investor": 1, "avatar": 1}).to_list(len(ids) + 1)}
        out = []
        for uid, row in by.items():
            u = users.get(uid) or {}
            try:
                from email_crypto import resolve_email
                email = resolve_email(u) or ""
            except Exception:
                email = u.get("email") or ""
            live = [h for h in row["holdings"] if h["status"] in FOUNDER_HOLD]
            out.append({**row, "invested": round(row["invested"], 6), "paid": round(row["paid"], 6),
                        "username": u.get("username") or "", "display_name": u.get("display_name") or "", "email": email,
                        "telegram_id": str(u.get("telegram_id") or ""), "telegram_username": u.get("telegram_username") or "",
                        "balance_ton": float(u.get("balance_ton") or 0), "bonus_balance": float(u.get("bonus_balance") or 0),
                        "registered_at": str(u.get("created_at") or ""), "last_login": str(u.get("last_login") or ""),
                        "is_blocked": bool(u.get("is_blocked")), "founder": bool(live),
                        "since": (u.get("investor") or {}).get("since") or min(h["created_at"] or "" for h in row["holdings"]),
                        "tiers": sorted({h["tier_name"] for h in live}) or sorted({h["tier_name"] for h in row["holdings"]})})
        out.sort(key=lambda x: (not x["founder"], -x["invested"]))
        return out

    @a.get("/investors")
    async def adm_investors(q: str = "", tier: str = "", status: str = "", current_user=Depends(get_current_admin)):
        rows = await _investor_rows()
        if q:
            k = _norm_key(q)
            rows = [r_ for r_ in rows if any(k in str(r_.get(f) or "").lower() for f in
                                            ("username", "display_name", "email", "telegram_id", "telegram_username", "user_id"))]
        if tier:
            rows = [r_ for r_ in rows if any(h["tier_id"] == tier for h in r_["holdings"])]
        if status == "founder":
            rows = [r_ for r_ in rows if r_["founder"]]
        elif status == "former":
            rows = [r_ for r_ in rows if not r_["founder"]]
        return {"items": rows, "count": len(rows),
                "totals": {"founders": sum(1 for r_ in rows if r_["founder"]),
                           "invested": round(sum(r_["invested"] for r_ in rows), 6),
                           "paid": round(sum(r_["paid"] for r_ in rows), 6)}}

    @a.get("/investors/{user_id}")
    async def adm_investor(user_id: str, current_user=Depends(get_current_admin)):
        """Everything known about the investor: account, balances, perks, shares with every payout, transactions,
        withdrawals, businesses, credits, referrals, City Pass, alliance, login history."""
        u = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not u:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        try:
            from email_crypto import resolve_email
            u["email"] = resolve_email(u) or u.get("email") or ""
        except Exception:
            pass
        for k in _SECRET:
            u.pop(k, None)
        holds = await db.founder_pass_holdings.find({"user_id": user_id, "status": {"$in": list(HOLD_STATUSES)}},
                                                    {"_id": 0}).sort("created_at", -1).to_list(50)
        txs = await db.transactions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(150).to_list(150)
        wds = [t for t in txs if (t.get("tx_type") or t.get("type")) in ("withdrawal", "instant_withdrawal")]
        deps = await db.transactions.find({"user_id": user_id, "$or": [{"tx_type": "deposit"}, {"type": "deposit"}]},
                                          {"_id": 0, "amount_ton": 1, "status": 1}).to_list(5000)
        all_wd = await db.transactions.find({"user_id": user_id, "tx_type": {"$in": ["withdrawal", "instant_withdrawal"]}},
                                            {"_id": 0, "amount_ton": 1, "amount": 1, "status": 1}).to_list(5000)
        biz_q: List[Dict[str, Any]] = [{"owner": user_id}]
        if u.get("wallet_address"):
            biz_q.append({"owner": u["wallet_address"]})
        biz = await db.businesses.find({"$or": biz_q}, {"_id": 0, "id": 1, "business_type": 1, "level": 1, "durability": 1,
                                                        "x": 1, "y": 1, "created_at": 1, "tier": 1}).to_list(200)
        credits = await db.credits.find({"borrower_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
        refs = await db.users.count_documents({"referrerId": user_id})
        ledger_rows = await db.platform_ledger.find({"user_id": user_id}, {"_id": 0}).to_list(20000)
        spent = round(sum(float(r_.get("ton") or 0) for r_ in ledger_rows if r_.get("dir") == "in"), 6)
        got = round(sum(float(r_.get("ton") or 0) for r_ in ledger_rows if r_.get("dir") == "out"), 6)
        cp = None
        try:
            import city_pass as _cp
            cfg_cp = await _cp.get_config(db)
            cp = await db.city_pass_progress.find_one({"user_id": user_id, "season_id": cfg_cp.get("season_id")}, {"_id": 0})
        except Exception:
            pass

        def _sum(rows, statuses=("completed", "approved", "sent", "success")):
            return round(sum(abs(float(r_.get("amount_ton") or r_.get("amount") or 0)) for r_ in rows
                             if (r_.get("status") or "completed") in statuses), 6)
        return {
            "user": u, "perks": await user_perks(db, user_id), "holdings": holds,
            "summary": {"invested": round(sum(float(h.get("price") or 0) for h in holds if h.get("status") in COUNTED_HOLD), 6),
                        "paid": round(sum(float(h.get("paid_total") or 0) for h in holds), 6),
                        "max_payout": round(sum(float(h.get("max_payout") or 0) for h in holds if h.get("status") in FOUNDER_HOLD), 6),
                        "deposits": _sum(deps), "withdrawn": _sum(all_wd),
                        "withdraw_pending": _sum(all_wd, ("pending", "processing")),
                        "platform_received": spent, "platform_paid": got,
                        "businesses": len(biz), "referrals": refs,
                        "active_debt": round(sum(float(c.get("remaining") or 0) for c in credits if c.get("status") in ("active", "overdue")), 6)},
            "transactions": txs, "withdrawals": wds, "businesses": biz, "credits": credits, "city_pass": cp,
        }

    root.include_router(r)
    root.include_router(p)
    root.include_router(a)
    return root
