"""History: names of operation types — Russian in the code, other languages made by LibreTranslate once and cached."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import transaction_history as th  # noqa: E402
import translation_service as ts  # noqa: E402


def test_names_are_translated_once_by_libretranslate_and_cached():
    async def go():
        db = AsyncMongoMockClient()["t"]
        calls = []

        async def fake(text, target, source="en", protect_emoji=False):
            calls.append((text, target, source))
            return f"[{target}] {text}"
        o1, o2 = ts.libretranslate_configured, ts.translate_libre_protected
        ts.libretranslate_configured, ts.translate_libre_protected = (lambda: True), fake
        try:
            ru = await th.type_names(db, "ru")
            assert ru["supply_payment_out"] == "Оплата грузового маршрута (архив)" and not calls
            de = await th.type_names(db, "de", budget=1000)
            assert de["delivery_speedup"] == "[de] Ускорение доставки" and all(c[2] == "ru" for c in calls)
            n = len(calls)
            await th.type_names(db, "de", budget=1000)                      # cached: no new calls
            assert len(calls) == n
            th.TRANSACTION_TYPES["delivery_speedup"]["name"] = "Ускорение доставки грузовика"
            de2 = await th.type_names(db, "de", budget=1000)                # the Russian changed → translated again
            assert de2["delivery_speedup"] == "[de] Ускорение доставки грузовика" and len(calls) == n + 1
        finally:
            th.TRANSACTION_TYPES["delivery_speedup"]["name"] = "Ускорение доставки"
            ts.libretranslate_configured, ts.translate_libre_protected = o1, o2
    asyncio.run(go())


def test_without_libretranslate_the_russian_name_stays():
    async def go():
        db = AsyncMongoMockClient()["t"]
        o = ts.libretranslate_configured
        ts.libretranslate_configured = lambda: False
        try:
            fr = await th.type_names(db, "fr")
            assert fr["comeback_bonus"] == "Бонус за возвращение"
        finally:
            ts.libretranslate_configured = o
    asyncio.run(go())
