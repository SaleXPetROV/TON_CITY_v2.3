"""Referral links that open the game as a Telegram Mini App (not the website in a browser).

    https://t.me/<bot>/<app>?startapp=<user_id>   — when the admin set the Mini App link («Ссылка на Mini App»)
    https://t.me/<bot>?startapp=<user_id>         — otherwise: the bot's Main Mini App (BotFather → Bot Settings →
                                                     Configure Mini App must be enabled for this short form)
Telegram passes `startapp` to the Mini App as `start_param`; routes/telegram_auth.py binds the referrer from it
(new account or an existing one without a referrer), the web app also reads it (App.js → ref_code).
Only when no bot is configured at all the old web link `<site>/?ref=<id>` is used.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

_cache = {"bot": ("", 0.0)}
TTL = 600.0


def _norm_tme(url: str) -> str:
    """https://t.me/... form without a trailing slash and without a previous startapp/start parameter."""
    u = (url or "").strip()
    if not u:
        return ""
    u = re.sub(r"^(https?://)?(www\.)?(telegram\.me|t\.me)/", "https://t.me/", u)
    if not u.startswith("https://t.me/"):
        return ""
    base, _, query = u.partition("?")
    keep = [p for p in query.split("&") if p and not p.startswith(("startapp=", "start=", "startattach="))]
    return base.rstrip("/") + (("?" + "&".join(keep)) if keep else "")


async def bot_username(db) -> str:
    name, at = _cache["bot"]
    if name and time.monotonic() - at < TTL:
        return name
    name = ""
    try:
        doc = await db.admin_settings.find_one({"type": "telegram_bot"}, {"_id": 0, "bot_username": 1}) or {}
        name = str(doc.get("bot_username") or "").strip().lstrip("@")
        if not name:
            gs = await db.game_settings.find_one({"type": "telegram_settings"}, {"_id": 0, "bot_username": 1}) or {}
            name = str(gs.get("bot_username") or "").strip().lstrip("@")
    except Exception as e:
        logger.debug(f"ref_links bot_username db: {e}")
    if not name:
        name = (os.environ.get("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    if not name:
        try:
            from promo_broadcast import _resolve_bot_username
            name = await _resolve_bot_username(db)
        except Exception as e:
            logger.debug(f"ref_links getMe: {e}")
    if name:
        _cache["bot"] = (name, time.monotonic())
    return name


async def miniapp_base(db) -> str:
    """The Mini App address referral links start from ('' when no bot is configured)."""
    try:
        gs = await db.game_settings.find_one({"type": "telegram_settings"}, {"_id": 0, "miniapp_link": 1, "app_url": 1}) or {}
    except Exception:
        gs = {}
    for cand in (gs.get("miniapp_link"), gs.get("app_url")):
        base = _norm_tme(str(cand or ""))
        if base:
            return base
    bot = await bot_username(db)
    return f"https://t.me/{bot}" if bot else ""


async def referral_link(db, user_id: str, web_base: Optional[str] = None) -> str:
    """The player's referral link: the Telegram Mini App with startapp=<id> (web link only as the last resort)."""
    if not user_id:
        return ""
    base = await miniapp_base(db)
    if base:
        return f"{base}{'&' if '?' in base else '?'}startapp={user_id}"
    web = (web_base or os.environ.get("PUBLIC_APP_URL") or "https://gramcity.games").rstrip("/")
    return f"{web}/?ref={user_id}"


def invalidate() -> None:
    _cache["bot"] = ("", 0.0)
