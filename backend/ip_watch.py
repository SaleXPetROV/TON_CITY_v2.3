"""Мульти-аккаунты по IP.

Every request of a signed-in player leaves (user, IP) in db.user_ips — at most once per 15 minutes per pair, written
in the background, so the game never waits for it. The IP is stored encrypted (core/pii.py) with a blind index, like
the anti-fraud events; only the admin report decrypts it.

  ClientIPMiddleware     — remembers the client IP of the request (Cloudflare → X-Real-IP → X-Forwarded-For from the right → peer)
  touch(db, user_doc)    — called from get_current_user: records the pair
  groups(db, …)          — IPs used by 2+ accounts in the last N days (ignored IPs left out)
  csv_report(groups)     — the file: group, IP, account id, nickname, blocked, last seen
  send_scheduled(db)     — the daily file to the admins' Telegram at the time set in the admin (scheduler, every 5 min)

Admin (Russian): Мульти-аккаунты → «Общий IP» — groups, block selected, «не мульти» (ignore an IP: office, mobile
operator), export, and the report settings (time, time zone, period, recipients, «Отправить сейчас»).
"""
import asyncio
import csv
import io
import ipaddress
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CLIENT_IP: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
REQUEST_PATH: ContextVar[str] = ContextVar("request_path", default="")
THROTTLE_S = 15 * 60
SETTINGS_TYPE = "multi_ip_report"
DEFAULTS: Dict[str, Any] = {"enabled": False, "time": "09:00", "tz": "Europe/Moscow", "days": 30, "min_users": 2,
                            "chat_ids": [], "only_new": False}
_seen: Dict[tuple, float] = {}
_tasks: set = set()


def _ip_from_scope(scope) -> Optional[str]:
    """Client IP that the player can't fake with his own header.

    Cloudflare's CF-Connecting-IP first, then X-Real-IP (nginx sets it to the address it sees), then
    X-Forwarded-For read from the RIGHT (the left part is whatever the client sent), then the peer.
    The first public address wins; a private one (an inner proxy) only if there is nothing else."""
    h = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
    cands = [h.get("cf-connecting-ip"), h.get("x-real-ip")]
    cands += list(reversed([x for x in (h.get("x-forwarded-for") or "").split(",")]))
    cands.append((scope.get("client") or [None])[0])
    first = None
    for cand in cands:
        c = (cand or "").strip()
        if not c:
            continue
        try:
            ipaddress.ip_address(c)
        except ValueError:
            continue
        if _public(c):
            return c
        first = first or c
    return first


