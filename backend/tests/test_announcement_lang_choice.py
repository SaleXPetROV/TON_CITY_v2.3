"""An announcement reaches every player in the RIGHT language: Telegram — the language of the bot (chosen in the bot),
the in-app notification — the language of the project; the two choices are independent (choosing a language in the
app does not change the bot language)."""
import asyncio
import os
import sys
import uuid

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


class FakeBot:
    def __init__(self):
        self.sent = {}
        self.last_failure = {}
        self.last_error = None

    async def ping(self):
        return True, ""

    async def send_message(self, chat_id, text, **kw):
        self.sent[str(chat_id)] = text
        return True

    async def send_photo(self, chat_id, photo, caption="", **kw):
        self.sent[str(chat_id)] = caption
        return True


def test_bot_language_for_telegram_project_language_in_app(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    import server
    import telegram_bot
    bot = FakeBot()
    monkeypatch.setattr(telegram_bot, "get_telegram_bot", lambda: bot)
    monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]   # a client of THIS test's event loop
    monkeypatch.setattr(server, "db", db)
    tag = uuid.uuid4().hex[:8]
    uid, chat = f"lang-{tag}", f"77{int(tag, 16) % 10**8}"
    uid2, chat2 = f"lang2-{tag}", f"78{int(tag, 16) % 10**8}"
    ann = {"id": f"ann-{tag}", "title": "Заголовок", "message": "Привет", "auto_translate": False,
           "translations": {"ru": {"title": "Заголовок", "message": "Привет"},
                            "en": {"title": "Title", "message": "Hello"}}}

    async def run():
        await db.users.insert_many([
            {"id": uid, "username": f"u{tag}", "language": "ru", "telegram_chat_id": chat},
            {"id": uid2, "username": f"v{tag}", "telegram_chat_id": chat2}])      # never picked a project language
        await db.telegram_mappings.insert_many([{"chat_id": chat, "language": "en"},
                                                {"chat_id": chat2, "language": "en"}])
        try:
            await server._publish_announcement(dict(ann))
            assert "Hello" in bot.sent[chat] and "Привет" not in bot.sent[chat]      # bot in English → English
            n = await db.notifications.find_one({"announcement_id": ann["id"], "user_id": uid}, {"_id": 0})
            assert n["message"] == "Привет"                                          # project in Russian → Russian
            n2 = await db.notifications.find_one({"announcement_id": ann["id"], "user_id": uid2}, {"_id": 0})
            assert n2["message"] == "Hello"                                          # no project language → the bot's
        finally:
            await db.users.delete_many({"id": {"$in": [uid, uid2]}})
            await db.telegram_mappings.delete_many({"chat_id": {"$in": [chat, chat2]}})
            await db.notifications.delete_many({"announcement_id": ann["id"]})
            await db.announcements.delete_many({"id": ann["id"]})
    asyncio.run(run())


