"""Telegram broadcast order: chats that blocked the bot go last, results are remembered, analysis counts."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import broadcast_order as bo  # noqa: E402


def run(c):
    return asyncio.run(c)


def test_speed_settings_limits():
    async def go():
        db = AsyncMongoMockClient()["t"]
        s = await bo.get_settings(db)
        assert bo.tg_rate(s) == (30.0, False)
        s = await bo.save_settings(db, {"tg_per_sec": 80})
        assert s["tg_per_sec"] == 30.0                       # free limit of Telegram
        s = await bo.save_settings(db, {"tg_per_sec": 20})
        assert bo.tg_rate(s) == (20.0, False)
        s = await bo.save_settings(db, {"paid": True, "paid_per_sec": 5000})
        assert bo.tg_rate(s) == (1000.0, True)
        s = await bo.save_settings(db, {"paid_per_sec": 5})
        assert bo.tg_rate(s) == (30.0, True)
    run(go())


def test_order_and_memory():
    async def go():
        db = AsyncMongoMockClient()["t"]
        # an old failure from before the history existed (int chat id)
        await db.telegram_mappings.insert_one({"chat_id": 105, "delivery_state": "blocked_by_user"})
        chats = ["101", "102", "103", "104", "105", "106"]
        rec = bo.Recorder("a1")
        rec.add("101", "blocked", "blocked_by_user")
        rec.add("102", "ok")
        rec.add("103", "error")
        rec.add("104", "not_found")
        await rec.flush(db)
        rec.add("104", "not_found")                          # dead twice in a row
        await rec.flush(db)
        h = await bo.history(db, chats)
        assert h["101"]["group"] == "blocked" and h["101"]["streak"] == 1
        assert h["104"]["streak"] == 2
        assert h["102"]["group"] == "ok" and h["103"]["group"] == "error"
        assert h["105"]["group"] == "blocked"                # taken from telegram_mappings
        assert "106" not in h                                # new chat
        o = bo.order(chats, h)
        assert o[:2] == ["102", "106"]                       # received last time + new, in their own order
        assert o[2] == "103"                                 # other error
        assert set(o[3:5]) == {"101", "105"} and o[5] == "104"   # dead last; dead twice — the very last
        assert bo.order(chats, h, dead_last=False) == chats

        # came back: blocked chat received this time
        rec.add("101", "ok")
        await rec.flush(db)
        d = await db.tg_delivery.find_one({"chat_id": "101"})
        assert d["state"] == "ok" and d["fail_streak"] == 0

        an = bo.new_analysis(h, o)
        assert an["main_total"] == 3 and an["groups"]["blocked"]["total"] == 3
        bo.note(an, "ok", "blocked"); bo.note(an, "blocked", "sent"); bo.note(an, "new", "not_found"); bo.note(an, "ok", "sent")
        assert an["newly_blocked"] == 1 and an["came_back"] == 1 and an["new_blocked"] == 1
        bo.finish(an, 0.0, 2.0, attempts=4, sent=2)
        assert an["delivered_per_sec"] == 1.0 and an["attempts_per_sec"] == 2.0 and an["dead_share"] == 50.0
    run(go())
