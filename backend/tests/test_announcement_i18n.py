"""Announcements are auto-translated (LibreTranslate) into every language the admin did not fill; the translations
are kept one day so a retried broadcast does not translate again."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
mongomock_motor = pytest.importorskip("mongomock_motor")
import announcement_i18n as ai  # noqa: E402
import translation_service as ts  # noqa: E402


def test_auto_translate_fills_every_language_and_caches(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["ann"]
    calls = []

    async def fake(text, target, source="en", **kw):
        calls.append((target, source))
        return f"[{target}] {text}"
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt")
    monkeypatch.setattr(ts, "translate_libre_protected", fake)
    ann = {"id": "a1", "title": "Обновление", "message": "Новые <b>игры</b>!", "lang": "all",
           "buttons": [{"text": "Играть", "url": "https://t.me/x"}],
           "translations": {"en": {"title": "Update", "message": "New games!", "buttons": []}}}
    out = asyncio.run(ai.auto_translate(db, ann))
    assert set(out) == set(ai.LANGS)
    assert out["en"]["message"] == "New games!"                       # the admin's own variant is kept
    assert out["de"]["message"] == "[de] New games!"                   # translated from the admin's English
    assert all(src == "en" for _, src in calls)
    n = len(calls)
    asyncio.run(ai.auto_translate(db, ann))                            # a retried broadcast: from the saved copy
    assert len(calls) == n
    # only the main text: the source language is detected (Cyrillic → ru), buttons translated too
    ann2 = {"id": "a2", "title": "Привет", "message": "Текст", "buttons": [{"text": "Играть", "url": "https://t.me/x"}]}
    out2 = asyncio.run(ai.auto_translate(db, ann2))
    assert out2["ru"]["message"] == "Текст" and out2["en"]["buttons"][0]["text"] == "[en] Играть"
    # one day later they are removed
    asyncio.run(db.announcement_translations.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}}))
    assert asyncio.run(ai.cleanup(db)) == 16


def test_without_libretranslate_nothing_changes(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["ann2"]
    monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
    assert asyncio.run(ai.auto_translate(db, {"id": "x", "message": "m"})) is None


def test_emoji_kept_in_translation(monkeypatch):
    """LibreTranslate drops emoji: they are protected, and if a placeholder is lost the text is translated piece by
    piece between the emoji — the button «🚀 Играть» stays «🚀 …» in every language."""
    import re
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt")

    async def engine_keeps_tags(text, target, source):          # keeps placeholders, drops raw emoji
        return ts.EMOJI_RE.sub("", text).replace("Играть", "Play").replace("станьте совладельцем", "become a co-owner")
    monkeypatch.setattr(ts, "_translate_libre", engine_keeps_tags)
    assert asyncio.run(ai._tr("🚀 Играть", "en", "ru")) == "🚀 Play"
    assert asyncio.run(ai._tr("💎 Founder Pass — станьте совладельцем! 👇", "en", "ru")) == \
        "💎 Founder Pass — become a co-owner! 👇"

    async def engine_drops_tags(text, target, source):          # loses every tag and every emoji
        out = re.sub(r"<b data-p=\"\d+\"></b>", "", ts.EMOJI_RE.sub("", text))
        return out.replace("Играть", "Play").replace("Купить", "Buy")
    monkeypatch.setattr(ts, "_translate_libre", engine_drops_tags)
    assert asyncio.run(ai._tr("🚀 Играть", "en", "ru")) == "🚀 Play"
    assert asyncio.run(ai._tr("Купить ✅ Играть 🇷🇺", "en", "ru")) == "Buy ✅ Play 🇷🇺"
