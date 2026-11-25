"""The seller's «resources sold» notification names the buyer: «@name купил …» or «Город купил …», in 9 languages."""
import asyncio
import os
import sys

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from core import sale_notify as sn  # noqa: E402


def test_player_buyer_is_named_and_city_has_its_own_title():
    t, b = sn.render("ru", city=False, buyer_name="An3412", amount=10.0, res="Металл", gross_ton=0.027, net_ton=0.02295)
    assert t == "💰 Ресурсы проданы на маркете"
    assert b.startswith("@An3412 купил 10 ед. «Металл» за 0.0270 GRAM (27 $CITY).")
    assert "Вам начислено после налога: 0.0230 GRAM (22.95 $CITY)." in b
    t, b = sn.render("ru", city=True, buyer_name=None, amount=10, res="Металл", gross_ton=0.027, net_ton=0.02295, to_bonus=True)
    assert t == "🏙 Город купил ваш лот" and b.startswith("Город купил 10 ед.") and "на бонусный баланс." in b


def test_every_language_and_the_credit_line():
    for lang in sn.LANGS:
        t, b = sn.render(lang, city=True, buyer_name=None, amount=20, res="R", gross_ton=0.05, net_ton=0.03, credit_ton=0.01)
        assert sn.CITY[lang] in b and "0.0500 GRAM" in b and "10 $CITY" in b and "{" not in b
        t2, b2 = sn.render(lang, city=False, buyer_name="", amount=20, res="R", gross_ton=0.05, net_ton=0.03)
        assert sn.SOMEONE[lang] in b2 and t2 != t


def test_notify_sale_sends_in_the_sellers_language(monkeypatch):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["s"]
        sent = []

        async def fake(db_, user, **kw):
            sent.append(kw)
        from core import notify
        monkeypatch.setattr(notify, "notify_user", fake)
        await sn.notify_sale(db, {"id": "u", "language": "de"}, city=True, buyer_name=None, amount=10, resource="cu",
                             gross_ton=0.027, net_ton=0.023)
        assert sent[0]["title"] == "🏙 Die Stadt hat dein Los gekauft" and sent[0]["message"].startswith("Die Stadt hat 10 Einh.")
        assert sent[0]["pretranslated"] is True and sent[0]["payload"]["buyer"] == "city"
    asyncio.run(go())
