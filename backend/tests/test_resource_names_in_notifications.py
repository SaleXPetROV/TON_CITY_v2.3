"""Notifications name resources the way the game does and say WHICH contract they are about.

    cd backend && python -m pytest tests/test_resource_names_in_notifications.py -q

• «Цена на Охлаждать выросла…» — the price alert machine-translated the English word «Cooling»; it must read
  «Холод» (the in-game name) in every language.
• «Контракт #10706414 был мирно разорван» — the player could not tell which contract it was; the text now names
  the resource, the daily volume, the price and the partner.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")

from core.chest_notify import RES_NAMES  # noqa: E402
from core.notif_i18n import LANGS, NOTIF, resource_label  # noqa: E402


def run(c):
    return asyncio.run(c)


# ───────────── resource_label ─────────────
def test_resource_label_uses_in_game_names_in_every_language():
    from business_config import RESOURCE_TYPES
    for rid, meta in RESOURCE_TYPES.items():
        assert resource_label(rid, "ru", icon=False) == meta["name_ru"], rid
        for lang in LANGS:
            name = resource_label(rid, lang, icon=False)
            assert name and name != rid, (rid, lang)
    assert resource_label("cooling", "ru", icon=False) == "Холод"
    assert resource_label("cooling", "es", icon=False) == RES_NAMES["cooling"]["es"]
    assert resource_label("cooling", "id", icon=False) == "Cooling"          # no Indonesian name → English
    assert resource_label("cooling", "ru").endswith("Холод")                  # with the icon
    assert resource_label("unknown_res", "ru") == "unknown_res"


def test_contract_templates_exist_in_all_languages_with_the_same_placeholders():
    import string
    for key in [k for k in NOTIF if k.startswith("contract_")]:
        assert set(NOTIF[key]) == set(LANGS), key
        ref = {f for _, f, _, _ in string.Formatter().parse(NOTIF[key]["en"][1]) if f}
        assert {"resource", "partner", "cid"} <= ref, key
        for lang, (_t, body) in NOTIF[key].items():
            got = {f for _, f, _, _ in string.Formatter().parse(body) if f}
            assert got == ref, (key, lang)


# ───────────── smart price alert ─────────────
class _Sent:
    def __init__(self):
        self.calls = []

    async def __call__(self, db, user, title, message, **kw):
        self.calls.append({"title": title, "message": message, **kw})


async def _sn_world(monkeypatch, lang="ru"):
    import smart_notify as sn
    db = mongomock_motor.AsyncMongoMockClient()["sn_names"]
    sn.init(db)
    sent = _Sent()
    import core.notify
    monkeypatch.setattr(core.notify, "notify_user", sent)

    async def no_translator(word, lang):          # a known resource must never reach the machine translator
        raise AssertionError(f"machine translation of {word!r}")
    monkeypatch.setattr(sn, "_translate_word", no_translator)
    await db.users.insert_one({"id": "u1", "language": lang, "telegram_chat_id": "1", "telegram_notifications": True,
                               "notification_preferences": {"smart": {"quiet_enabled": False}}})
    return sn, sent


@pytest.mark.parametrize("vars_", [
    {"resource": "Cooling", "resource_id": "cooling"},   # what price_watch sends now
    {"resource": "Cooling"},                             # older callers: English name only
    {"resource": "cooling"},                             # or the id
])
def test_price_up_names_cooling_holod(monkeypatch, vars_):
    async def go():
        sn, sent = await _sn_world(monkeypatch, "ru")
        r = await sn.send("u1", "price_up", {**vars_, "change": 17, "old": 0.003, "new": 0.0035})
        assert r["sent"]
        for c in sent.calls:
            assert "Холод" in c["title"] and "Холод" in c["message"], c
            assert "Охлажд" not in c["title"] + c["message"]
    run(go())


def test_price_up_telegram_copy_in_another_language_is_named_too(monkeypatch):
    async def go():
        sn, sent = await _sn_world(monkeypatch, "ru")

        async def tg_lang(_user):
            return "es"
        monkeypatch.setattr(sn, "_tg_lang", tg_lang)
        await sn.send("u1", "price_up", {"resource": "Cooling", "resource_id": "cooling", "change": 17, "old": 1, "new": 1.2})
        app = [c for c in sent.calls if c.get("telegram") is False][0]
        tg = [c for c in sent.calls if c.get("in_app") is False][0]
        assert "Холод" in app["message"]
        assert RES_NAMES["cooling"]["es"] in tg["message"] and "Холод" not in tg["message"]
    run(go())


# ───────────── supply contracts ─────────────
class U:
    def __init__(self, id, username):
        self.id, self.username, self.display_name = id, username, username


async def _tender_world(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["tenders_names"]
    await db.users.insert_many([
        {"id": "buyer", "username": "Boris", "language": "ru", "balance_ton": 10.0, "frozen_city_for_tenders": 70.0},
        {"id": "seller", "username": "Anna", "language": "es", "balance_ton": 10.0, "frozen_city_for_tenders": 35.0},
    ])
    await db.tenders.insert_one({"id": "t1", "buyer_id": "buyer", "resource_type": "cooling", "status": "FILLED",
                                 "total_amount_needed": 20.0, "current_filled_amount": 20.0})
    await db.tender_contracts.insert_one({
        "id": "10706414-aaaa-bbbb-cccc-dddddddddddd", "tender_id": "t1", "buyer_id": "buyer", "buyer_username": "Boris",
        "seller_id": "seller", "seller_username": "Anna", "resource_type": "cooling", "tier": 1,
        "daily_amount": 20.0, "price_per_unit": 3.5, "status": "ACTIVE", "escrow_deposit": 35.0,
        "buyer_escrow_deposit": 70.0, "tax_rate": 0.15,
        "break_request": {"id": "br1", "requested_by": "seller", "requested_by_id": "seller", "status": "PENDING"},
    })
    import routes.tenders as T
    monkeypatch.setattr(T, "db", db)
    sent = []

    async def fake_notify(db_, user, title="", message="", **kw):
        u = user if isinstance(user, dict) else {"id": user}
        sent.append({"to": u.get("id"), "title": title, "message": message, **kw})
    import core.notify
    monkeypatch.setattr(core.notify, "notify_user", fake_notify)

    async def no_ws(*a, **k):
        return None
    monkeypatch.setattr(T, "_emit_ws", no_ws)
    return db, T, sent


CID = "10706414-aaaa-bbbb-cccc-dddddddddddd"


def test_mutual_break_says_which_resource_and_partner(monkeypatch):
    async def go():
        db, T, sent = await _tender_world(monkeypatch)
        assert (await T.accept_mutual_break(CID, current_user=U("buyer", "Boris")))["status"] == "broken_mutual"
        to_buyer = [x for x in sent if x["to"] == "buyer"][-1]
        to_seller = [x for x in sent if x["to"] == "seller"][-1]
        # the buyer (Russian): resource, volume, price, partner, and the number for support
        assert "Холод" in to_buyer["message"] and "20 ед./сутки" in to_buyer["message"]
        assert "3.50 $CITY" in to_buyer["message"] and "@Anna" in to_buyer["message"]
        assert "#10706414" in to_buyer["message"] and "по соглашению сторон" in to_buyer["title"]
        # the seller (Spanish) sees the Spanish in-game name and the buyer as the partner
        assert RES_NAMES["cooling"]["es"] in to_seller["message"] and "@Boris" in to_seller["message"]
        assert "cooling" not in to_buyer["message"] + to_seller["message"]
        assert to_buyer["payload"]["resource_type"] == "cooling"
        assert to_buyer["i18n_key"] == "contract_break_mutual"
        # money: both reserves unfrozen, nobody fined
        assert (await db.users.find_one({"id": "buyer"}))["frozen_city_for_tenders"] == 0
        assert (await db.users.find_one({"id": "seller"}))["frozen_city_for_tenders"] == 0
        assert (await db.users.find_one({"id": "buyer"}))["balance_ton"] == 10.0
    run(go())


def test_break_request_and_its_rejection_name_the_resource(monkeypatch):
    async def go():
        db, T, sent = await _tender_world(monkeypatch)
        await T.reject_mutual_break(CID, current_user=U("buyer", "Boris"))
        to_seller = [x for x in sent if x["to"] == "seller"][-1]
        assert RES_NAMES["cooling"]["es"] in to_seller["message"] and "@Boris" in to_seller["message"]

        class Req:
            reason = "mutual"
        await T.propose_mutual_break(CID, Req(), current_user=U("seller", "Anna"))
        to_buyer = [x for x in sent if x["to"] == "buyer"][-1]
        assert "Холод" in to_buyer["message"] and "@Anna" in to_buyer["message"]
        assert to_buyer["payload"]["kind"] == "break_request"                 # the accept / reject buttons stay
    run(go())


def test_timeout_break_is_not_called_a_manual_break(monkeypatch):
    async def go():
        db, T, sent = await _tender_world(monkeypatch)
        c = await db.tender_contracts.find_one({"id": CID}, {"_id": 0})
        await T._do_break(c, broken_by="seller", reason="pending_timeout")
        to_seller = [x for x in sent if x["to"] == "seller"][-1]               # culprit (Spanish)
        to_buyer = [x for x in sent if x["to"] == "buyer"][-1]                 # partner (Russian)
        assert "automáticamente" in to_seller["message"]
        assert "автоматически" in to_buyer["message"] and "Холод" in to_buyer["message"]
        assert "@Anna" in to_buyer["message"] and f"{T.PENDING_TIMEOUT_HOURS} ч" in to_buyer["message"]

        db2, T2, sent2 = await _tender_world(monkeypatch)
        c = await db2.tender_contracts.find_one({"id": CID}, {"_id": 0})
        await T2._do_break(c, broken_by="buyer", reason="manual")
        culprit = [x for x in sent2 if x["to"] == "buyer"][-1]
        assert "Вы в одностороннем порядке" in culprit["message"] and "Холод" in culprit["message"]
    run(go())


def test_pending_notice_names_the_resource_not_its_id(monkeypatch):
    async def go():
        db, T, sent = await _tender_world(monkeypatch)
        await db.users.update_one({"id": "seller"}, {"$set": {"resources": {"cooling": 0}}})
        c = await db.tender_contracts.find_one({"id": CID}, {"_id": 0})
        await T._process_tick(c)
        to_seller = [x for x in sent if x["to"] == "seller"][-1]
        assert "«Холод»" in to_seller["message"] and "cooling" not in to_seller["message"]
    run(go())
