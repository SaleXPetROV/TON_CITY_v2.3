"""Мульти-аккаунты по устройству (the IP report's twin: ip_watch.py).

The app sends two device marks with every API request (frontend/src/lib/deviceId.js):
  X-Device-Id — a random id made once and kept in the app's storage on that device (localStorage + cookie). Accounts
                switched in the same Telegram app / browser share it → a strong sign of one person.
  X-Device-Fp — the FingerprintJS hash of the device: survives a cleared storage, but identical phone models may share
                it → a weaker sign (shown separately, never used for the caps).
Every signed-in request leaves (player, kind, hash of the mark) in db.user_devices — at most once per 15 minutes per
pair, written in the background (the game never waits). Only a SHA-256 of the mark is kept, plus a rough device label
(«Android · Telegram»), so nothing here identifies a person by itself.

  touch(db, user_doc) — from ip_watch.guard (every «who is this player» dependency)
  groups(db, …)       — devices used by 2+ accounts in the last N days (ignored devices left out)
  csv_report(groups)  — the file; also sent with the daily multi-account report (ip_watch.send_report)
  same_device_users   — the accounts sharing a device id with a player (market_maker.device_group: one player for caps)

Admin (Russian): Мульти-аккаунты → «Общее устройство» — groups, block selected, «не мульти», CSV.
"""
import asyncio
import csv
import hashlib
import io
import logging
import re
import time
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEVICE_ID: ContextVar[Optional[str]] = ContextVar("device_id", default=None)
DEVICE_FP: ContextVar[Optional[str]] = ContextVar("device_fp", default=None)
DEVICE_UA: ContextVar[Optional[str]] = ContextVar("device_ua", default=None)
THROTTLE_S = 15 * 60
KINDS = ("id", "fp")
_seen: Dict[tuple, float] = {}
_tasks: set = set()
_OK = re.compile(r"^[A-Za-z0-9_\-]{8,80}$")


def from_scope(scope) -> None:
    """Called by ip_watch.ClientIPMiddleware for every request: read the device headers (never trusted for anything
    but this report — a player can send anything, so they only ever ADD to the suspicion)."""
    h = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
    did, fp = (h.get("x-device-id") or "").strip(), (h.get("x-device-fp") or "").strip()
    return (did if _OK.match(did) else None, fp if _OK.match(fp) else None, (h.get("user-agent") or "")[:300])


def _hash(kind: str, v: str) -> str:
    return hashlib.sha256(f"gc-device:{kind}:{v}".encode()).hexdigest()[:32]


def label(ua: str) -> str:
    """A rough, non-identifying device label from the user agent."""
    u = ua or ""
    os_ = ("iOS" if re.search(r"iPhone|iPad|iPod", u) else "Android" if "Android" in u else "Windows" if "Windows" in u
           else "macOS" if "Mac OS" in u else "Linux" if "Linux" in u else "—")
    m = re.search(r"Android (\d+)", u) or re.search(r"OS (\d+)_", u)
    if m and os_ in ("Android", "iOS"):
        os_ += f" {m.group(1)}"
    app = ("Telegram" if re.search(r"Telegram|TgWebView|wv\)", u) else "Chrome" if "Chrome" in u
           else "Safari" if "Safari" in u else "Firefox" if "Firefox" in u else "")
    return f"{os_} · {app}" if app else os_


def touch(db, user_doc: Dict[str, Any]) -> None:
    """Remember (player, device) of the current request. Never raises, never blocks the request."""
    try:
        uid = (user_doc or {}).get("id")
        if not uid:
            return
        marks = [("id", DEVICE_ID.get()), ("fp", DEVICE_FP.get())]
        now = time.time()
        todo = []
        for kind, v in marks:
            if not v:
                continue
            h = _hash(kind, v)
            k = (uid, kind, h)
            if now - _seen.get(k, 0) < THROTTLE_S:
                continue
            _seen[k] = now
            todo.append((kind, h))
        if not todo:
            return
        if len(_seen) > 200000:
            for kk in [x for x, t in _seen.items() if now - t > THROTTLE_S]:
                _seen.pop(kk, None)
        t = asyncio.get_running_loop().create_task(_write(db, uid, (user_doc or {}).get("username"), todo,
                                                          label(DEVICE_UA.get() or "")))
        _tasks.add(t)
        t.add_done_callback(_tasks.discard)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"device_watch touch: {e}")


async def _write(db, uid: str, username: Optional[str], todo: List[tuple], dev_label: str) -> None:
    now = datetime.now(timezone.utc)
    for kind, h in todo:
        try:
            await db.user_devices.update_one(
                {"user_id": uid, "kind": kind, "dev": h},
                {"$set": {"username": username, "last_seen": now, "label": dev_label},
                 "$setOnInsert": {"first_seen": now}, "$inc": {"hits": 1}},
                upsert=True)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"device_watch write: {e}")


async def ensure_indexes(db) -> None:
    try:
        await db.user_devices.create_index([("user_id", 1), ("kind", 1), ("dev", 1)], unique=True, name="user_dev")
        await db.user_devices.create_index([("dev", 1), ("last_seen", -1)], name="dev_last_seen")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"device_watch indexes: {e}")


