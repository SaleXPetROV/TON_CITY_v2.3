"""Tender offers that nobody answers: withdraw, reminders (2 h, then every 12 h), expiry after 72 h.

The seller could not take an unanswered offer back (the API even told them to «withdraw it»); offers could wait
forever. Now: the author withdraws (offer or change request), the side that must answer gets one grouped reminder
in its own language with an «Open offers» button, and after 72 h the offer closes and the author is told.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import tender_reminders as tr  # noqa: E402


def run(c):
    return asyncio.run(c)


def ago(h):
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()


class U:  # the part of core.models.User the endpoints read
    def __init__(self, id, username):
        self.id, self.username, self.display_name = id, username, username


async def world(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["tenders"]
    await db.users.insert_many([
        {"id": "buyer", "username": "Boris", "language": "ru", "telegram_chat_id": "1", "balance_ton": 10.0},
        {"id": "seller", "username": "Anna", "language": "es", "telegram_chat_id": "2", "balance_ton": 10.0},
        {"id": "seller2", "username": "Ivan", "language": "en", "balance_ton": 10.0},
    ])
    await db.game_settings.insert_one({"type": "telegram_settings", "app_url": "https://gram.example"})
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

    async def base(_db):
        return "https://t.me/GramCityBot/app"
    import core.ref_links
    monkeypatch.setattr(core.ref_links, "miniapp_base", base)
    return db, T, sent


def offer(id, seller="seller", created=None, status="PROPOSED", **kw):
    return {"id": id, "tender_id": "t1", "buyer_id": "buyer", "buyer_username": "Boris", "seller_id": seller,
            "seller_username": {"seller": "Anna", "seller2": "Ivan"}[seller], "resource_type": "energy", "tier": 1,
            "daily_amount": 100.0, "price_per_unit": 0.25, "status": status, "escrow_deposit": 0.0,
            "buyer_escrow_deposit": 0.0, "created_at": created or ago(0), **kw}


def test_seller_withdraws_an_unanswered_offer_and_nobody_else_can(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        await db.tender_contracts.insert_one(offer("c1"))
        with pytest.raises(Exception) as e:
            await T.withdraw_offer("c1", current_user=U("buyer", "Boris"))
        assert getattr(e.value, "status_code", None) == 403
        r = await T.withdraw_offer("c1", current_user=U("seller", "Anna"))
        assert r["status"] == "withdrawn"
        c = await db.tender_contracts.find_one({"id": "c1"})
        assert c["status"] == "WITHDRAWN"
        # no money moved, the buyer got an in-app notice only (no Telegram), in Russian
        assert (await db.users.find_one({"id": "seller"}))["balance_ton"] == 10.0
        n = [x for x in sent if x["to"] == "buyer"][-1]
        assert n["telegram"] is False and "отозвал" in n["message"] and "Anna" in n["message"]
        # a second withdraw / the buyer's accept now say why, in the player's language
        with pytest.raises(Exception) as e:
            await T.withdraw_offer("c1", current_user=U("seller", "Anna"))
        assert e.value.status_code == 409 and "retiró" in e.value.detail      # seller is Spanish
        with pytest.raises(Exception) as e:
            await T.accept_offer("c1", current_user=U("buyer", "Boris"))
        assert e.value.status_code == 409 and "отозвал" in e.value.detail
        assert (await db.users.find_one({"id": "buyer"})).get("frozen_city_for_tenders", 0) == 0
    run(go())


def test_accept_after_withdraw_race_freezes_nothing(monkeypatch):
    """The offer is withdrawn between the buyer's checks and the activation: nothing is frozen."""
    async def go():
        db, T, sent = await world(monkeypatch)
        await db.tender_contracts.insert_one(offer("c1"))
        real = T._user_by_id

        async def racing(uid):
            u = await real(uid)
            if uid == "seller":       # the seller withdraws while the buyer's accept is validating
                await db.tender_contracts.update_one({"id": "c1"}, {"$set": {"status": "WITHDRAWN"}})
            return u
        monkeypatch.setattr(T, "_user_by_id", racing)
        with pytest.raises(Exception) as e:
            await T.accept_offer("c1", current_user=U("buyer", "Boris"))
        assert e.value.status_code == 409
        for uid in ("buyer", "seller"):
            assert float((await db.users.find_one({"id": uid})).get("frozen_city_for_tenders", 0) or 0) == 0
    run(go())


