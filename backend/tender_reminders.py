"""Unanswered tender offers and contract change requests: reminders and expiry.

A seller's offer on a tender (tender_contracts.status = PROPOSED) and a change request on a running contract
(tender_contracts.pending_amendment.status = PENDING) wait for the other side. Nothing forced an answer, so
offers could hang forever. Now (every 30 min, leader scheduler):

  • reminder  — the side that has to answer gets ONE grouped message (Telegram + in-app, in the language chosen in
                the project) once something waits longer than `first_after_h` (2 h), then at most every `repeat_h`
                (12 h) while anything still waits. Button «Open offers» → the right tab of «Trading → Contracts».
  • expiry    — after `expire_h` (72 h) an unanswered offer is closed (status EXPIRED) and a change request
                is closed (pending_amendment.status = EXPIRED); the author is told. No money moves: nothing is frozen
                while an offer is PROPOSED, and a change request moves escrow only when accepted.

Settings: game_settings {type: "tender_reminders"} — admin «Тендеры: напоминания» (routes in this module).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULTS = {"enabled": True, "first_after_h": 2.0, "repeat_h": 12.0, "expire_h": 72.0}
SETTINGS_TYPE = "tender_reminders"
LANGS = ("en", "ru", "es", "zh", "fr", "de", "ja", "ko", "id")

# web path of each tab of «Trading → Contracts»; Telegram opens the Mini App with startapp=go-<sub>
SUB_PATH = {"purchases": "/trading?tab=operations&sub=purchases",
            "supplies": "/trading?tab=operations&sub=supplies"}

T: Dict[str, Dict[str, str]] = {
    "title": {
        "ru": "📋 Вас ждут ответы по контрактам", "en": "📋 Contract offers are waiting for you",
        "es": "📋 Tienes ofertas de contrato pendientes", "zh": "📋 有合约提议等待您处理",
        "fr": "📋 Des offres de contrat vous attendent", "de": "📋 Vertragsangebote warten auf dich",
        "ja": "📋 未回答の契約提案があります", "ko": "📋 응답을 기다리는 계약 제안이 있습니다",
        "id": "📋 Ada penawaran kontrak yang menunggu Anda"},
    "head": {
        "ru": "Непринятых предложений: <b>{n}</b>", "en": "Unanswered offers: <b>{n}</b>",
        "es": "Ofertas sin responder: <b>{n}</b>", "zh": "未处理的提议：<b>{n}</b>",
        "fr": "Offres sans réponse : <b>{n}</b>", "de": "Unbeantwortete Angebote: <b>{n}</b>",
        "ja": "未回答の提案：<b>{n}</b>", "ko": "응답하지 않은 제안: <b>{n}</b>", "id": "Penawaran belum dijawab: <b>{n}</b>"},
    "offer_line": {
        "ru": "• @{who} — {amount} ед./сутки «{res}» на {price} $CITY в сутки", "en": "• @{who} — {amount} units/day of «{res}» for {price} $CITY/day",
        "es": "• @{who} — {amount} ud./día de «{res}» por {price} $CITY/día", "zh": "• @{who} — 每天 {amount} 单位「{res}」，每天 {price} $CITY",
        "fr": "• @{who} — {amount} u./jour de « {res} » pour {price} $CITY/jour", "de": "• @{who} — {amount} Einh./Tag «{res}» für {price} $CITY/Tag",
        "ja": "• @{who} — 「{res}」を1日 {amount} 単位、1日 {price} $CITY", "ko": "• @{who} — 「{res}」 하루 {amount}개, 하루 {price} $CITY",
        "id": "• @{who} — {amount} unit/hari «{res}» seharga {price} $CITY/hari"},
    "amend_line": {
        "ru": "• @{who} предлагает изменить контракт «{res}»: {amount} ед./сутки на {price} $CITY в сутки",
        "en": "• @{who} proposes new terms for «{res}»: {amount} units/day for {price} $CITY/day",
        "es": "• @{who} propone nuevas condiciones para «{res}»: {amount} ud./día por {price} $CITY/día",
        "zh": "• @{who} 提议修改「{res}」合约：每天 {amount} 单位，每天 {price} $CITY",
        "fr": "• @{who} propose de nouvelles conditions pour « {res} » : {amount} u./jour pour {price} $CITY/jour",
        "de": "• @{who} schlägt neue Bedingungen für «{res}» vor: {amount} Einh./Tag für {price} $CITY/Tag",
        "ja": "• @{who} が「{res}」の契約変更を提案：1日 {amount} 単位、1日 {price} $CITY",
        "ko": "• @{who} 님이 「{res}」 계약 변경 제안: 하루 {amount}개, 하루 {price} $CITY",
        "id": "• @{who} mengusulkan syarat baru untuk «{res}»: {amount} unit/hari seharga {price} $CITY/hari"},
    "more": {"ru": "• и ещё {n}", "en": "• and {n} more", "es": "• y {n} más", "zh": "• 还有 {n} 条", "fr": "• et {n} de plus",
             "de": "• und {n} weitere", "ja": "• ほか {n} 件", "ko": "• 외 {n}건", "id": "• dan {n} lainnya"},
    "foot": {
        "ru": "Примите или отклоните их. Без ответа предложение закроется через {h} ч после отправки.",
        "en": "Accept or decline them. Without an answer an offer closes {h} h after it was sent.",
        "es": "Acéptalas o recházalas. Sin respuesta, la oferta se cierra {h} h después de enviarse.",
        "zh": "请接受或拒绝。若未回复，提议将在发出 {h} 小时后关闭。",
        "fr": "Acceptez-les ou refusez-les. Sans réponse, une offre se ferme {h} h après son envoi.",
        "de": "Nimm sie an oder lehne sie ab. Ohne Antwort schließt ein Angebot {h} Std. nach dem Senden.",
        "ja": "承認または拒否してください。回答がない場合、提案は送信から {h} 時間後に終了します。",
        "ko": "수락하거나 거절하세요. 응답이 없으면 제안은 보낸 지 {h}시간 후 종료됩니다.",
        "id": "Terima atau tolak. Tanpa jawaban, penawaran ditutup {h} jam setelah dikirim."},
    "button": {"ru": "📋 Открыть предложения", "en": "📋 Open offers", "es": "📋 Abrir ofertas", "zh": "📋 打开提议",
               "fr": "📋 Ouvrir les offres", "de": "📋 Angebote öffnen", "ja": "📋 提案を開く", "ko": "📋 제안 열기",
               "id": "📋 Buka penawaran"},
    # the author's offer was closed by the 72 h limit
    "exp_title": {"ru": "⌛ Предложение закрыто", "en": "⌛ Offer closed", "es": "⌛ Oferta cerrada", "zh": "⌛ 提议已关闭",
                  "fr": "⌛ Offre fermée", "de": "⌛ Angebot geschlossen", "ja": "⌛ 提案が終了しました", "ko": "⌛ 제안이 종료되었습니다",
                  "id": "⌛ Penawaran ditutup"},
    "exp_offer": {
        "ru": "@{who} не ответил на ваше предложение «{res}» ({amount} ед./сутки на {price} $CITY в сутки) за {h} ч — оно закрыто. Можете отправить новое этому или другому покупателю.",
        "en": "@{who} did not answer your offer «{res}» ({amount} units/day for {price} $CITY/day) within {h} h — it is closed. You can send a new one to this or another buyer.",
        "es": "@{who} no respondió a tu oferta «{res}» ({amount} ud./día por {price} $CITY/día) en {h} h; se ha cerrado. Puedes enviar una nueva a este u otro comprador.",
        "zh": "@{who} 在 {h} 小时内未回复您的提议「{res}」（每天 {amount} 单位，每天 {price} $CITY），提议已关闭。您可以向该买家或其他买家发送新提议。",
        "fr": "@{who} n'a pas répondu à votre offre « {res} » ({amount} u./jour pour {price} $CITY/jour) en {h} h : elle est fermée. Vous pouvez en envoyer une nouvelle à cet acheteur ou à un autre.",
        "de": "@{who} hat dein Angebot «{res}» ({amount} Einh./Tag für {price} $CITY/Tag) nicht innerhalb von {h} Std. beantwortet – es ist geschlossen. Du kannst diesem oder einem anderen Käufer ein neues senden.",
        "ja": "@{who} が {h} 時間以内にあなたの提案「{res}」（1日 {amount} 単位、1日 {price} $CITY）に回答しなかったため、提案は終了しました。この買い手や他の買い手に新しい提案を送れます。",
        "ko": "@{who} 님이 {h}시간 동안 「{res}」 제안(하루 {amount}개, 하루 {price} $CITY)에 응답하지 않아 제안이 종료되었습니다. 이 구매자나 다른 구매자에게 새 제안을 보낼 수 있습니다.",
        "id": "@{who} tidak menjawab penawaran Anda «{res}» ({amount} unit/hari seharga {price} $CITY/hari) dalam {h} jam — penawaran ditutup. Anda bisa mengirim yang baru ke pembeli ini atau pembeli lain."},
    "exp_amend": {
        "ru": "@{who} не ответил на ваше предложение изменить контракт «{res}» за {h} ч — оно закрыто, контракт работает на прежних условиях.",
        "en": "@{who} did not answer your proposed change to the «{res}» contract within {h} h — it is closed, the contract keeps its current terms.",
        "es": "@{who} no respondió a tu propuesta de cambio del contrato «{res}» en {h} h; se ha cerrado y el contrato mantiene sus condiciones.",
        "zh": "@{who} 在 {h} 小时内未回复您对「{res}」合约的修改提议，提议已关闭，合约保持原条件。",
        "fr": "@{who} n'a pas répondu à votre demande de modification du contrat « {res} » en {h} h : elle est fermée, le contrat garde ses conditions.",
        "de": "@{who} hat deine Änderung am Vertrag «{res}» nicht innerhalb von {h} Std. beantwortet – sie ist geschlossen, der Vertrag läuft zu den bisherigen Bedingungen.",
        "ja": "@{who} が {h} 時間以内に「{res}」契約の変更提案に回答しなかったため終了しました。契約は現在の条件のままです。",
        "ko": "@{who} 님이 {h}시간 동안 「{res}」 계약 변경 제안에 응답하지 않아 종료되었습니다. 계약은 기존 조건으로 유지됩니다.",
        "id": "@{who} tidak menjawab usulan perubahan kontrak «{res}» Anda dalam {h} jam — usulan ditutup, kontrak tetap dengan syarat sekarang."},
    # the other side took its offer / change request back (in-app only)
    "wd_title": {"ru": "↩️ Предложение отозвано", "en": "↩️ Offer withdrawn", "es": "↩️ Oferta retirada", "zh": "↩️ 提议已撤回",
                 "fr": "↩️ Offre retirée", "de": "↩️ Angebot zurückgezogen", "ja": "↩️ 提案が取り下げられました",
                 "ko": "↩️ 제안이 철회되었습니다", "id": "↩️ Penawaran ditarik"},
    "wd_offer": {
        "ru": "@{who} отозвал предложение «{res}» ({amount} ед./сутки на {price} $CITY в сутки).",
        "en": "@{who} withdrew the offer «{res}» ({amount} units/day for {price} $CITY/day).",
        "es": "@{who} retiró la oferta «{res}» ({amount} ud./día por {price} $CITY/día).",
        "zh": "@{who} 撤回了提议「{res}」（每天 {amount} 单位，每天 {price} $CITY）。",
        "fr": "@{who} a retiré l'offre « {res} » ({amount} u./jour pour {price} $CITY/jour).",
        "de": "@{who} hat das Angebot «{res}» ({amount} Einh./Tag für {price} $CITY/Tag) zurückgezogen.",
        "ja": "@{who} が提案「{res}」（1日 {amount} 単位、1日 {price} $CITY）を取り下げました。",
        "ko": "@{who} 님이 「{res}」 제안(하루 {amount}개, 하루 {price} $CITY)을 철회했습니다.",
        "id": "@{who} menarik penawaran «{res}» ({amount} unit/hari seharga {price} $CITY/hari)."},
    "wd_amend": {
        "ru": "@{who} отозвал предложение изменить контракт «{res}». Контракт работает на прежних условиях.",
        "en": "@{who} withdrew the proposed change to the «{res}» contract. The contract keeps its current terms.",
        "es": "@{who} retiró la propuesta de cambio del contrato «{res}». El contrato mantiene sus condiciones.",
        "zh": "@{who} 撤回了对「{res}」合约的修改提议。合约保持原条件。",
        "fr": "@{who} a retiré sa demande de modification du contrat « {res} ». Le contrat garde ses conditions.",
        "de": "@{who} hat die Änderung am Vertrag «{res}» zurückgezogen. Der Vertrag läuft zu den bisherigen Bedingungen.",
        "ja": "@{who} が「{res}」契約の変更提案を取り下げました。契約は現在の条件のままです。",
        "ko": "@{who} 님이 「{res}」 계약 변경 제안을 철회했습니다. 계약은 기존 조건으로 유지됩니다.",
        "id": "@{who} menarik usulan perubahan kontrak «{res}». Kontrak tetap dengan syarat sekarang."},
}

# why an accept / reject / withdraw no longer works (API error text, in the player's language)
CLOSED: Dict[str, Dict[str, str]] = {
    "WITHDRAWN": {"ru": "Продавец уже отозвал это предложение.", "en": "The seller has already withdrawn this offer.",
                  "es": "El vendedor ya retiró esta oferta.", "zh": "卖家已撤回此提议。", "fr": "Le vendeur a déjà retiré cette offre.",
                  "de": "Der Verkäufer hat dieses Angebot bereits zurückgezogen.", "ja": "販売者はすでにこの提案を取り下げました。",
                  "ko": "판매자가 이미 이 제안을 철회했습니다.", "id": "Penjual sudah menarik penawaran ini."},
    "EXPIRED": {"ru": "Срок предложения истёк — оно закрыто.", "en": "This offer has expired and is closed.",
                "es": "Esta oferta ha caducado y está cerrada.", "zh": "此提议已过期并关闭。", "fr": "Cette offre a expiré et est fermée.",
                "de": "Dieses Angebot ist abgelaufen und geschlossen.", "ja": "この提案は期限切れで終了しました。",
                "ko": "이 제안은 만료되어 종료되었습니다.", "id": "Penawaran ini kedaluwarsa dan ditutup."},
    "REJECTED": {"ru": "Предложение уже отклонено.", "en": "This offer has already been declined.",
                 "es": "Esta oferta ya fue rechazada.", "zh": "此提议已被拒绝。", "fr": "Cette offre a déjà été refusée.",
                 "de": "Dieses Angebot wurde bereits abgelehnt.", "ja": "この提案はすでに拒否されました。",
                 "ko": "이 제안은 이미 거절되었습니다.", "id": "Penawaran ini sudah ditolak."},
    "ACCEPTED": {"ru": "Предложение уже принято — контракт заключён.", "en": "This offer has already been accepted — the contract is signed.",
                 "es": "Esta oferta ya fue aceptada: el contrato está firmado.", "zh": "此提议已被接受，合约已签订。",
                 "fr": "Cette offre a déjà été acceptée : le contrat est signé.", "de": "Dieses Angebot wurde bereits angenommen – der Vertrag ist geschlossen.",
                 "ja": "この提案はすでに承認され、契約が成立しています。", "ko": "이 제안은 이미 수락되어 계약이 체결되었습니다.",
                 "id": "Penawaran ini sudah diterima — kontrak sudah dibuat."},
    "AMENDMENT_CLOSED": {"ru": "Это предложение изменений уже закрыто: его приняли, отклонили, отозвали или истёк срок.",
                         "en": "This change request is already closed: it was accepted, declined, withdrawn or expired.",
                         "es": "Esta propuesta de cambio ya está cerrada: fue aceptada, rechazada, retirada o caducó.",
                         "zh": "此修改提议已关闭：已被接受、拒绝、撤回或过期。",
                         "fr": "Cette demande de modification est déjà fermée : acceptée, refusée, retirée ou expirée.",
                         "de": "Diese Änderungsanfrage ist bereits geschlossen: angenommen, abgelehnt, zurückgezogen oder abgelaufen.",
                         "ja": "この変更提案はすでに終了しています（承認・拒否・取り下げ・期限切れ）。",
                         "ko": "이 변경 제안은 이미 종료되었습니다(수락, 거절, 철회 또는 만료).",
                         "id": "Usulan perubahan ini sudah ditutup: diterima, ditolak, ditarik, atau kedaluwarsa."},
    "OTHER": {"ru": "Предложение уже закрыто.", "en": "This offer is already closed.", "es": "Esta oferta ya está cerrada.",
              "zh": "此提议已关闭。", "fr": "Cette offre est déjà fermée.", "de": "Dieses Angebot ist bereits geschlossen.",
              "ja": "この提案はすでに終了しています。", "ko": "이 제안은 이미 종료되었습니다.", "id": "Penawaran ini sudah ditutup."},
}
_ACCEPTED_STATES = {"ACTIVE", "PENDING_FUNDS", "PENDING_RESOURCES", "PENDING_STORAGE", "COMPLETED", "BROKEN"}


def _t(key: str, lang: str, **kw) -> str:
    d = T[key]
    s = d.get(lang) or d["en"]
    try:
        return s.format(**kw)
    except (KeyError, IndexError, ValueError):
        return s


def closed_offer_text(status: Optional[str], lang: str) -> str:
    key = status if status in CLOSED else ("ACCEPTED" if status in _ACCEPTED_STATES else "OTHER")
    d = CLOSED[key]
    return d.get(lang) or d["en"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def get_settings(db) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    try:
        doc = await db.game_settings.find_one({"type": SETTINGS_TYPE}, {"_id": 0}) or {}
        for k in DEFAULTS:
            if k in doc:
                out[k] = doc[k]
    except Exception:
        pass
    return out


def _price_txt(c: Dict[str, Any], price: float, amount: Any = None) -> str:
    """The DAILY cost in $CITY — unambiguous (prices are per unit, every tier)."""
    amt = float(amount if amount is not None else (c.get("daily_amount") or 0))
    return f"{amt * float(price or 0):.2f}"


async def _res_name(db, rid: str, lang: str) -> str:
    try:
        from core.chest_notify import resource_name
        return await resource_name(db, rid, lang)
    except Exception:
        return rid


async def _lang(db, user: Optional[Dict[str, Any]]) -> str:
    from core.notif_i18n import user_lang
    return user_lang(user)


async def open_links(db, sub: str) -> Dict[str, Optional[str]]:
    """Where the «Open offers» button leads: the Mini App (startapp=go-<sub>) or the website path."""
    tg = None
    try:
        from core.ref_links import miniapp_base
        base = await miniapp_base(db)
        if base:
            tg = f"{base}{'&' if '?' in base else '?'}startapp=go-{sub}"
    except Exception:
        tg = None
    web = None
    try:
        from core.notify import resolve_miniapp_url
        site = await resolve_miniapp_url(db)
        if site and "t.me/" not in site:
            web = site + SUB_PATH[sub]
    except Exception:
        web = None
    return {"tg": tg or web, "path": SUB_PATH[sub]}


async def _send(db, user: Dict[str, Any], title: str, body: str, type_key: str, sub: str,
                telegram: bool = True, payload: Optional[Dict[str, Any]] = None) -> None:
    from core.notify import notify_user
    lang = await _lang(db, user)
    links = await open_links(db, sub)
    markup = None
    if telegram and links["tg"]:
        markup = {"inline_keyboard": [[{"text": _t("button", lang), "url": links["tg"]}]]}
    pl = {"open_path": links["path"], "open_label": _t("button", lang), **(payload or {})}
    await notify_user(db, user, title=title, message=body, type_key=type_key, priority="warning",
                      payload=pl, reply_markup=markup, telegram=telegram, pretranslated=True)


# ───────────────────────── withdraw notices ─────────────────────────

async def notify_withdrawn(db, contract: Dict[str, Any], kind: str = "offer", author_id: Optional[str] = None) -> None:
    """In-app notice to the side that was asked (no Telegram: nothing to do for them)."""
    if kind == "offer":
        to_id, who = contract.get("buyer_id"), contract.get("seller_username") or "seller"
        amount, price = contract.get("daily_amount"), float(contract.get("price_per_unit") or 0)
        sub = "purchases"
    else:
        am = contract.get("pending_amendment") or {}
        author_id = author_id or am.get("proposed_by_id")
        to_id = contract["seller_id"] if author_id == contract.get("buyer_id") else contract.get("buyer_id")
        who = (contract.get("buyer_username") if author_id == contract.get("buyer_id") else contract.get("seller_username")) or "user"
        amount, price = am.get("new_daily_amount"), float(am.get("new_price_per_unit") or 0)
        sub = "purchases" if to_id == contract.get("buyer_id") else "supplies"
    user = await db.users.find_one({"id": to_id}, {"_id": 0})
    if not user:
        return
    lang = await _lang(db, user)
    res = await _res_name(db, contract.get("resource_type") or "", lang)
    body = _t("wd_offer" if kind == "offer" else "wd_amend", lang, who=who, res=res,
              amount=int(float(amount or 0)), price=_price_txt(contract, price, amount))
    await _send(db, user, _t("wd_title", lang), body, "tender_offer_withdrawn", sub, telegram=False,
                payload={"contract_id": contract.get("id"), "tender_id": contract.get("tender_id"), "kind": "tender_withdrawn"})


# ───────────────────────── the periodic pass ─────────────────────────

async def _expire(db, cfg: Dict[str, Any], now: datetime) -> Dict[str, int]:
    """Close what waited longer than expire_h; tell the author."""
    out = {"offers": 0, "amendments": 0}
    cutoff = (now - timedelta(hours=float(cfg["expire_h"]))).isoformat()
    h = int(round(float(cfg["expire_h"])))
    async for c in db.tender_contracts.find({"status": "PROPOSED", "created_at": {"$lte": cutoff}}, {"_id": 0}).limit(500):
        r = await db.tender_contracts.update_one({"id": c["id"], "status": "PROPOSED"},
                                                 {"$set": {"status": "EXPIRED", "expired_at": now.isoformat(),
                                                           "broken_at": now.isoformat()}})
        if not getattr(r, "modified_count", 0):
            continue
        out["offers"] += 1
        seller = await db.users.find_one({"id": c.get("seller_id")}, {"_id": 0})
        if seller:
            lang = await _lang(db, seller)
            res = await _res_name(db, c.get("resource_type") or "", lang)
            body = _t("exp_offer", lang, who=c.get("buyer_username") or "buyer", res=res, h=h,
                      amount=int(float(c.get("daily_amount") or 0)), price=_price_txt(c, float(c.get("price_per_unit") or 0)))
            try:
                await _send(db, seller, _t("exp_title", lang), body, "tender_offer_expired", "supplies",
                            payload={"contract_id": c["id"], "tender_id": c.get("tender_id"), "kind": "tender_expired"})
            except Exception as e:
                logger.warning(f"tender expiry notify failed: {e}")
        try:
            from core.websocket import manager as ws
            await ws.send_personal({"type": "tender_contract_expired", "contract_id": c["id"]}, c.get("buyer_id"))
        except Exception:
            pass
    async for c in db.tender_contracts.find({"pending_amendment.status": "PENDING",
                                             "pending_amendment.proposed_at": {"$lte": cutoff}}, {"_id": 0}).limit(500):
        am = c.get("pending_amendment") or {}
        r = await db.tender_contracts.update_one(
            {"id": c["id"], "pending_amendment.id": am.get("id"), "pending_amendment.status": "PENDING"},
            {"$set": {"pending_amendment.status": "EXPIRED", "pending_amendment.resolved_at": now.isoformat()}})
        if not getattr(r, "modified_count", 0):
            continue
        out["amendments"] += 1
        author = await db.users.find_one({"id": am.get("proposed_by_id")}, {"_id": 0})
        if author:
            other_name = c.get("seller_username") if am.get("proposed_by") == "buyer" else c.get("buyer_username")
            lang = await _lang(db, author)
            res = await _res_name(db, c.get("resource_type") or "", lang)
            sub = "purchases" if am.get("proposed_by") == "buyer" else "supplies"
            try:
                await _send(db, author, _t("exp_title", lang), _t("exp_amend", lang, who=other_name or "user", res=res, h=h),
                            "tender_amendment_expired", sub, payload={"contract_id": c["id"], "kind": "tender_expired"})
            except Exception as e:
                logger.warning(f"amendment expiry notify failed: {e}")
    return out


async def _waiting_by_user(db, older_than: str) -> Dict[str, List[Dict[str, Any]]]:
    """user_id → what waits for THEIR answer (offers on their tenders + change requests from the other side)."""
    waits: Dict[str, List[Dict[str, Any]]] = {}
    async for c in db.tender_contracts.find({"status": "PROPOSED"}, {"_id": 0}).limit(5000):
        waits.setdefault(c["buyer_id"], []).append({"kind": "offer", "c": c, "at": c.get("created_at") or "",
                                                    "old": (c.get("created_at") or "") <= older_than})
    async for c in db.tender_contracts.find({"pending_amendment.status": "PENDING"}, {"_id": 0}).limit(5000):
        am = c.get("pending_amendment") or {}
        to_id = c["seller_id"] if am.get("proposed_by") == "buyer" else c["buyer_id"]
        waits.setdefault(to_id, []).append({"kind": "amend", "c": c, "at": am.get("proposed_at") or "",
                                            "old": (am.get("proposed_at") or "") <= older_than})
    return waits


async def _remind(db, cfg: Dict[str, Any], now: datetime) -> int:
    first = (now - timedelta(hours=float(cfg["first_after_h"]))).isoformat()
    repeat_cut = now - timedelta(hours=float(cfg["repeat_h"]))
    sent = 0
    for uid, items in (await _waiting_by_user(db, first)).items():
        if not any(x["old"] for x in items):          # nothing waits long enough yet
            continue
        user = await db.users.find_one({"id": uid}, {"_id": 0})
        if not user:
            continue
        last = _parse(user.get("tender_reminder_at"))
        if last and last > repeat_cut:
            continue
        # claim the slot first (two leaders / a re-run never send twice)
        claim = {"id": uid, "$or": [{"tender_reminder_at": {"$exists": False}}, {"tender_reminder_at": None},
                                    {"tender_reminder_at": {"$lte": repeat_cut.isoformat()}}]}
        r = await db.users.update_one(claim, {"$set": {"tender_reminder_at": now.isoformat()}})
        if not getattr(r, "modified_count", 0):
            continue
        lang = await _lang(db, user)
        items.sort(key=lambda x: x["at"])
        lines = [_t("head", lang, n=len(items))]
        for x in items[:3]:
            c = x["c"]
            res = await _res_name(db, c.get("resource_type") or "", lang)
            if x["kind"] == "offer":
                lines.append(_t("offer_line", lang, who=c.get("seller_username") or "seller", res=res,
                                amount=int(float(c.get("daily_amount") or 0)),
                                price=_price_txt(c, float(c.get("price_per_unit") or 0))))
            else:
                am = c.get("pending_amendment") or {}
                who = c.get("buyer_username") if am.get("proposed_by") == "buyer" else c.get("seller_username")
                lines.append(_t("amend_line", lang, who=who or "user", res=res,
                                amount=int(float(am.get("new_daily_amount") or 0)),
                                price=_price_txt(c, float(am.get("new_price_per_unit") or 0), am.get("new_daily_amount"))))
        if len(items) > 3:
            lines.append(_t("more", lang, n=len(items) - 3))
        lines.append("")
        lines.append(_t("foot", lang, h=int(round(float(cfg["expire_h"])))))
        # the tab that holds most of them: offers on my tenders → «Закупки»; change requests from my buyers → «Поставки»
        sub = "purchases"
        n_sup = sum(1 for x in items if x["kind"] == "amend" and x["c"].get("seller_id") == uid)
        if n_sup * 2 > len(items):
            sub = "supplies"
        try:
            await _send(db, user, _t("title", lang), "\n".join(lines), "tender_offers_pending", sub,
                        payload={"kind": "tender_reminder", "count": len(items)})
            sent += 1
        except Exception as e:
            logger.warning(f"tender reminder failed for {uid}: {e}")
    return sent


async def run(db) -> Dict[str, Any]:
    cfg = await get_settings(db)
    if not cfg.get("enabled", True):
        return {"skipped": "disabled"}
    now = _now()
    expired = await _expire(db, cfg, now)
    reminded = await _remind(db, cfg, now)
    return {"expired": expired, "reminded": reminded}


def create_admin_router(db, get_current_admin):
    """Admin: GET/PUT /api/admin/tender-reminders — the three intervals and the switch."""
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/api/admin/tender-reminders", tags=["admin-tenders"])

    class Patch(BaseModel):
        enabled: Optional[bool] = None
        first_after_h: Optional[float] = None
        repeat_h: Optional[float] = None
        expire_h: Optional[float] = None

    @router.get("")
    async def get_(admin=Depends(get_current_admin)):
        return await get_settings(db)

    @router.put("")
    async def put_(p: Patch, admin=Depends(get_current_admin)):
        patch = {k: v for k, v in p.dict().items() if v is not None}
        for k in ("first_after_h", "repeat_h", "expire_h"):
            if k in patch and not (0.25 <= float(patch[k]) <= 24 * 30):
                raise HTTPException(status_code=400, detail="Интервал должен быть от 15 минут до 30 дней")
        cur = {**(await get_settings(db)), **patch}
        if float(cur["first_after_h"]) >= float(cur["expire_h"]):
            raise HTTPException(status_code=400, detail="Первое напоминание должно приходить раньше, чем предложение закроется")
        await db.game_settings.update_one({"type": SETTINGS_TYPE}, {"$set": {**patch, "type": SETTINGS_TYPE}}, upsert=True)
        return await get_settings(db)

    return router
