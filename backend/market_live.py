"""Live market for everyone, cheaply: the «Купить» list of the resource market is updated in every open app within
~2 seconds of any change (a player's lot, a purchase, a cancel, the City Market buying or selling) — without each
client polling the server.

How: every server process looks at the ACTIVE lots once every TICK seconds — one small indexed query (id + amount),
and only while somebody is connected to that process. If something changed, it pushes ONE small message with the diff
to the sockets of that process (the shared personal socket /api/ws/<user>, core/websocket.manager):

    {"type": "market_update", "removed": [id, …], "updated": [{"id", "amount"}, …], "added": [lot, …]}
    {"type": "market_update", "reload": true}            ← too many new lots at once: the app reloads the list once

The diff catches every way a lot changes (no hook is needed in the buy / list / cancel / City Market code), and works
with several server processes: each one serves its own sockets.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

TICK = 2.0                 # seconds between two looks at the market
MAX_ADDED = 40             # more new lots at once → «reload» instead of sending them all
QUERY = {"status": "active", "tutorial": {"$ne": True}}

_task: Optional[asyncio.Task] = None


def diff(prev: Dict[str, int], cur: Dict[str, int]) -> Dict[str, Any]:
    removed = [i for i in prev if i not in cur]
    added = [i for i in cur if i not in prev]
    updated = [{"id": i, "amount": a} for i, a in cur.items() if i in prev and prev[i] != a]
    return {"removed": removed, "added": added, "updated": updated}


async def snapshot(db) -> Dict[str, int]:
    out: Dict[str, int] = {}
    async for x in db.market_listings.find(QUERY, {"_id": 0, "id": 1, "amount": 1}):
        if x.get("id"):
            out[x["id"]] = int(x.get("amount") or 0)
    return out


async def run(db, manager, enrich: Optional[Callable[[List[Dict[str, Any]]], Awaitable[Any]]] = None, tick: float = TICK):
    prev: Optional[Dict[str, int]] = None
    while True:
        try:
            await asyncio.sleep(tick)
            if not getattr(manager, "active_connections", None):
                prev = None                                   # nobody to tell: no query at all
                continue
            cur = await snapshot(db)
            if prev is None:
                prev = cur                                    # the first look is the baseline
                continue
            d = diff(prev, cur)
            prev = cur
            if not (d["removed"] or d["added"] or d["updated"]):
                continue
            msg: Dict[str, Any] = {"type": "market_update", "removed": d["removed"], "updated": d["updated"], "added": []}
            if len(d["added"]) > MAX_ADDED:
                msg = {"type": "market_update", "reload": True}
            elif d["added"]:
                lots = await db.market_listings.find({"id": {"$in": d["added"]}, **QUERY}, {"_id": 0}).to_list(MAX_ADDED)
                if enrich:
                    try:
                        await enrich(lots)
                    except Exception as e:                    # a name lookup must never stop the update
                        logger.debug(f"market live enrich: {e}")
                msg["added"] = lots
            await manager.broadcast(msg)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"market live: {e}")
            prev = None


def start(db, manager, enrich=None) -> None:
    """Start the watcher of THIS process (idempotent)."""
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(run(db, manager, enrich))
