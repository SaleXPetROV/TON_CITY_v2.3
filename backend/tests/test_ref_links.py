"""Referral links open the Telegram Mini App: t.me/<bot>/<app>?startapp=<id> or t.me/<bot>?startapp=<id>."""
import os
import sys
from functools import partial

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def test_ref_links():
    import asyncio
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from motor.motor_asyncio import AsyncIOMotorClient
    from core import ref_links as rl

    assert rl._norm_tme("t.me/MyBot/app?startapp=old&x=1") == "https://t.me/MyBot/app?x=1"
    assert rl._norm_tme("https://telegram.me/MyBot/") == "https://t.me/MyBot"
    assert rl._norm_tme("https://gramcity.games") == ""

    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        gs = await db.game_settings.find_one({"type": "telegram_settings"}, {"_id": 0, "miniapp_link": 1, "app_url": 1}) or {}
        ab = await db.admin_settings.find_one({"type": "telegram_bot"}, {"_id": 0, "bot_username": 1})
        try:
            await db.game_settings.update_one({"type": "telegram_settings"},
                                              {"$set": {"miniapp_link": "https://t.me/TestCityBot/play", "app_url": "https://gramcity.games"}}, upsert=True)
            rl.invalidate()
            assert await rl.referral_link(db, "u-1") == "https://t.me/TestCityBot/play?startapp=u-1"
            # no Mini App link → the bot's Main Mini App
            await db.game_settings.update_one({"type": "telegram_settings"}, {"$set": {"miniapp_link": ""}})
            await db.admin_settings.update_one({"type": "telegram_bot"}, {"$set": {"bot_username": "@TestCityBot"}}, upsert=True)
            rl.invalidate()
            assert await rl.referral_link(db, "u-2") == "https://t.me/TestCityBot?startapp=u-2"
            # «URL открытия приложения» that is already a t.me Mini App link is reused
            await db.game_settings.update_one({"type": "telegram_settings"}, {"$set": {"app_url": "https://t.me/TestCityBot/game"}})
            assert await rl.referral_link(db, "u-3") == "https://t.me/TestCityBot/game?startapp=u-3"
        finally:
            await db.game_settings.update_one({"type": "telegram_settings"},
                                              {"$set": {"miniapp_link": gs.get("miniapp_link", ""), "app_url": gs.get("app_url", "")}})
            if ab is None:
                await db.admin_settings.delete_one({"type": "telegram_bot"})
            else:
                await db.admin_settings.update_one({"type": "telegram_bot"}, {"$set": {"bot_username": ab.get("bot_username", "")}})
            rl.invalidate()

    asyncio.run(run())
