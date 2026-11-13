"""Withdrawal approve / reject — one implementation for the admin panel and the Telegram bot (withdrawals.py).

The bot's buttons used to run an old copy of the logic (wrong payout wallet, no decryption, no lock, refund by wallet
only) and showed nothing on errors. Now: the same functions, the card becomes a result button with the hash.
"""
import asyncio
import os
import sys
import types

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import withdrawals as wd  # noqa: E402

HASH = "a" * 64


def run(c):
    return asyncio.run(c)


class FakeTon:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    async def send_ton_payout(self, dest_address, amount_ton, mnemonics, user_username=""):
        self.calls.append((dest_address, amount_ton, mnemonics))
        if self.fail:
            raise self.fail
        return HASH


class FakeBot:
    def __init__(self, admin="777"):
        self.edits, self.answers, self.sent, self.admin = [], [], [], admin

    async def get_admin_telegram_id(self):
        return self.admin

    async def edit_message(self, chat_id, message_id, text, reply_markup=None):
        self.edits.append((str(chat_id), message_id, text, reply_markup))
        return True

    async def answer_callback(self, cid, text, show_alert=False):
        self.answers.append(text)

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(text)
        return True


async def _world(monkeypatch, ton, status="pending"):
    db = mongomock_motor.AsyncMongoMockClient()["wd"]
    await db.users.insert_one({"id": "u1", "username": "An3412", "balance_ton": 0.0, "telegram_chat_id": "555",
                               "raw_address": "0:abc", "language": "es"})
    await db.transactions.insert_one({"id": "t1", "tx_type": "withdrawal", "status": status, "user_id": "u1",
                                      "user_username": "An3412", "amount_ton": 1.05, "net_amount": 1.0185,
                                      "commission": 0.0315, "created_at": "2026-11-07T13:50:00+00:00",
                                      "admin_tg_card": {"chat_id": "777", "message_id": 42, "address": "UQB…"}})
    await db.admin_settings.insert_one({"type": "withdrawal_wallet", "mnemonic": "word " * 24})
    import ton_integration
    monkeypatch.setattr(ton_integration, "ton_client", ton)
    sent = []

    def _bg(db_, uid, *a, **kw):
        sent.append({"uid": uid, **kw})
    import core.notify
    monkeypatch.setattr(core.notify, "notify_user_background", _bg)
    bot = FakeBot()
    import telegram_bot
    monkeypatch.setattr(telegram_bot, "get_telegram_bot", lambda: bot)
    return db, bot, sent


def test_approve_pays_once_records_hash_and_turns_the_card_into_a_result(monkeypatch):
    async def go():
        ton = FakeTon()
        db, bot, sent = await _world(monkeypatch, ton)
        r = await wd.approve(db, "t1")
        assert r["hash"] == HASH and len(ton.calls) == 1
        assert ton.calls[0][0] == "0:abc" and ton.calls[0][1] == 1.0185
        tx = await db.transactions.find_one({"id": "t1"})
        assert tx["status"] == "completed" and tx["blockchain_hash"] == HASH
        assert tx["explorer_url"] == f"https://tonviewer.com/transaction/{HASH}"
        # the player is notified with the hash (rendered in their language by notify_user)
        assert sent and sent[0]["tx_hash"] == HASH and sent[0]["i18n_key"] == "withdrawal_approved"
        # the admin's card: text with the hash, ONE result button with the explorer link
        chat, mid, text, kb = bot.edits[-1]
        assert (chat, mid) == ("777", 42) and HASH in text and "ВЫВЕДЕНО" in text
        assert kb["inline_keyboard"] == [[{"text": "✅ Выведено — открыть транзакцию",
                                           "url": f"https://tonviewer.com/transaction/{HASH}"}]]
        with pytest.raises(wd.WithdrawalError):                 # a second tap never pays again
            await wd.approve(db, "t1")
        assert len(ton.calls) == 1
    run(go())


def test_reject_refunds_once_by_user_id(monkeypatch):
    async def go():
        db, bot, sent = await _world(monkeypatch, FakeTon())
        r = await wd.reject(db, "t1")
        assert r["amount"] == 1.05
        u = await db.users.find_one({"id": "u1"})
        assert u["balance_ton"] == pytest.approx(1.05)
        with pytest.raises(wd.WithdrawalError):
            await wd.reject(db, "t1")
        u = await db.users.find_one({"id": "u1"})
        assert u["balance_ton"] == pytest.approx(1.05)
        _, _, text, kb = bot.edits[-1]
        assert "ОТКЛОНЕНО" in text and kb["inline_keyboard"][0][0]["text"] == "❌ Отклонено"
        assert sent[0]["i18n_key"] == "withdrawal_rejected"
    run(go())


def test_network_failure_refunds_and_shows_it(monkeypatch):
    async def go():
        db, bot, sent = await _world(monkeypatch, FakeTon(fail=RuntimeError("seqno")))
        with pytest.raises(wd.WithdrawalError):
            await wd.approve(db, "t1")
        tx = await db.transactions.find_one({"id": "t1"})
        assert tx["status"] == "failed"
        assert (await db.users.find_one({"id": "u1"}))["balance_ton"] == pytest.approx(1.05)
        assert "Не выведено" in bot.edits[-1][3]["inline_keyboard"][0][0]["text"]
    run(go())


def test_bot_buttons_work_for_the_admin_even_when_the_id_is_stored_as_a_number(monkeypatch):
    async def go():
        ton = FakeTon()
        db, _bot, _sent = await _world(monkeypatch, ton)
        await db.admin_settings.insert_one({"type": "telegram_bot", "admin_telegram_id": 777})   # an int
        import telegram_bot as tb
        bot = tb.TelegramBot.__new__(tb.TelegramBot)
        bot.db = db
        fake = FakeBot()
        bot.edit_message = fake.edit_message
        bot.answer_callback = fake.answer_callback
        bot.send_message = fake.send_message
        bot.delete_message = fake.edit_message
        bot._spawn = lambda coro: coro.close()
        assert await bot.get_admin_telegram_id() == "777"
        await bot.handle_callback_query({"id": "cb1", "data": "approve_wd_t1", "from": {"id": 777},
                                         "message": {"message_id": 42}})
        tx = await db.transactions.find_one({"id": "t1"})
        assert tx["status"] == "completed" and len(ton.calls) == 1
        assert fake.answers[0].startswith("⏳")
        assert any("ВЫВЕДЕНО" in e[2] for e in fake.edits)
        # a tap on the result button does nothing (and says so)
        await bot.handle_callback_query({"id": "cb2", "data": "wd_done_t1", "from": {"id": 777}, "message": {"message_id": 42}})
        assert fake.answers[-1] == "Заявка уже обработана" and len(ton.calls) == 1
    run(go())