async def same_device_users(db, uid: str) -> Set[str]:
    """Accounts sharing an app-storage device id with `uid` (the strong mark only), the player included."""
    devs = await db.user_devices.distinct("dev", {"user_id": uid, "kind": "id"})
    if not devs:
        return {uid}
    ignored = set(await db.user_devices_ignored.distinct("dev", {"dev": {"$in": devs}}))
    devs = [d for d in devs if d not in ignored]
    if not devs:
        return {uid}
    return set(await db.user_devices.distinct("user_id", {"kind": "id", "dev": {"$in": devs}})) | {uid}


def _iso(v) -> Optional[str]:
    if not v:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


async def groups(db, days: int = 30, min_users: int = 2, include_ignored: bool = False, q: str = "",
                 kind: str = "all") -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    ignored = {d["dev"]: d async for d in db.user_devices_ignored.find({}, {"_id": 0})}
    flt: Dict[str, Any] = {"last_seen": {"$gte": since}}
    if kind in KINDS:
        flt["kind"] = kind
    by_dev: Dict[str, Dict[str, Any]] = {}
    async for r in db.user_devices.find(flt, {"_id": 0}):
        g = by_dev.setdefault(r["dev"], {"dev": r["dev"], "kind": r.get("kind") or "id", "rows": []})
        g["rows"].append(r)
    out: List[Dict[str, Any]] = []
    uids: set = set()
    for d, g in by_dev.items():
        users = {r["user_id"] for r in g["rows"]}
        if len(users) < max(2, int(min_users)):
            continue
        if d in ignored and not include_ignored:
            continue
        g["user_ids"] = users
        uids |= users
        out.append(g)
    docs = {u["id"]: u async for u in db.users.find(
        {"id": {"$in": list(uids)}},
        {"_id": 0, "id": 1, "username": 1, "is_blocked": 1, "block_reason": 1, "created_at": 1, "is_admin": 1,
         "balance_ton": 1, "bonus_balance": 1})} if uids else {}
    shared: Dict[str, int] = {}
    for g in out:
        for u in g["user_ids"]:
            shared[u] = shared.get(u, 0) + 1
    res = []
    ql = (q or "").strip().lower()
    for g in out:
        rows = sorted(g["rows"], key=lambda r: r.get("last_seen") or since, reverse=True)
        users = []
        for r in rows:
            d = docs.get(r["user_id"]) or {}
            users.append({
                "id": r["user_id"], "username": d.get("username") or r.get("username") or "—",
                "blocked": bool(d.get("is_blocked")), "block_reason": d.get("block_reason"), "admin": bool(d.get("is_admin")),
                "created_at": _iso(d.get("created_at")),
                "balance_city": round((float(d.get("balance_ton") or 0) + float(d.get("bonus_balance") or 0)) * 1000, 2),
                "first_seen": _iso(r.get("first_seen")), "last_seen": _iso(r.get("last_seen")),
                "hits": int(r.get("hits") or 0), "label": r.get("label") or "", "shared_ips": shared.get(r["user_id"], 1)})
        labels = sorted({u["label"] for u in users if u["label"]})
        name = f"Устройство {g['dev'][:8]}"
        if ql and ql not in name.lower() and ql not in g["dev"] and not any(
                ql in (u["username"] or "").lower() or ql in u["id"].lower() for u in users):
            continue
        res.append({"ip": name, "ip_bidx": g["dev"], "dev": g["dev"], "kind": g["kind"], "labels": labels,
                    "count": len(g["user_ids"]), "blocked": sum(1 for u in users if u["blocked"]),
                    "last_seen": users[0]["last_seen"] if users else None, "users": users,
                    "ignored": g["dev"] in ignored, "note": (ignored.get(g["dev"]) or {}).get("note")})
    res.sort(key=lambda g: g["last_seen"] or "", reverse=True)
    res.sort(key=lambda g: (0 if g["kind"] == "id" else 1, -g["count"]))      # the strong mark first, then the biggest
    accounts = {u["id"] for g in res for u in g["users"]}
    return {"days": days, "min_users": min_users, "groups": res, "totals": {
        "groups": len(res), "accounts": len(accounts),
        "blocked": len({u["id"] for g in res for u in g["users"] if u["blocked"]}),
        "tracked_pairs": await db.user_devices.count_documents({"last_seen": {"$gte": since}}),
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
    w.writerow(["Группа", "Устройство", "Признак", "Тип устройства", "ID игрока", "Ник", "Аккаунтов на устройстве",
                "Заблокирован", f"Последний вход ({tz})", "Действий"])
    for i, g in enumerate(data.get("groups") or [], 1):
        sign = "общее хранилище приложения" if g["kind"] == "id" else "одинаковый отпечаток"
        for u in g["users"]:
            w.writerow([i, g["dev"][:12], sign, u.get("label") or "", u["id"], u["username"], g["count"],
                        "да" if u["blocked"] else "нет", when(u.get("last_seen")), u["hits"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")
