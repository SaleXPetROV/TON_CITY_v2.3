"""The support agent's link goes to the SITE (Админка → Поддержка → «Сайт для агентов поддержки»), never to the bot."""
import asyncio
import os
import sys

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import support_handler as sh  # noqa: E402


def run(c):
    return asyncio.run(c)


def test_agent_link_uses_the_agent_site_and_never_a_bot_link(monkeypatch):
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["sup"]
        sh.init_support(db, None, None, None)
        for k in ("PUBLIC_APP_URL", "BACKEND_URL", "PUBLIC_URL", "FRONTEND_URL", "REACT_APP_BACKEND_URL"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setattr(sh, "_resolve_public_url", lambda: asyncio.sleep(0, result=""))
        await db.support_agents.insert_one({"telegram_id": "42", "display_name": "Ann"})
        # the players' link is a bot link → not used for the agent
        await db.support_settings.insert_one({"_id": "main", "public_url": "https://t.me/gramcity_games_bot", "hidden_path": "panel-x"})
        assert await sh.agent_site_base() == ""
        await db.support_settings.update_one({"_id": "main"}, {"$set": {"agent_site_url": "https://gramcity.app"}})
        url = await sh.agent_panel_url("42")
        assert url.startswith("https://gramcity.app/panel-x?login_token=")
        kb = sh.agent_panel_markup(url)
        assert kb == {"inline_keyboard": [[{"text": "🛡 Открыть панель агента", "url": url}]]}
        assert sh._is_bot_link("https://t.me/x?startapp=1") and not sh._is_bot_link("https://gramcity.app")
    run(go())
