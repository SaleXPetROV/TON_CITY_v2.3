"""Telegram routes: an unreachable TELEGRAM_API_BASE (e.g. a Worker) must not stop the bot when another route works."""
import asyncio
import json

from aiohttp import web


def run(c):
    return asyncio.run(c)


async def _servers():
    async def ok(request):
        return web.Response(text=json.dumps({"ok": True, "result": {"id": 1}}), content_type="application/json")

    async def hang(request):
        await asyncio.sleep(4)
        return web.Response(text="late")

    async def html(request):
        return web.Response(status=404, text="<html>not found</html>")

    async def bad_token(request):
        return web.Response(status=401, text=json.dumps({"ok": False, "error_code": 401, "description": "Unauthorized"}))
    app = web.Application()
    app.router.add_get("/ok/bot{tok}/getMe", ok)
    app.router.add_get("/hang/bot{tok}/getMe", hang)
    app.router.add_get("/html/bot{tok}/getMe", html)
    app.router.add_get("/bad/bot{tok}/getMe", bad_token)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}"


def test_switches_to_the_route_that_works(monkeypatch):
    import telegram_bot as T

    async def go():
        runner, url = await _servers()
        try:
            monkeypatch.setattr(T, "TELEGRAM_API_BASE", f"{url}/hang")
            monkeypatch.setattr(T, "_DIRECT_API", f"{url}/ok")
            monkeypatch.setenv("TELEGRAM_API_BASE", f"{url}/hang")
            monkeypatch.setenv("TELEGRAM_API_BASE_FALLBACKS", f"{url}/html")
            for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
                monkeypatch.delenv(k, raising=False)
            bot = T.TelegramBot.__new__(T.TelegramBot)
            bot._session = None
            bot._bg_tasks = set()

            async def tok():
                return "123:abc"
            bot.get_bot_token = tok
            d = await bot.diagnose(timeout=1.5)
            assert d["ok"] and T.TELEGRAM_API_BASE == f"{url}/ok"
            errs = [p["error"] for p in d["probes"]]
            assert "таймаут" in errs[0] and "не пересылает" in errs[1]
            ok, why = await bot.ping(timeout=1.5)
            assert ok and why == ""
            # a token Telegram refuses is told as such
            monkeypatch.setattr(T, "TELEGRAM_API_BASE", f"{url}/bad")
            monkeypatch.setattr(T, "_DIRECT_API", f"{url}/bad")
            monkeypatch.delenv("TELEGRAM_API_BASE_FALLBACKS")
            monkeypatch.setenv("TELEGRAM_API_BASE", f"{url}/bad")
            ok, why = await bot.ping(timeout=1.5)
            assert not ok and "отклонил токен" in why and "123:abc" not in why
            if bot._session:
                await bot._session.close()
        finally:
            await runner.cleanup()
    run(go())
