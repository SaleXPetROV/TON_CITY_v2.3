"""Approving and rejecting a withdrawal request — ONE implementation for the admin panel and the Telegram bot.

Before, the bot had its own copy of this logic which had drifted away from the admin panel: it read only the old
«sender_wallet» seed and did not decrypt it, ignored the «withdrawal_wallet» set in «Контракт», was not atomic (two
taps could pay twice) and refunded by wallet only (lost for Telegram-only players). Its errors were invisible, too:
the button press had already been answered, so «Одобрить» / «Отклонить» simply did nothing.

    await approve(db, tx_id)  -> {"status": "completed", "hash": "<tx hash>", "tx": {...}}
    await reject(db, tx_id)   -> {"status": "rejected", "amount": 1.05, "tx": {...}}
    raises WithdrawalError(status_code, detail) — the admin API turns it into an HTTPException.

After either of them the admin's Telegram card of the request (if any) is turned into a result button
(update_admin_card), so the result is the same whether the admin pressed the button in the bot or in the panel.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WithdrawalError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def explorer_url(tx_hash: Optional[str]) -> Optional[str]:
    if not tx_hash or tx_hash == "sent_success":
        return None
    from core.notify import tx_hash_hex
    return f"https://tonviewer.com/transaction/{tx_hash_hex(tx_hash)}"


async def _seed(db) -> Optional[str]:
    from mnemonic_crypto import decrypt_mnemonic
    for typ in ("withdrawal_wallet", "sender_wallet"):
        doc = await db.admin_settings.find_one({"type": typ}, {"_id": 0, "mnemonic": 1})
        if doc and doc.get("mnemonic"):
            seed = decrypt_mnemonic(doc["mnemonic"])
            if seed:
                return seed
    return os.getenv("TON_WALLET_MNEMONIC") or None


def _refund_filter(tx: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    ors = []
    if tx.get("user_id"):
        ors.append({"id": tx["user_id"]})
    w = tx.get("user_wallet") or tx.get("from_address")
    if w:
        ors += [{"wallet_address": w}, {"raw_address": w}]
    raw = tx.get("user_raw_address") or ((user or {}).get("raw_address"))
    if raw:
        ors.append({"raw_address": raw})
    return {"$or": ors} if ors else None


async def approve(db, tx_id: str) -> Dict[str, Any]:
    from core.helpers import find_user
    from ton_integration import ton_client

    # 1. atomic lock: only one approval can ever run for a request
    started = datetime.now(timezone.utc).isoformat()
    tx = await db.transactions.find_one_and_update(       # returns the document as it was (still «pending»)
        {"id": tx_id, "status": "pending"},
        {"$set": {"status": "processing", "processing_started": started}})
    if tx:                                                # (no projection: FerretDB has no findAndModify «fields»)
        tx.pop("_id", None)
        tx.update({"status": "processing", "processing_started": started})
    if not tx:
        existing = await db.transactions.find_one({"id": tx_id}, {"_id": 0, "status": 1})
        if not existing:
            raise WithdrawalError(404, "Заявка не найдена")
        st = existing.get("status")
        raise WithdrawalError(400, {
            "processing": "Заявка уже обрабатывается, дождитесь завершения",
            "completed": "Заявка уже одобрена и выполнена",
            "rejected": "Заявка была отклонена ранее",
        }.get(st, f"Заявка уже обработана (статус: {st})"))

    # 2. destination
    user_wallet = tx.get("user_wallet")
    user = await find_user(db, user_id=tx.get("user_id"), wallet=user_wallet)
    dest = (user or {}).get("raw_address") or (user or {}).get("wallet_address") \
        or tx.get("user_raw_address") or tx.get("to_address") or user_wallet
    if not dest:
        await db.transactions.update_one({"id": tx_id}, {"$set": {"status": "pending"}})
        raise WithdrawalError(400, "Адрес получателя не найден")

    # 3. the payout wallet (Контракт → кошелёк для вывода; then the old sender wallet; then .env)
    seed = await _seed(db)
    if not seed:
        await db.transactions.update_one({"id": tx_id}, {"$set": {"status": "pending"}})
        raise WithdrawalError(500, "Кошелёк для вывода не настроен. Настройте его в разделе «Контракт» в админке.")

    net_amount = float(tx.get("net_amount", 0) or 0)
    commission = float(tx.get("commission", 0) or 0)
    amount_original = float(tx.get("amount_ton", 0) or 0) or (net_amount + commission)
    logger.info(f"📤 withdrawal {tx_id}: net={net_amount}, commission={commission} → {dest}")

    payout_sent = None
    try:
        tx_hash = await ton_client.send_ton_payout(dest_address=dest, amount_ton=net_amount, mnemonics=seed,
                                                   user_username=(user or {}).get("username", ""))
        # from here on the TON has LEFT the wallet: a bookkeeping error must never refund the player
        payout_sent = tx_hash
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.transactions.update_one({"id": tx_id}, {"$set": {
            "status": "completed", "completed_at": now_iso, "blockchain_hash": tx_hash,
            "explorer_url": explorer_url(tx_hash), "from_address": "Система", "to_address": user_wallet}})
        await db.admin_stats.update_one(
            {"type": "treasury"},
            {"$inc": {"withdrawal_fees": commission, "total_withdrawals": net_amount, "total_withdrawals_count": 1}},
            upsert=True)
        try:
            import ledger as _ledger
            await _ledger.record(db, "withdrawal_fee", commission, user_id=tx.get("user_id"), ref=tx_id,
                                 note=f"Вывод {net_amount:g} GRAM")
        except Exception:
            pass
        # the player: in-app + Telegram, in their language, with the hash (copyable) and a «Транзакция» button
        try:
            from core.notify import notify_user_background
            notify_user_background(
                db, tx.get("user_id"), title="✅ Вывод одобрен",
                message=f"💸 Ваш запрос на вывод <b>{net_amount:.4f} GRAM</b> одобрен и отправлен на ваш кошелёк.",
                type_key="withdrawal_approved", priority="success",
                payload={"tx_id": tx_id, "amount": net_amount, "hash": tx_hash},
                i18n_key="withdrawal_approved", i18n_vars={"amount": f"{net_amount:.4f}"}, tx_hash=tx_hash)
        except Exception as e:
            logger.warning(f"withdrawal_approved notify failed: {e}")
        tx.update({"status": "completed", "blockchain_hash": tx_hash})
        await update_admin_card(db, tx)
        return {"status": "completed", "hash": tx_hash, "tx": tx}
    except WithdrawalError:
        raise
    except Exception as e:
        logger.error(f"❌ withdrawal {tx_id} approve error: {e}")
        try:
            from ton_integration import PayoutAmbiguous as _Amb
        except Exception:
            _Amb = ()
        if _Amb and isinstance(e, _Amb):
            logger.critical(f"🚨 withdrawal {tx_id}: payout outcome UNKNOWN ({e}); hash={e.msg_hash}")
            await db.transactions.update_one({"id": tx_id}, {"$set": {
                "status": "needs_review", "blockchain_hash": e.msg_hash or None, "error": str(e),
                "needs_review_at": datetime.now(timezone.utc).isoformat()}})
            raise WithdrawalError(502, "Сеть GRAM не ответила — выплата могла уйти. Заявка помечена для проверки в «Сверке», повторно не одобряйте.")
        if payout_sent:
            logger.critical(f"🚨 withdrawal {tx_id}: payout SENT ({payout_sent}) but bookkeeping failed: {e}")
            try:
                await db.transactions.update_one({"id": tx_id}, {"$set": {
                    "status": "needs_review", "blockchain_hash": payout_sent,
                    "error": f"payout sent, bookkeeping failed: {e}",
                    "needs_review_at": datetime.now(timezone.utc).isoformat()}})
            except Exception:
                pass
            raise WithdrawalError(500, "Выплата отправлена, но запись не сохранилась — заявка помечена для проверки, повторно не одобряйте.")
        # the network refused the payout — the money goes back to the player
        flt = _refund_filter(tx, user)
        if flt:
            await db.users.update_one(flt, {"$inc": {"balance_ton": amount_original}})
        else:
            logger.error(f"❌ withdrawal {tx_id}: no user to refund")
        await db.transactions.update_one({"id": tx_id}, {"$set": {"status": "failed", "error": str(e)}})
        tx.update({"status": "failed", "error": str(e)})
        await update_admin_card(db, tx)
        raise WithdrawalError(502, f"Ошибка сети GRAM: {e}")


async def reject(db, tx_id: str) -> Dict[str, Any]:
    # atomic: pending → rejected first, so two taps can never refund twice
    tx = await db.transactions.find_one_and_update(       # returns the document as it was (still «pending»)
        {"id": tx_id, "status": "pending"},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc).isoformat()}})
    if tx:
        tx.pop("_id", None)
    if not tx:
        existing = await db.transactions.find_one({"id": tx_id}, {"_id": 0, "status": 1})
        if not existing:
            raise WithdrawalError(404, "Заявка не найдена")
        st = existing.get("status")
        raise WithdrawalError(400, {
            "rejected": "Заявка уже была отклонена ранее",
            "completed": "Заявка уже одобрена и выполнена",
            "processing": "Заявка уже обрабатывается, дождитесь завершения",
        }.get(st, f"Невозможно отклонить заявку со статусом: {st}"))
    amount = float(tx.get("amount_ton") or abs(float(tx.get("amount", 0) or 0)))
    flt = _refund_filter(tx)
    res = await db.users.update_one(flt, {"$inc": {"balance_ton": amount}}) if (flt and amount > 0) else None
    if not res or not res.modified_count:
        await db.transactions.update_one({"id": tx_id}, {"$set": {"status": "pending"}, "$unset": {"rejected_at": ""}})
        raise WithdrawalError(404 if amount > 0 else 400,
                              "Пользователь не найден в базе для возврата" if amount > 0 else "Сумма для возврата не указана")
    await db.transactions.update_one({"id": tx_id}, {"$set": {"admin_note": f"Возвращено {amount} GRAM на balance_ton"}})
    try:
        from core.notify import notify_user_background
        notify_user_background(
            db, tx.get("user_id"), title="❌ Вывод отклонён",
            message=(f"💰 Ваш запрос на вывод <b>{amount:.4f} GRAM</b> отклонён администратором.\n\n"
                     f"↩️ Средства возвращены на ваш баланс."),
            type_key="withdrawal_rejected", priority="warning", payload={"tx_id": tx_id, "amount": amount},
            add_home_button=True, i18n_key="withdrawal_rejected", i18n_vars={"amount": f"{amount:.4f}"})
    except Exception as e:
        logger.warning(f"withdrawal_rejected notify failed: {e}")
    tx["status"] = "rejected"
    await update_admin_card(db, tx)
    return {"status": "rejected", "amount": amount, "tx": tx}


# ───────────── the admin's Telegram card of a request ─────────────
def admin_card_text(tx: Dict[str, Any], address: str = "") -> str:
    amount = float(tx.get("amount_ton") or abs(float(tx.get("amount", 0) or 0)))
    net = float(tx.get("net_amount", amount) or 0)
    fee = float(tx.get("commission", 0) or 0)
    addr = address or tx.get("to_address_display") or tx.get("user_wallet") or tx.get("to_address") or "?"
    head = {
        "completed": "✅ <b>ВЫВЕДЕНО</b>", "rejected": "❌ <b>ОТКЛОНЕНО</b>", "failed": "⚠️ <b>ОШИБКА ВЫПЛАТЫ</b>",
        "needs_review": "⚠️ <b>НУЖНА ПРОВЕРКА</b>", "processing": "⏳ <b>ОБРАБАТЫВАЕТСЯ</b>",
    }.get(tx.get("status"), "🔔 <b>НОВАЯ ЗАЯВКА НА ВЫВОД</b>")
    lines = [head, "",
             f"👤 Пользователь: <b>{tx.get('user_username', 'Unknown')}</b>",
             f"💰 Сумма: <b>{amount:.4f} GRAM</b>",
             f"💸 К выплате: <b>{net:.4f} GRAM</b>",
             f"📊 Комиссия: <b>{fee:.4f} GRAM</b>", "",
             f"📍 Адрес: <code>{addr}</code>",
             f"📅 {str(tx.get('created_at', ''))[:16]}"]
    h = tx.get("blockchain_hash")
    if h and h != "sent_success":
        lines += ["", f"🔗 Хэш: <code>{h}</code>"]
    if tx.get("status") == "rejected":
        lines += ["", "↩️ Средства возвращены на баланс игрока."]
    if tx.get("status") == "failed" and tx.get("error"):
        lines += ["", f"Сеть GRAM отказала: {str(tx['error'])[:200]}", "↩️ Средства возвращены на баланс игрока."]
    if tx.get("status") == "needs_review":
        lines += ["", "Выплата могла уйти — проверьте в «Сверке», повторно не одобряйте."]
    return "\n".join(lines)


def admin_card_markup(tx: Dict[str, Any]) -> Dict[str, Any]:
    st = tx.get("status")
    tid = tx.get("id", "")
    if st == "pending":
        return {"inline_keyboard": [[{"text": "✅ Одобрить", "callback_data": f"approve_wd_{tid}"},
                                     {"text": "❌ Отклонить", "callback_data": f"reject_wd_{tid}"}]]}
    url = explorer_url(tx.get("blockchain_hash"))
    if st == "completed":
        btn = {"text": "✅ Выведено — открыть транзакцию", "url": url} if url else \
              {"text": "✅ Выведено", "callback_data": f"wd_done_{tid}"}
    elif st == "rejected":
        btn = {"text": "❌ Отклонено", "callback_data": f"wd_done_{tid}"}
    elif st == "failed":
        btn = {"text": "⚠️ Не выведено — средства возвращены", "callback_data": f"wd_done_{tid}"}
    elif st == "needs_review":
        btn = {"text": "⚠️ Нужна проверка (Сверка)", "url": url} if url else \
              {"text": "⚠️ Нужна проверка (Сверка)", "callback_data": f"wd_done_{tid}"}
    else:
        btn = {"text": "⏳ Обрабатывается…", "callback_data": f"wd_done_{tid}"}
    return {"inline_keyboard": [[btn]]}


async def update_admin_card(db, tx: Dict[str, Any]) -> None:
    """Rewrite the admin's Telegram card of this request: the result instead of «Одобрить / Отклонить»."""
    try:
        card = (await db.transactions.find_one({"id": tx.get("id")}, {"_id": 0, "admin_tg_card": 1}) or {}).get("admin_tg_card")
        if not card or not card.get("chat_id") or not card.get("message_id"):
            return
        from telegram_bot import get_telegram_bot
        bot = get_telegram_bot()
        if not bot:
            return
        await bot.edit_message(card["chat_id"], card["message_id"], admin_card_text(tx, card.get("address", "")),
                               reply_markup=admin_card_markup(tx))
    except Exception as e:
        logger.debug(f"admin withdrawal card update: {e}")
