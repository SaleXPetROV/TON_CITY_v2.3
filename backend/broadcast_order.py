"""Telegram broadcast: speed settings, recipient order from the previous broadcasts, and the after-send analysis.

Telegram lets a bot send about 30 messages a second in total (bots.faq). A send to a chat that blocked the bot is
refused, but it still takes a place in that budget — so a broadcast where half the chats blocked the bot delivered
only about half of the speed. Here every chat's last result is remembered (`tg_delivery`), and the next broadcast goes:

    1. new chats (never sent to) and chats that received the last broadcast,
    2. chats where the last send failed for another reason (network, Telegram error),
    3. chats that blocked the bot / were deleted — last, the most recently blocked first
       (someone who blocked once may come back; an account deleted long ago won't).

So everyone who can read the message gets it at full speed first, and the dead chats are tried at the end.

Paid broadcasts (Telegram's own feature, enabled in @BotFather): up to 1000 messages a second, 0.1 Star per message
over the free 30/s, the bot needs ≥ 100 000 Stars on its balance and ≥ 100 000 monthly users. Off by default.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

FREE_MAX = 30.0          # Telegram's free bulk limit, messages per second
PAID_MAX = 1000.0        # with paid broadcasts enabled in @BotFather
DEAD = ("blocked", "not_found")
GROUPS = ("new", "ok", "error", "blocked")   # sending order
GROUP_RANK = {g: i for i, g in enumerate(GROUPS)}


def _env_rate() -> float:
    try:
        return float(os.environ.get("BROADCAST_TG_PER_SEC") or FREE_MAX)
    except Exception:  # noqa: BLE001
        return FREE_MAX


DEFAULTS = {"tg_per_sec": None, "paid": False, "paid_per_sec": 100, "dead_last": True}


async def get_settings(db) -> Dict[str, Any]:
    doc = await db.admin_settings.find_one({"type": "broadcast_speed"}, {"_id": 0, "type": 0}) or {}
    s = {**DEFAULTS, **doc}
    if not s.get("tg_per_sec"):
        s["tg_per_sec"] = min(_env_rate(), FREE_MAX)
    return s


async def save_settings(db, body: Dict[str, Any]) -> Dict[str, Any]:
    s = await get_settings(db)
    if "tg_per_sec" in body:
        s["tg_per_sec"] = max(1.0, min(float(body["tg_per_sec"]), FREE_MAX))
    if "paid" in body:
        s["paid"] = bool(body["paid"])
    if "paid_per_sec" in body:
        s["paid_per_sec"] = max(FREE_MAX, min(float(body["paid_per_sec"]), PAID_MAX))
    if "dead_last" in body:
        s["dead_last"] = bool(body["dead_last"])
    await db.admin_settings.update_one({"type": "broadcast_speed"}, {"$set": {**s, "type": "broadcast_speed"}}, upsert=True)
    return s


def tg_rate(s: Dict[str, Any]) -> Tuple[float, bool]:
    """(messages per second, paid broadcast on)."""
    if s.get("paid"):
        return max(FREE_MAX, min(float(s.get("paid_per_sec") or 100), PAID_MAX)), True
    return max(1.0, min(float(s.get("tg_per_sec") or FREE_MAX), FREE_MAX)), False


async def ensure_indexes(db) -> None:
    try:
        await db.tg_delivery.create_index("chat_id", unique=True)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"tg_delivery index: {e}")


_OLD_DEAD = {"blocked_by_user", "deactivated", "no_access", "forbidden", "not_found", "blocked"}


async def history(db, chat_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """chat_id → {group, streak, state}: what happened to this chat in the previous broadcasts."""
    ids = [str(c) for c in chat_ids]
    out: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(ids), 1000):
        part = ids[i:i + 1000]
        async for d in db.tg_delivery.find({"chat_id": {"$in": part}}, {"_id": 0}):
            st = d.get("state")
            g = "ok" if st == "ok" else "blocked" if st in DEAD else "error"
            out[d["chat_id"]] = {"group": g, "streak": int(d.get("fail_streak") or 0), "state": st, "detail": d.get("detail")}
        # before this history existed, only failures were written to telegram_mappings — use them once
        missing = [c for c in part if c not in out]
        if missing:
            both = missing + [int(c) for c in missing if c.lstrip("-").isdigit()]   # old rows keep int ids
            async for m in db.telegram_mappings.find({"chat_id": {"$in": both}, "delivery_state": {"$in": list(_OLD_DEAD)}},
                                                     {"_id": 0, "chat_id": 1, "delivery_state": 1}):
                cid = str(m.get("chat_id"))
                if cid not in out:
                    out[cid] = {"group": "blocked", "streak": 1, "state": "blocked", "detail": m.get("delivery_state")}
    return out


def order(chat_ids: Iterable[str], hist: Dict[str, Dict[str, Any]], dead_last: bool = True) -> List[str]:
    ids = [str(c) for c in chat_ids]
    if not dead_last:
        return ids
    pos = {c: i for i, c in enumerate(ids)}

    def key(c):
        h = hist.get(c)
        if not h:
            return (0, 0, pos[c])
        g = GROUP_RANK[h["group"]]
        # new and «received last time» are one wave; among the dead, the freshly blocked first
        return (0 if g <= 1 else g, h["streak"] if h["group"] == "blocked" else 0, pos[c])
    return sorted(ids, key=key)


class Recorder:
    """Collects every chat's result and writes them to `tg_delivery` in batches."""

    def __init__(self, ann_id: Optional[str]):
        self.ann_id = ann_id
        self.buf: Dict[str, Tuple[str, Optional[str]]] = {}
        import asyncio as _asyncio
        self._lock = _asyncio.Lock()          # the once-a-second flush and the final one never write together

    def add(self, cid: str, state: str, detail: Optional[str] = None) -> None:
        self.buf[str(cid)] = (state, detail)

    async def flush(self, db) -> None:
        async with self._lock:
            await self._flush(db)

    async def _flush(self, db) -> None:
        if not self.buf:
            return
        from pymongo import UpdateOne
        items, self.buf = self.buf, {}
        now = datetime.now(timezone.utc).isoformat()
        ops = []
        for cid, (state, detail) in items.items():
            if state == "ok":
                ops.append(UpdateOne({"chat_id": cid}, {"$set": {"state": "ok", "detail": None, "last_ok_at": now,
                                                                 "fail_streak": 0, "last_ann": self.ann_id, "updated_at": now}},
                                     upsert=True))
            else:
                ops.append(UpdateOne({"chat_id": cid}, {"$set": {"state": state, "detail": detail, "last_fail_at": now,
                                                                 "last_ann": self.ann_id, "updated_at": now},
                                                        "$inc": {"fail_streak": 1}}, upsert=True))
        for i in range(0, len(ops), 500):
            try:
                await db.tg_delivery.bulk_write(ops[i:i + 500], ordered=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"tg_delivery write failed: {e}")