class ClientIPMiddleware:
    """Pure ASGI middleware (so the context variable reaches the endpoint and its dependencies)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            t1 = CLIENT_IP.set(_ip_from_scope(scope))
            t2 = REQUEST_PATH.set(scope.get("path") or "")
            try:
                return await self.app(scope, receive, send)
            finally:
                CLIENT_IP.reset(t1)
                REQUEST_PATH.reset(t2)
        return await self.app(scope, receive, send)


def _public(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return not (a.is_private or a.is_loopback or a.is_link_local or a.is_unspecified or a.is_reserved)
    except ValueError:
        return False


def touch(db, user_doc: Dict[str, Any]) -> None:
    """Remember (player, IP) of the current request. Never raises, never blocks the request."""
    try:
        ip = CLIENT_IP.get()
        uid = (user_doc or {}).get("id")
        if not ip or not uid or not _public(ip):
            return
        now = time.time()
        k = (uid, ip)
        if now - _seen.get(k, 0) < THROTTLE_S:
            return
        _seen[k] = now
        if len(_seen) > 200000:
            for kk in [x for x, t in _seen.items() if now - t > THROTTLE_S]:
                _seen.pop(kk, None)
        t = asyncio.get_running_loop().create_task(_write(db, uid, (user_doc or {}).get("username"), ip))
        _tasks.add(t)
        t.add_done_callback(_tasks.discard)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"ip_watch touch: {e}")


async def _write(db, uid: str, username: Optional[str], ip: str) -> None:
    from core import pii as _pii
    now = datetime.now(timezone.utc)
    try:
        await db.user_ips.update_one(
            {"user_id": uid, "ip_bidx": _pii.bidx(ip)},
            {"$set": {"ip_enc": _pii.enc(ip), "username": username, "last_seen": now},
             "$setOnInsert": {"first_seen": now}, "$inc": {"hits": 1}},
            upsert=True)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"ip_watch write: {e}")


def blocked_request() -> bool:
    """A blocked player may still open the app (to see why) and write to support — nothing else."""
    p = REQUEST_PATH.get() or ""
    return not (p.startswith("/api/auth/") or p.startswith("/api/support/") or p.startswith("/api/ws/")
                or p in ("/api/health", "/api/me"))


def guard(db, user_doc: Dict[str, Any]) -> None:
    """Called by every «who is this player» dependency: remember the IP and stop a blocked player."""
    touch(db, user_doc)
    if user_doc and user_doc.get("is_blocked") and not user_doc.get("is_admin") and blocked_request():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")


async def ensure_indexes(db) -> None:
    try:
        await db.user_ips.create_index([("user_id", 1), ("ip_bidx", 1)], unique=True, name="user_ip")
        await db.user_ips.create_index([("ip_bidx", 1), ("last_seen", -1)], name="ip_last_seen")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"ip_watch indexes: {e}")


def _iso(v) -> Optional[str]:
    """ISO time with the zone (the database may hand back a naive UTC datetime)."""
    if not v:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


async def groups(db, days: int = 30, min_users: int = 2, include_ignored: bool = False, q: str = "") -> Dict[str, Any]:
    from core import pii as _pii
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    ignored = {d["ip_bidx"]: d async for d in db.user_ips_ignored.find({}, {"_id": 0})}
    by_ip: Dict[str, Dict[str, Any]] = {}
    async for r in db.user_ips.find({"last_seen": {"$gte": since}}, {"_id": 0}):
        g = by_ip.setdefault(r["ip_bidx"], {"ip_bidx": r["ip_bidx"], "ip_enc": r.get("ip_enc"), "rows": []})
        g["rows"].append(r)
    out: List[Dict[str, Any]] = []
    uids: set = set()
    for b, g in by_ip.items():
        users = {r["user_id"] for r in g["rows"]}
        if len(users) < max(2, int(min_users)):
            continue
        if b in ignored and not include_ignored:
            continue
        g["user_ids"] = users
        uids |= users
        out.append(g)
    docs = {u["id"]: u async for u in db.users.find(
        {"id": {"$in": list(uids)}},
        {"_id": 0, "id": 1, "username": 1, "is_blocked": 1, "block_reason": 1, "created_at": 1, "is_admin": 1,
         "balance_ton": 1, "bonus_balance": 1, "telegram_username": 1})} if uids else {}
    # how many IPs each account shares (a «hub» account links several groups)
    shared: Dict[str, int] = {}
    for g in out:
        for u in g["user_ids"]:
            shared[u] = shared.get(u, 0) + 1
    res = []
    ql = (q or "").strip().lower()
    for g in out:
        ip = _pii.dec(g["ip_enc"]) or "—"
        rows = sorted(g["rows"], key=lambda r: r.get("last_seen") or since, reverse=True)
        users = []
        for r in rows:
            d = docs.get(r["user_id"]) or {}
            users.append({
                "id": r["user_id"], "username": d.get("username") or r.get("username") or "—",
                "blocked": bool(d.get("is_blocked")), "block_reason": d.get("block_reason"), "admin": bool(d.get("is_admin")),
                "created_at": _iso(d.get("created_at")),
                "balance_city": round((float(d.get("balance_ton") or 0) + float(d.get("bonus_balance") or 0)) * 1000, 2),
                "first_seen": _iso(r.get("first_seen")),
                "last_seen": _iso(r.get("last_seen")),
                "hits": int(r.get("hits") or 0), "shared_ips": shared.get(r["user_id"], 1)})
        if ql and ql not in ip.lower() and not any(ql in (u["username"] or "").lower() or ql in u["id"].lower() for u in users):
            continue
        res.append({"ip": ip, "ip_bidx": g["ip_bidx"], "count": len(g["user_ids"]),
                    "blocked": sum(1 for u in users if u["blocked"]),
                    "last_seen": users[0]["last_seen"] if users else None, "users": users,
                    "ignored": g["ip_bidx"] in ignored, "note": (ignored.get(g["ip_bidx"]) or {}).get("note")})
    res.sort(key=lambda g: g["last_seen"] or "", reverse=True)      # newest first …
    res.sort(key=lambda g: -g["count"])                              # … within the biggest groups first
    accounts = {u["id"] for g in res for u in g["users"]}
    return {"days": days, "min_users": min_users, "groups": res, "totals": {
        "groups": len(res), "accounts": len(accounts),
        "blocked": len({u["id"] for g in res for u in g["users"] if u["blocked"]}),
        "tracked_pairs": await db.user_ips.count_documents({"last_seen": {"$gte": since}}),
        "ignored": len(ignored)}}


def csv_report(data: Dict[str, Any], tz: str = "UTC") -> bytes:
    from zoneinfo import ZoneInfo
    try:
        zone = ZoneInfo(tz or "UTC")
    except Exception:  # noqa: BLE001
        tz, zone = "UTC", timezone.utc

    def when(iso):
        try:
            return datetime.fromisoformat(_iso(iso)).astimezone(zone).strftime("%Y-%m-%d %H:%M") if iso else ""
        except Exception:  # noqa: BLE001
            return (iso or "")[:16].replace("T", " ")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Группа", "IP", "ID игрока", "Ник", "Аккаунтов на IP", "Заблокирован", f"Последний вход ({tz})", "Действий"])
    for i, g in enumerate(data.get("groups") or [], 1):
        for u in g["users"]:
            w.writerow([i, g["ip"], u["id"], u["username"], g["count"], "да" if u["blocked"] else "нет",
                        when(u.get("last_seen")), u["hits"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")      # BOM: Excel opens Cyrillic correctly


async def get_settings(db) -> Dict[str, Any]:
    d = await db.admin_settings.find_one({"type": SETTINGS_TYPE}, {"_id": 0}) or {}
    return {**DEFAULTS, **{k: v for k, v in d.items() if k != "type"}}


async def save_settings(db, patch: Dict[str, Any]) -> Dict[str, Any]:
    import re
    from zoneinfo import ZoneInfo
    clean: Dict[str, Any] = {}
    if "enabled" in patch:
        clean["enabled"] = bool(patch["enabled"])
    if "time" in patch:
        if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", str(patch["time"])):
            raise ValueError("Время — в формате ЧЧ:ММ")
        clean["time"] = str(patch["time"])
    if "tz" in patch:
        ZoneInfo(str(patch["tz"]))
        clean["tz"] = str(patch["tz"])
    if "days" in patch:
        clean["days"] = max(1, min(90, int(patch["days"])))
    if "min_users" in patch:
        clean["min_users"] = max(2, min(50, int(patch["min_users"])))
    if "only_new" in patch:
        clean["only_new"] = bool(patch["only_new"])
    if "chat_ids" in patch:
        ids = patch["chat_ids"] if isinstance(patch["chat_ids"], list) else str(patch["chat_ids"]).replace(",", " ").split()
        clean["chat_ids"] = [str(x).strip() for x in ids if re.match(r"^-?\d{3,20}$", str(x).strip())][:20]
    await db.admin_settings.update_one({"type": SETTINGS_TYPE}, {"$set": {**clean, "type": SETTINGS_TYPE}}, upsert=True)
    return await get_settings(db)


async def recipients(db, s: Dict[str, Any]) -> List[str]:
    if s.get("chat_ids"):
        return list(s["chat_ids"])
    out = []
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "telegram_chat_id": 1, "telegram_id": 1}):
        c = u.get("telegram_chat_id") or u.get("telegram_id")
        if c and str(c) not in out:
            out.append(str(c))
    return out


async def send_report(db, s: Optional[Dict[str, Any]] = None, *, reason: str = "по расписанию") -> Dict[str, Any]:
    s = s or await get_settings(db)
    data = await groups(db, days=s["days"], min_users=s["min_users"])
    if s.get("only_new"):
        seen = (await db.admin_settings.find_one({"type": SETTINGS_TYPE}, {"_id": 0, "reported": 1}) or {}).get("reported") or []
        seen = set(seen)
        data["groups"] = [g for g in data["groups"] if g["ip_bidx"] not in seen]
    to = await recipients(db, s)
    if not to:
        return {"ok": False, "reason": "Нет получателей: укажите Telegram ID или привяжите Telegram к аккаунту администратора"}
    try:
        from telegram_bot import get_telegram_bot
        bot = get_telegram_bot()
    except Exception:
        bot = None
    if not bot:
        return {"ok": False, "reason": "Telegram-бот не настроен"}
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo(s["tz"]))
    accounts = {u["id"] for g in data["groups"] for u in g["users"]}
    caption = (f"🕵️ <b>Мульти-аккаунты по IP</b> · {now.strftime('%d.%m.%Y %H:%M')} ({reason})\n"
               f"За {s['days']} дн.: {len(data['groups'])} IP, {len(accounts)} аккаунтов"
               + (" (только новые)" if s.get("only_new") else "") + ".\nСписок — в файле (id, ник, IP).")
    fname = f"multi_accounts_{now.strftime('%Y-%m-%d_%H%M')}.csv"
    content = csv_report(data, s["tz"])
    sent = 0
    for chat in to:
        try:
            if await bot.send_document(chat, content, filename=fname, caption=caption, content_type="text/csv; charset=utf-8"):
                sent += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"multi-ip report to {chat}: {e}")
    if sent and s.get("only_new"):
        await db.admin_settings.update_one({"type": SETTINGS_TYPE},
                                           {"$addToSet": {"reported": {"$each": [g["ip_bidx"] for g in data["groups"]]}}})
    out = {"ok": sent > 0, "sent": sent, "recipients": len(to), "groups": len(data["groups"]), "accounts": len(accounts)}
    if not sent:
        out["reason"] = "Telegram не принял файл: получатель должен хотя бы раз написать боту /start, проверьте Telegram ID"
    return out


async def send_scheduled(db) -> Optional[Dict[str, Any]]:
    """Scheduler (every 5 min): once a day, at or after the time set in the admin."""
    s = await get_settings(db)
    if not s.get("enabled"):
        return None
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo(s["tz"]))
    hh, mm = [int(x) for x in s["time"].split(":")]
    due = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    today = now.date().isoformat()
    if now < due or s.get("last_sent_date") == today or now - due > timedelta(hours=3):
        return None
    r = await db.admin_settings.update_one({"type": SETTINGS_TYPE, "last_sent_date": {"$ne": today}},
                                           {"$set": {"last_sent_date": today}})
    if not r.modified_count:          # another worker already took it
        return None
    res = await send_report(db, s)
    await db.admin_settings.update_one({"type": SETTINGS_TYPE}, {"$set": {"last_result": {**res, "at": now.isoformat()}}})
    return res
