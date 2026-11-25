"""Referrals: the link reaches the bot even without a Main Mini App; the bot remembers the inviter; the Mini App
sign-up binds him; nobody invites himself."""
import asyncio

import mongomock_motor

import core.ref_links as RL
import routes.telegram_auth as TA


def run(c):
    return asyncio.run(c)


def test_link_uses_start_without_named_app(monkeypatch):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["r"]
        RL.invalidate()
        await db.game_settings.insert_one({"type": "telegram_settings", "app_url": "https://t.me/GramCityBot"})
        assert await RL.referral_link(db, "u-1") == "https://t.me/GramCityBot?start=u-1"
        await db.game_settings.update_one({"type": "telegram_settings"}, {"$set": {"miniapp_link": "https://t.me/GramCityBot/play"}})
        assert await RL.referral_link(db, "u-1") == "https://t.me/GramCityBot/play?startapp=u-1"
    run(go())


def test_bot_referral_used_by_miniapp_and_no_self_invite():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["r"]
        await db.users.insert_one({"id": "inviter", "email": "a@x.io"})
        await db.bot_referrals.insert_one({"telegram_id": "777", "ref_id": "inviter"})
        assert await TA._pending_bot_referral(db, "777") == "inviter"
        assert await TA._pending_bot_referral(db, "888") is None
        f = await TA._referral_binding_fields(db, "inviter")
        assert f["referrerId"] == "inviter"
        assert await TA._referral_binding_fields(db, "inviter", self_id="inviter") == {}
        assert await TA._referral_binding_fields(db, "ref_inviter") != {}
    run(go())


def test_bot_remembers_and_binds_fresh_account():
    async def go():
        import telegram_bot as TB
        db = mongomock_motor.AsyncMongoMockClient()["r"]
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        await db.users.insert_many([{"id": "inviter"}, {"id": "newbie", "telegram_chat_id": "555", "created_at": now.isoformat()},
                                    {"id": "old", "telegram_chat_id": "556", "created_at": (now - timedelta(days=30)).isoformat()}])
        bot = TB.TelegramBot.__new__(TB.TelegramBot)
        bot.db = db
        assert not await bot._is_link_token("inviter")
        assert await bot._remember_bot_referral(555, "inviter") == "inviter"
        assert (await db.bot_referrals.find_one({"telegram_id": "555"}))["ref_id"] == "inviter"
        assert (await db.users.find_one({"id": "newbie"}))["referrerId"] == "inviter"
        assert await bot._remember_bot_referral(556, "inviter") == "inviter"
        assert not (await db.users.find_one({"id": "old"})).get("referrerId")     # an old player is not re-bound
        assert await bot._remember_bot_referral(555, "nobody") is None
    run(go())
