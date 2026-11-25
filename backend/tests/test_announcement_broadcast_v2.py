"""Announcement broadcast v2:
1) picture stored once as a file; Telegram gets the bytes once, then the file_id;
2) one broadcast at a time across processes (database lock);
3) Telegram goes to every bot subscriber (linked or not), one message per chat; in-app goes to every account at
   the configured pace; counters in `delivery`.
"""
import asyncio
import base64
import os
import sys
import time
import uuid

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def test_data_uri_becomes_file():
    from core.media import to_media_url, local_file
    uri = "data:image/png;base64," + base64.b64encode(PNG).decode()
    url = to_media_url(uri)
    assert url.startswith("/api/media/announcements/") and url.endswith(".png")
    f = local_file(url)
    assert f is not None and f.read_bytes() == PNG
    assert to_media_url(uri) == url                      # same picture → same file
    assert local_file("/api/media/announcements/../../etc/passwd") is None


def test_photo_uploaded_once_then_file_id():
    import telegram_bot as tg

    calls = []

    class _Bot(tg.TelegramBot):
        async def get_bot_token(self):
            return "1:x"

        async def _send_photo_once(self, bot_token, chat_id, photo, caption, parse_mode, reply_markup, is_file_id=False):
            calls.append((chat_id, "fid" if is_file_id else "upload"))
            await asyncio.sleep(0.05)
            return True, ("FID1" if not is_file_id else None), False

    async def run():
        bot = _Bot(None)
        tg.TelegramBot._photo_ids.clear()
        src = "data:image/png;base64," + base64.b64encode(PNG + uuid.uuid4().bytes).decode()
        res = await asyncio.gather(*[bot.send_photo(str(i), src, caption="c") for i in range(6)])
        return res

    res = asyncio.run(run())
    assert all(res)
    assert [k for _c, k in calls].count("upload") == 1, calls
    assert [k for _c, k in calls].count("fid") == 5, calls


class _FakeBot:
    last_failure: dict = {}

    def __init__(self):
        self.calls = []

    async def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None, **kw):
        self.calls.append(("msg", str(chat_id)))
        return True

    async def send_photo(self, chat_id, photo_url, caption="", parse_mode="HTML", reply_markup=None, **kw):
        self.calls.append(("photo", str(chat_id), photo_url))
        return True


async def _fanout():
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    import telegram_bot as tg_mod
    import server as srv

    tag = uuid.uuid4().hex[:8]
    users = [
        {"id": f"bc-{tag}-1", "telegram_chat_id": f"91{tag}", "language": "en"},
        {"id": f"bc-{tag}-2", "telegram_chat_id": f"91{tag}", "language": "en"},     # same chat as user 1
        {"id": f"bc-{tag}-3", "telegram_chat_id": None, "language": "ru"},
    ]
    sub = {"chat_id": f"92{tag}", "language": "ru"}                                # bot subscriber, no account
    group = {"chat_id": f"-100{tag}", "language": "ru"}                            # a group the bot is in — never a target
    fake = _FakeBot()
    orig_bot, orig_db = tg_mod.telegram_bot, srv.db
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    srv.db = client[os.environ["DB_NAME"]]
    os.environ["ANNOUNCEMENT_INAPP_PER_SEC"] = "40"
    try:
        tg_mod.telegram_bot = fake
        await srv.db.users.insert_many([dict(u) for u in users])
        await srv.db.telegram_mappings.insert_many([dict(sub), dict(group)])
        ann_id = f"ann-{tag}"
        # the lock: a second broadcast cannot start while this one holds it
        assert await srv._broadcast_lock_take(ann_id)
        assert not await srv._broadcast_lock_take("someone-else")
        img = "data:image/png;base64," + base64.b64encode(PNG).decode()
        ann = {"id": ann_id, "title": f"Hello {tag}", "message": "World", "image_url": img}
        await srv.db.announcements.insert_one(dict(ann))
        t0 = time.monotonic()
        await srv._run_announcement_guarded(ann)
        took = time.monotonic() - t0
        doc = await srv.db.announcements.find_one({"id": ann_id}, {"_id": 0}) or {}
        notif = await srv.db.notifications.find_one({"user_id": users[0]["id"], "announcement_id": ann_id}, {"_id": 0}) or {}
        n_users = await srv.db.users.count_documents({"id": {"$nin": [None, ""]}})
        free_after = await srv._broadcast_lock_take("after")
        await srv._broadcast_lock_release("after")
        return fake, doc, notif, took, n_users, free_after, tag
    finally:
        await srv.db.users.delete_many({"id": {"$in": [u["id"] for u in users]}})
        await srv.db.telegram_mappings.delete_many({"chat_id": {"$in": [sub["chat_id"], group["chat_id"]]}})
        await srv.db.notifications.delete_many({"title": f"Hello {tag}"})
        await srv.db.announcements.delete_many({"id": f"ann-{tag}"})
        os.environ.pop("ANNOUNCEMENT_INAPP_PER_SEC", None)
        tg_mod.telegram_bot = orig_bot
        srv.db = orig_db


def test_fanout_counts_lock_and_picture():
    fake, doc, notif, took, n_users, free_after, tag = asyncio.run(_fanout())
    d = doc.get("delivery") or {}
    chats = [c[1] for c in fake.calls]
    assert chats.count(f"91{tag}") == 1 and chats.count(f"92{tag}") == 1, fake.calls   # linked + unlinked subscriber
    assert f"-100{tag}" not in chats, "groups/channels get the channel post only, not a second broadcast copy"
    assert d["status"] == "done" and d["in_app"] == d["in_app_total"] == n_users, d
    assert d["sent"] == d["telegram_total"] >= 2, d
    # the picture is a stored file: the announcement, the notification and Telegram use the short URL
    assert doc["image_url"].startswith("/api/media/announcements/"), doc["image_url"][:60]
    assert notif.get("image_url") == doc["image_url"]
    assert all(c[2] == doc["image_url"] for c in fake.calls if c[0] == "photo")
    if n_users > 40:                                      # 40 accounts per second → at least one pause
        assert took >= 0.9, took
    assert free_after, "lock must be released after the fan-out"
