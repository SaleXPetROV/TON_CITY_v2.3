"""Screen texts: the server's Russian source matches the app's, LibreTranslate translates once, placeholders safe."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import translation_service as ts  # noqa: E402
import ui_i18n  # noqa: E402

FRONT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src", "i18n")


def test_the_server_has_the_apps_russian_texts():
    for f in os.listdir(FRONT):
        if f.endswith(".json"):
            app = json.load(open(os.path.join(FRONT, f), encoding="utf-8"))
            assert ui_i18n.sources()[f[:-5]] == app["ru"], f"run scripts/sync_ui_i18n.py ({f})"
            assert set(app["en"]) == set(app["ru"]), f


def test_libretranslate_once_and_again_only_when_the_russian_changes():
    async def go():
        db = AsyncMongoMockClient()["t"]
        calls = []

        async def fake(text, target, source="en", protect_emoji=False):
            calls.append(text)
            return f"<{target}>{text}"
        o1, o2 = ts.libretranslate_configured, ts.translate_libre_protected
        ts.libretranslate_configured, ts.translate_libre_protected = (lambda: True), fake
        try:
            b = await ui_i18n.bundle(db, "spot", "de", budget=1000)
            assert b["complete"] and b["texts"]["buy"] == "<de>Купить"
            n = len(calls)
            await ui_i18n.bundle(db, "spot", "de", budget=1000)
            assert len(calls) == n
            ru = await ui_i18n.bundle(db, "spot", "ru")
            assert ru["texts"]["buy"] == "Купить" and len(calls) == n
        finally:
            ts.libretranslate_configured, ts.translate_libre_protected = o1, o2
    asyncio.run(go())
