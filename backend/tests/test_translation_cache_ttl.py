"""LibreTranslate cache: one-off texts (sums, names) live 10 minutes, repeating texts are kept; old rows purged once."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import translation_service as ts  # noqa: E402
from core import notify  # noqa: E402


def run(c):
    return asyncio.run(c)


@pytest.fixture
def lt(monkeypatch):
    calls = []

    async def fake(text, target, source="auto"):
        calls.append(text)
        return f"[{target}] {text}"
    monkeypatch.setattr(ts, "translate_text", fake)
    monkeypatch.setattr(ts, "translation_configured", lambda: True)
    return calls


def test_one_off_text_expires_and_is_purged(lt):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["tc"]
        msg = "@An3412 купил 10 ед. за 27 $CITY"
        assert notify.one_off_ttl(msg) == 10
        assert await ts.translate_cached(db, msg, "en", "ru", ttl_minutes=10) == f"[en] {msg}"
        await ts.translate_cached(db, msg, "en", "ru", ttl_minutes=10)       # a broadcast: translated once
        assert len(lt) == 1
        row = await db.translation_cache.find_one({})
        assert row["keep"] is False and row.get("expires_at")
        assert await ts.purge_expired(db) == 0                                # still fresh
        await db.translation_cache.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}})
        assert await ts.purge_expired(db) == 1 and await db.translation_cache.count_documents({}) == 0
    run(go())


def test_repeating_text_is_kept_and_never_downgraded(lt):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["tc"]
        title = "Предложение отклонено"
        assert notify.one_off_ttl(title) is None
        await ts.translate_cached(db, title, "de", "ru")
        await ts.translate_cached(db, title, "de", "ru", ttl_minutes=10)     # a one-off use of a kept text
        row = await db.translation_cache.find_one({})
        assert row["keep"] is True and "expires_at" not in row and len(lt) == 1
        await db.translation_cache.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)}})
        assert await ts.purge_expired(db) == 0
    run(go())


def test_legacy_rows_purged_once_other_kinds_kept(lt):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["tc"]
        await db.translation_cache.insert_many([{"_id": "a", "text": "x"}, {"_id": "b", "text": "y"},
                                                {"kind": "lt_msg", "src": "s", "lang": "de", "text": "z"}])
        assert await ts.purge_legacy_once(db) == 2
        await db.translation_cache.insert_one({"_id": "c", "text": "new"})
        assert await ts.purge_legacy_once(db) == 0                             # only once
        assert await db.translation_cache.count_documents({}) == 2
    run(go())