def test_app_language_does_not_overwrite_bot_language():
    """PUT /api/auth/update-language changes the project language only; the bot language stays as chosen in the bot
    (it is filled from the app only when the bot has none yet)."""
    import httpx
    import jwt
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from pymongo import MongoClient
    from security_middleware import get_or_generate_jwt_secret
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    email = "testuser@example.com"
    u = db.users.find_one({"email": email}, {"_id": 0, "telegram_chat_id": 1, "language": 1, "language_chosen": 1})
    if u is None:
        import pytest
        pytest.skip("test user missing")
    chat = f"79{uuid.uuid4().int % 10**8}"
    tok = jwt.encode({"sub": email, "exp": 9999999999}, get_or_generate_jwt_secret(), algorithm="HS256")
    h = {"Authorization": f"Bearer {tok}"}
    try:
        db.users.update_one({"email": email}, {"$set": {"telegram_chat_id": chat}})
        db.telegram_mappings.insert_one({"chat_id": chat, "language": "en"})
        r = httpx.put("http://127.0.0.1:8001/api/auth/update-language", json={"language": "ru", "chosen": True}, headers=h)
        assert r.status_code == 200, r.text
        assert db.telegram_mappings.find_one({"chat_id": chat})["language"] == "en"
        assert db.users.find_one({"email": email})["language"] == "ru"
        # the bot has no language yet → it gets the app language
        db.telegram_mappings.update_one({"chat_id": chat}, {"$unset": {"language": ""}})
        httpx.put("http://127.0.0.1:8001/api/auth/update-language", json={"language": "de"}, headers=h)
        assert db.telegram_mappings.find_one({"chat_id": chat})["language"] == "de"
    finally:
        db.telegram_mappings.delete_many({"chat_id": chat})
        restore = {k: u[k] for k in ("telegram_chat_id", "language", "language_chosen") if k in u}
        unset = {k: "" for k in ("telegram_chat_id", "language", "language_chosen") if k not in u}
        db.users.update_one({"email": email}, {**({"$set": restore} if restore else {}), **({"$unset": unset} if unset else {})})


def test_undelivered_reasons_are_told_apart(monkeypatch):
    """«Не доставлено» is split by Telegram's exact answer: blocked the bot / never allowed it to write / deleted
    account; the reason is kept on the chat and cleared when the player allows the bot to write."""
    import json
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    import server
    import telegram_bot
    note = telegram_bot.TelegramBot._note_failure.__func__
    answers = {"blocked by the user": "Forbidden: bot was blocked by the user",
               "deactivated": "Forbidden: user is deactivated",
               "initiate": "Forbidden: bot can't initiate conversation with a user"}

    class Bot(FakeBot):
        last_failure = {}
        last_failure_detail = {}
        last_error = None
        fail = {}

        def __init__(self):
            self.sent = {}                      # the failure maps stay on the class (as in TelegramBot)

        async def send_message(self, chat_id, text, **kw):
            why = self.fail.get(str(chat_id))
            if why:
                note(Bot, chat_id, 403, json.dumps({"ok": False, "error_code": 403, "description": why}))
                return False
            return await FakeBot.send_message(self, chat_id, text)

    bot = Bot()
    monkeypatch.setattr(telegram_bot, "get_telegram_bot", lambda: bot)
    monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]   # a client of THIS test's event loop
    monkeypatch.setattr(server, "db", db)
    tag = uuid.uuid4().hex[:6]
    chats = {k: f"8{i}{int(tag, 16) % 10**7}" for i, k in enumerate(answers)}
    for k, c in chats.items():
        Bot.fail[c] = answers[k]
    ann = {"id": f"ann-r-{tag}", "title": "T", "message": "M", "auto_translate": False}

    async def run():
        await db.telegram_mappings.insert_many([{"chat_id": c, "language": "ru"} for c in chats.values()])
        await db.announcements.insert_one(dict(ann))
        try:
            await server._publish_announcement(dict(ann))
            d = (await db.announcements.find_one({"id": ann["id"]}, {"_id": 0, "delivery": 1}) or {}).get("delivery") \
                or {}
            states = {m["chat_id"]: m.get("delivery_state") async for m in
                      db.telegram_mappings.find({"chat_id": {"$in": list(chats.values())}}, {"_id": 0})}
            assert states[chats["blocked by the user"]] == "blocked_by_user"
            assert states[chats["deactivated"]] == "deactivated"
            assert states[chats["initiate"]] == "no_access"
            assert d["blocked"] == 3 and d["blocked_detail"] == {"blocked_by_user": 1, "deactivated": 1, "no_access": 1}
            return d
        finally:
            await db.telegram_mappings.delete_many({"chat_id": {"$in": list(chats.values())}})
            await db.notifications.delete_many({"announcement_id": ann["id"]})
            await db.announcements.delete_many({"id": ann["id"]})
    asyncio.run(run())
