"""Centralised in-app + Telegram notification helper.

Use ``notify_user`` from any backend module to:
  • Insert a row into ``db.notifications`` for the in-app drawer
  • Push a ``notification_new`` event over the WebSocket so the bell shakes
    instantly (no polling delay)
  • Mirror the same text to Telegram if the user has connected their account
    and has notifications enabled

This is a thin coroutine — callers should NOT await it inside hot loops or
critical paths. Best-effort: any error is logged but never raised.
"""
from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# Inline keyboard with a single "🏠 На главную" button. The Telegram bot
# already handles the `back_to_menu` callback (see telegram_bot.py) — tapping
# it returns the user to the bot's main menu (cmd_start).
HOME_BUTTON_MARKUP: Dict[str, Any] = {
    "inline_keyboard": [[{"text": "🏠 На главную", "callback_data": "back_to_menu"}]]
}


def ton_explorer_url(tx_hash: str) -> Optional[str]:
    """Build a TON explorer link for a transaction hash (tonviewer)."""
    if not tx_hash or tx_hash == "sent_success":
        return None
    return f"https://tonviewer.com/transaction/{tx_hash}"


def tx_and_home_markup(tx_hash: str = None, lang: str = "ru") -> Dict[str, Any]:
    """Inline keyboard: optional '🔗 Транзакция' link button (opens the explorer)
    + '🏠 На главную'. Used by deposit/withdrawal Telegram notifications so the
    bot shows a clickable transaction link instead of a raw hash in the text."""
    tx_label = "🔗 Транзакция" if lang == "ru" else "🔗 Transaction"
    home_label = "🏠 На главную" if lang == "ru" else "🏠 Main menu"
    rows = []
    url = ton_explorer_url(tx_hash) if tx_hash else None
    if url:
        rows.append([{"text": tx_label, "url": url}])
    rows.append([{"text": home_label, "callback_data": "back_to_menu"}])
    return {"inline_keyboard": rows}


async def notify_user(
    db,
    user_doc_or_id: Any,
    title: str,
    message: str,
    type_key: str = "system",
    priority: str = "info",
    payload: Optional[Dict[str, Any]] = None,
    image_url: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    add_home_button: bool = False,
    telegram_message: Optional[str] = None,
) -> None:
    """Send a notification in-app + telegram + WS push. Best-effort.

    ``add_home_button`` attaches a "🏠 На главную" inline button to the Telegram
    message. ``reply_markup`` lets callers pass a fully custom inline keyboard
    (takes precedence over ``add_home_button``).

    ``telegram_message`` lets callers send DIFFERENT text to Telegram than what
    is stored for the in-app notification. Used so the web app keeps the full
    transaction hash inline (rendered as styled HTML) while the bot shows a
    clean message with a "Транзакция" link button instead of a raw hash.
    """
    user_doc = None
    user_id = None

    if isinstance(user_doc_or_id, dict):
        user_doc = user_doc_or_id
        user_id = user_doc.get("id")
    elif isinstance(user_doc_or_id, str):
        user_id = user_doc_or_id
        try:
            user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        except Exception as e:
            logger.warning(f"notify_user: user lookup failed: {e}")

    if not user_id:
        return

    notif = {
        "id": str(_uuid.uuid4()),
        "user_id": user_id,
        "type": type_key,
        "priority": priority,
        "title": title or "",
        "message": message or "",
        "payload": payload or {},
        "image_url": image_url,
        "read": False,
        # notify_user handles Telegram mirroring inline below, so mark the
        # notification as already-delivered to Telegram. Without this flag the
        # `send_pending_notifications` background job would find the row a few
        # minutes later and send a THIRD duplicate copy prefixed with
        # "🏙️ GRAM City" to the user's chat.
        "telegram_sent": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.notifications.insert_one(dict(notif))
    except Exception as e:
        logger.warning(f"notify_user db insert failed: {e}")

    # Real-time WS push so the bell shakes instantly
    try:
        from core.websocket import manager as ws_manager
        await ws_manager.send_personal({"type": "notification_new", "notification": notif}, user_id)
    except Exception as e:
        logger.debug(f"notify_user ws push failed: {e}")

    # Mirror to Telegram (best-effort). Internal callers pass trusted text with
    # intentional HTML tags (<b>, <code>, …), so we DO NOT escape those — the
    # previous escape converted `<b>` into `&lt;b&gt;` which Telegram then
    # rendered as literal "<b>text</b>" characters instead of bold text.
    if not user_doc:
        return
    chat_id = user_doc.get("telegram_chat_id")
    if not chat_id or not user_doc.get("telegram_notifications", True):
        return

    markup = reply_markup or (HOME_BUTTON_MARKUP if add_home_button else None)
    tg_src = telegram_message if telegram_message is not None else message
    body = f"<b>{title}</b>\n\n{tg_src}" if title else (tg_src or "")

    # Preferred path: send through the live TelegramBot instance. Its
    # `send_message` resolves the bot token dynamically from env/DB on every
    # call and always uses parse_mode="HTML", so HTML tags render correctly and
    # inline keyboards (the "🏠 На главную" button) are supported.
    try:
        from telegram_bot import get_telegram_bot
        bot = get_telegram_bot()
        if bot is not None:
            ok = await bot.send_message(str(chat_id), body, reply_markup=markup)
            if ok:
                return
    except Exception as e:
        logger.debug(f"notify_user bot send failed, falling back: {e}")

    # Fallback: legacy standalone sender (also HTML, supports reply_markup).
    try:
        from telegram_notifications import send_telegram_message
        await send_telegram_message(str(chat_id), body, reply_markup=markup)
    except Exception as e:
        logger.debug(f"notify_user telegram mirror failed: {e}")