def new_analysis(hist: Dict[str, Dict[str, Any]], ordered: List[str]) -> Dict[str, Any]:
    groups = {g: {"total": 0, "sent": 0, "blocked": 0, "not_found": 0, "failed": 0} for g in GROUPS}
    for c in ordered:
        groups[(hist.get(c) or {}).get("group", "new")]["total"] += 1
    main = groups["new"]["total"] + groups["ok"]["total"] + groups["error"]["total"]
    return {"groups": groups, "main_total": main, "main_done": 0, "main_done_sec": None,
            "newly_blocked": 0, "came_back": 0, "new_blocked": 0, "rate_limited": 0,
            "duration_sec": None, "delivered_per_sec": None, "attempts_per_sec": None, "dead_share": None,
            "rate_start": None, "rate_end": None, "paid": False}


def note(an: Dict[str, Any], group: str, result: str) -> None:
    """result: sent | blocked | not_found | failed."""
    g = an["groups"][group]
    g[result] = g.get(result, 0) + 1
    if group == "ok" and result in DEAD:
        an["newly_blocked"] += 1
    elif group == "blocked" and result == "sent":
        an["came_back"] += 1
    elif group == "new" and result in DEAD:
        an["new_blocked"] += 1


def finish(an: Dict[str, Any], started: float, ended: float, attempts: int, sent: int) -> None:
    dur = max(0.001, ended - started)
    an["duration_sec"] = round(dur, 1)
    an["delivered_per_sec"] = round(sent / dur, 1)
    an["attempts_per_sec"] = round(attempts / dur, 1)
    dead = sum(an["groups"][g]["blocked"] + an["groups"][g]["not_found"] for g in GROUPS)
    an["dead_share"] = round(100.0 * dead / attempts, 1) if attempts else 0.0
