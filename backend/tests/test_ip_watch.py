"""Multi-accounts by shared IP: IP detection, grouping, CSV, report settings and the daily schedule.
No network, no database server (mongomock_motor)."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import ip_watch  # noqa: E402
from core import pii  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def _scope(headers=None, peer="10.0.0.5"):
    return {"type": "http", "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()], "client": (peer, 1234)}


def test_ip_detection_prefers_trusted_headers():
    assert ip_watch._ip_from_scope(_scope({"cf-connecting-ip": "8.8.8.8", "x-real-ip": "1.1.1.1"})) == "8.8.8.8"
    assert ip_watch._ip_from_scope(_scope({"x-real-ip": "1.1.1.1", "x-forwarded-for": "9.9.9.9"})) == "1.1.1.1"
    # the client put a fake address on the left; nginx appended the real one on the right
    assert ip_watch._ip_from_scope(_scope({"x-forwarded-for": "9.9.9.9, 77.88.55.60"})) == "77.88.55.60"
    # inner proxy (private) on the right → the public one before it
    assert ip_watch._ip_from_scope(_scope({"x-forwarded-for": "77.88.55.60, 172.18.0.2"})) == "77.88.55.60"
    assert ip_watch._ip_from_scope(_scope({"x-forwarded-for": "garbage"}, peer="5.6.7.8")) == "5.6.7.8"
    assert ip_watch._ip_from_scope(_scope({}, peer="127.0.0.1")) == "127.0.0.1"


def test_blocked_request_paths():
    for p, blocked in [("/api/auth/me", False), ("/api/support/chat", False), ("/api/health", False),
                       ("/api/businesses", True), ("/api/market/buy", True)]:
        t = ip_watch.REQUEST_PATH.set(p)
        try:
            assert ip_watch.blocked_request() is blocked, p
        finally:
            ip_watch.REQUEST_PATH.reset(t)


async def _db_with_rows():
    db = AsyncMongoMockClient()["t"]
    now = datetime.now(timezone.utc)
    await db.users.insert_many([
        {"id": "u1", "username": "alpha", "created_at": "2026-10-01T00:00:00+00:00", "balance_ton": 1.5},
        {"id": "u2", "username": "beta", "created_at": "2026-10-05T00:00:00+00:00", "is_blocked": True},
        {"id": "u3", "username": "gamma"},
        {"id": "u4", "username": "solo"},
        {"id": "adm", "username": "boss", "is_admin": True, "telegram_chat_id": 555000},
    ])
    for uid, ip, ago in [("u1", "77.88.55.60", 1), ("u2", "77.88.55.60", 2), ("u3", "77.88.55.60", 3),
                         ("u1", "5.6.7.8", 1), ("u3", "5.6.7.8", 1), ("u4", "9.9.9.9", 1),
                         ("u4", "4.4.4.4", 60)]:   # old row — outside a 30-day window
        await ip_watch._write(db, uid, None, ip)
        await db.user_ips.update_one({"user_id": uid, "ip_bidx": pii.bidx(ip)},
                                     {"$set": {"last_seen": now - timedelta(days=ago)}})
    return db


def test_groups_and_csv():
    async def go():
        db = await _db_with_rows()
        data = await ip_watch.groups(db, days=30, min_users=2)
        ips = [g["ip"] for g in data["groups"]]
        assert ips == ["77.88.55.60", "5.6.7.8"]            # biggest group first; single-account IPs skipped
        g = data["groups"][0]
        assert g["count"] == 3 and g["blocked"] == 1
        names = {u["username"] for u in g["users"]}
        assert names == {"alpha", "beta", "gamma"}
        u1 = next(u for u in g["users"] if u["id"] == "u1")
        assert u1["shared_ips"] == 2 and u1["balance_city"] == 1500.0
        assert data["totals"]["accounts"] == 3

        assert [g["ip"] for g in (await ip_watch.groups(db, days=30, min_users=3))["groups"]] == ["77.88.55.60"]
        assert [g["ip"] for g in (await ip_watch.groups(db, q="gamma"))["groups"]] == ["77.88.55.60", "5.6.7.8"]
        assert [g["ip"] for g in (await ip_watch.groups(db, q="5.6.7"))["groups"]] == ["5.6.7.8"]

        await db.user_ips_ignored.insert_one({"ip_bidx": g["ip_bidx"], "note": "семья"})
        assert [x["ip"] for x in (await ip_watch.groups(db))["groups"]] == ["5.6.7.8"]
        withign = await ip_watch.groups(db, include_ignored=True)
        assert any(x["ignored"] and x["note"] == "семья" for x in withign["groups"])

        csv = ip_watch.csv_report(withign, "Europe/Moscow").decode("utf-8")
        assert "Последний вход (Europe/Moscow)" in csv
        assert csv.startswith("﻿Группа;IP;ID игрока;Ник")
        assert "77.88.55.60;u2;beta;3;да" in csv
        assert csv.count("\n") == 1 + 5
    run(go())


def test_settings_validation():
    async def go():
        db = AsyncMongoMockClient()["t"]
        s = await ip_watch.save_settings(db, {"enabled": True, "time": "8:30", "tz": "Europe/Minsk", "days": 500,
                                              "min_users": 1, "chat_ids": "123456, -100987654, abc, 12"})
        assert s["enabled"] and s["time"] == "8:30" and s["tz"] == "Europe/Minsk"
        assert s["days"] == 90 and s["min_users"] == 2
        assert s["chat_ids"] == ["123456", "-100987654"]
        with pytest.raises(ValueError):
            await ip_watch.save_settings(db, {"time": "25:00"})
        with pytest.raises(Exception):
            await ip_watch.save_settings(db, {"tz": "Mars/Base"})
        assert await ip_watch.recipients(db, s) == ["123456", "-100987654"]
        await db.users.insert_one({"id": "a", "is_admin": True, "telegram_chat_id": 42})
        assert await ip_watch.recipients(db, {**s, "chat_ids": []}) == ["42"]
    run(go())


class _Bot:
    def __init__(self):
        self.sent = []

    async def send_document(self, chat, content, filename="", caption="", content_type=""):
        self.sent.append((chat, filename, content))
        return True


def test_scheduled_sends_once_a_day(monkeypatch):
    bot = _Bot()
    import types
    monkeypatch.setitem(sys.modules, "telegram_bot", types.SimpleNamespace(get_telegram_bot=lambda: bot))

    async def go():
        db = await _db_with_rows()
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        # not enabled → nothing
        assert await ip_watch.send_scheduled(db) is None
        # time is later today → nothing yet
        later = (now + timedelta(hours=1)).strftime("%H:%M")
        if (now + timedelta(hours=1)).date() == now.date():
            await ip_watch.save_settings(db, {"enabled": True, "time": later, "chat_ids": "123456"})
            assert await ip_watch.send_scheduled(db) is None
        # time has passed (but within 3 h) → one file, then not again today
        earlier = now - timedelta(minutes=10)
        if earlier.date() == now.date():
            await ip_watch.save_settings(db, {"enabled": True, "time": earlier.strftime("%H:%M"), "chat_ids": "123456"})
            r = await ip_watch.send_scheduled(db)
            assert r and r["ok"] and r["groups"] == 2 and r["accounts"] == 3
            assert bot.sent[0][0] == "123456" and bot.sent[0][1].endswith(".csv")
            assert "77.88.55.60" in bot.sent[0][2].decode("utf-8")
            assert await ip_watch.send_scheduled(db) is None
            assert len(bot.sent) == 1
            st = await ip_watch.get_settings(db)
            assert st["last_result"]["ok"] and st["last_sent_date"] == now.date().isoformat()
        # only_new: IPs already reported are skipped next time
        await ip_watch.save_settings(db, {"only_new": True})
        r1 = await ip_watch.send_report(db, reason="вручную")
        r2 = await ip_watch.send_report(db, reason="вручную")
        assert r1["groups"] == 2 and r2["groups"] == 0
    run(go())


def test_naive_times_are_utc():
    naive = datetime(2026, 11, 13, 18, 41)
    assert ip_watch._iso(naive) == "2026-11-13T18:41:00+00:00"
    data = {"groups": [{"ip": "1.1.1.1", "count": 2, "users": [
        {"id": "a", "username": "x", "blocked": False, "last_seen": ip_watch._iso(naive), "hits": 1}]}]}
    assert "2026-11-13 21:41" in ip_watch.csv_report(data, "Europe/Moscow").decode("utf-8")
