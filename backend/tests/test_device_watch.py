"""Multi-accounts by device (device_watch.py): the marks from the request, the groups for the admin, the caps."""
import asyncio
from datetime import datetime, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
import device_watch as dw  # noqa: E402


def run(c):
    return asyncio.run(c)


def _scope(**h):
    return {"type": "http", "headers": [(k.encode(), v.encode()) for k, v in h.items()]}


def test_marks_are_read_and_checked():
    did, fp, ua = dw.from_scope(_scope(**{"x-device-id": "3f1c2a9e-1111-4b2b-9c3d-abcdefabcdef", "x-device-fp": "a1b2c3d4e5f6a7b8",
                                          "user-agent": "Mozilla/5.0 (Linux; Android 14; wv) Telegram"}))
    assert did and fp and "Android" in ua
    assert dw.from_scope(_scope(**{"x-device-id": "<script>"}))[0] is None       # junk is ignored
    assert dw.label("Mozilla/5.0 (Linux; Android 14; SM-A515F; wv) AppleWebKit Chrome") == "Android 14 · Telegram"


def test_groups_and_same_device_users():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["d"]
        now = datetime.now(timezone.utc)
        for uid in ("a", "b", "c"):
            await db.users.insert_one({"id": uid, "username": uid})
        h = dw._hash("id", "device-one-000000")
        for uid in ("a", "b"):
            await db.user_devices.insert_one({"user_id": uid, "kind": "id", "dev": h, "last_seen": now, "first_seen": now,
                                              "hits": 3, "label": "Android 14 · Telegram"})
        await db.user_devices.insert_one({"user_id": "c", "kind": "id", "dev": dw._hash("id", "other-device-00"),
                                          "last_seen": now, "first_seen": now, "hits": 1})
        g = await dw.groups(db)
        assert g["totals"]["groups"] == 1 and {u["id"] for u in g["groups"][0]["users"]} == {"a", "b"}
        assert await dw.same_device_users(db, "a") == {"a", "b"}
        assert await dw.same_device_users(db, "c") == {"c"}
        await db.user_devices_ignored.insert_one({"dev": h, "note": "семья"})
        assert (await dw.groups(db))["totals"]["groups"] == 0
        assert await dw.same_device_users(db, "a") == {"a"}           # «не мульти» also frees the caps
        assert dw.csv_report(await dw.groups(db, include_ignored=True)).startswith("﻿".encode())
    run(go())


def test_the_city_market_caps_count_one_device_as_one_player():
    async def go():
        import market_maker as mm
        db = mongomock_motor.AsyncMongoMockClient()["d2"]
        now = datetime.now(timezone.utc)
        h = dw._hash("id", "device-one-000000")
        for uid in ("a", "b"):
            await db.user_devices.insert_one({"user_id": uid, "kind": "id", "dev": h, "last_seen": now})
        cache = {}
        assert await mm.device_group(db, "b", cache) == await mm.device_group(db, "a", {}) == "a"
    run(go())