def test_author_withdraws_a_change_request(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        am = {"id": "a1", "proposed_by": "seller", "proposed_by_id": "seller", "proposed_at": ago(1), "status": "PENDING",
              "new_daily_amount": 200.0, "new_price_per_unit": 0.3, "old_daily_amount": 100.0}
        await db.tender_contracts.insert_one(offer("c1", status="ACTIVE", pending_amendment=am))
        with pytest.raises(Exception) as e:        # the other side cannot withdraw it
            await T.withdraw_amendment("c1", "a1", current_user=U("buyer", "Boris"))
        assert e.value.status_code == 409
        await T.withdraw_amendment("c1", "a1", current_user=U("seller", "Anna"))
        c = await db.tender_contracts.find_one({"id": "c1"})
        assert c["pending_amendment"]["status"] == "WITHDRAWN" and c["status"] == "ACTIVE"
        assert any(x["to"] == "buyer" and "изменить контракт" in x["message"] for x in sent)
        with pytest.raises(Exception) as e:        # accepting a withdrawn change request applies nothing
            await T.accept_amendment("c1", "a1", current_user=U("buyer", "Boris"))
        assert e.value.status_code == 409
        assert (await db.tender_contracts.find_one({"id": "c1"}))["daily_amount"] == 100.0
    run(go())


def test_reminder_after_2h_grouped_in_the_players_language_then_not_before_12h(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        await db.tender_contracts.insert_many([offer("fresh", created=ago(0.5))])
        await tr.run(db)
        assert not [x for x in sent if x.get("type_key") == "tender_offers_pending"]       # < 2 h: nothing yet

        await db.tender_contracts.insert_many([offer("old1", created=ago(3)), offer("old2", seller="seller2", created=ago(5))])
        await tr.run(db)
        rem = [x for x in sent if x.get("type_key") == "tender_offers_pending"]
        assert len(rem) == 1 and rem[0]["to"] == "buyer"
        msg = rem[0]["message"]
        assert "Непринятых предложений: <b>3</b>" in msg and "@Ivan" in msg and "@Anna" in msg
        assert "25.00 $CITY в сутки" in msg              # 100 units × 0.25 — the daily cost, no per-10 ambiguity
        kb = rem[0]["reply_markup"]["inline_keyboard"][0][0]
        assert kb["text"] == "📋 Открыть предложения" and kb["url"] == "https://t.me/GramCityBot/app?startapp=go-purchases"
        assert rem[0]["payload"]["open_path"] == "/trading?tab=operations&sub=purchases"

        await tr.run(db)                                   # again right away: not before 12 h
        assert len([x for x in sent if x.get("type_key") == "tender_offers_pending"]) == 1
        await db.users.update_one({"id": "buyer"}, {"$set": {"tender_reminder_at": ago(13)}})
        await tr.run(db)
        assert len([x for x in sent if x.get("type_key") == "tender_offers_pending"]) == 2
    run(go())


def test_change_request_reminder_goes_to_the_side_that_must_answer(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        am = {"id": "a1", "proposed_by": "buyer", "proposed_by_id": "buyer", "proposed_at": ago(4), "status": "PENDING",
              "new_daily_amount": 200.0, "new_price_per_unit": 0.3}
        await db.tender_contracts.insert_one(offer("c1", status="ACTIVE", pending_amendment=am))
        await tr.run(db)
        rem = [x for x in sent if x.get("type_key") == "tender_offers_pending"]
        assert [x["to"] for x in rem] == ["seller"]
        assert "Boris" in rem[0]["message"] and "60.00 $CITY/día" in rem[0]["message"]     # Spanish, 200 × 0.3
        assert rem[0]["payload"]["open_path"].endswith("sub=supplies")
    run(go())


def test_offer_and_change_request_expire_after_72h_and_the_author_is_told(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        am = {"id": "a1", "proposed_by": "seller", "proposed_by_id": "seller2", "proposed_at": ago(80), "status": "PENDING",
              "new_daily_amount": 200.0, "new_price_per_unit": 0.3}
        await db.tender_contracts.insert_many([
            offer("old", created=ago(73)), offer("young", created=ago(71)),
            offer("c2", seller="seller2", status="ACTIVE", pending_amendment=am)])
        out = await tr.run(db)
        assert out["expired"] == {"offers": 1, "amendments": 1}
        assert (await db.tender_contracts.find_one({"id": "old"}))["status"] == "EXPIRED"
        assert (await db.tender_contracts.find_one({"id": "young"}))["status"] == "PROPOSED"
        assert (await db.tender_contracts.find_one({"id": "c2"}))["pending_amendment"]["status"] == "EXPIRED"
        exp = [x for x in sent if x.get("type_key") in ("tender_offer_expired", "tender_amendment_expired")]
        assert {x["to"] for x in exp} == {"seller", "seller2"}
        es = next(x for x in exp if x["to"] == "seller")
        assert "72 h" in es["message"] and "Boris" in es["message"]
        # the buyer's accept on the expired offer explains it
        with pytest.raises(Exception) as e:
            await T.accept_offer("old", current_user=U("buyer", "Boris"))
        assert "истёк" in e.value.detail
    run(go())


def test_new_offer_notification_carries_the_open_button(monkeypatch):
    async def go():
        db, T, sent = await world(monkeypatch)
        await T._notify_user(await db.users.find_one({"id": "buyer"}, {"_id": 0}), "t", "m", open_sub="purchases")
        kb = sent[-1]["reply_markup"]["inline_keyboard"][0][0]
        assert kb["url"].endswith("startapp=go-purchases") and sent[-1]["payload"]["open_label"] == "📋 Открыть предложения"
    run(go())


def test_my_lists_show_only_live_contracts(monkeypatch):
    """«Мои поставки» / «Мои закупки»: expired, withdrawn, rejected, broken contracts are not listed."""
    async def go():
        db, T, _ = await world(monkeypatch)
        await db.tenders.insert_one({"id": "T1", "buyer_id": "buyer", "buyer_username": "Boris", "status": "OPEN",
                                     "resource_type": "energy", "created_at": ago(1)})
        for i, st in enumerate(["PROPOSED", "ACTIVE", "PENDING_FUNDS", "EXPIRED", "WITHDRAWN", "REJECTED", "BROKEN"]):
            await db.tender_contracts.insert_one({"id": f"C{i}", "tender_id": "T1", "seller_id": "seller",
                                                  "buyer_id": "buyer", "resource_type": "energy", "daily_amount": 10,
                                                  "status": st, "created_at": ago(i)})
        sup = await T.my_supplies(current_user=U("seller", "Anna"))
        pur = await T.my_purchases(current_user=U("buyer", "Boris"))
        return sorted(c["status"] for c in sup["contracts"]), sorted(c["status"] for c in pur["tenders"][0]["contracts"])
    sup, pur = run(go())
    assert sup == ["ACTIVE", "PENDING_FUNDS", "PROPOSED"]
    assert pur == ["ACTIVE", "PENDING_FUNDS", "PROPOSED"]


def test_proposed_offer_has_expires_at(monkeypatch):
    async def go():
        db, T, _ = await world(monkeypatch)
        await db.tenders.insert_one({"id": "T1", "buyer_id": "buyer", "buyer_username": "Boris", "status": "OPEN",
                                     "resource_type": "energy", "created_at": ago(1)})
        created = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.tender_contracts.insert_one({"id": "C1", "tender_id": "T1", "seller_id": "seller", "buyer_id": "buyer",
                                              "resource_type": "energy", "daily_amount": 10, "status": "PROPOSED",
                                              "created_at": created.isoformat()})
        sup = await T.my_supplies(current_user=U("seller", "Anna"))
        return created, sup["contracts"][0]
    created, c = run(go())
    left = datetime.fromisoformat(c["expires_at"]) - datetime.now(timezone.utc)
    assert c["expire_h"] == 72
    assert timedelta(hours=71, minutes=58) < left <= timedelta(hours=71, minutes=59, seconds=1)
