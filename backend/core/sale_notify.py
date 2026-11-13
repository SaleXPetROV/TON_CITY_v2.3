"""«Your resources were sold» — the seller's notification, in every project language.

Who bought is named: a player → «@name купил …», the City Market → «Город купил …» (its own title too).
Used by the player purchase (server /market/buy) and by the City Market / admin buyout (_admin_buyout_apply_sale).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

LANGS = ("en", "ru", "es", "zh", "fr", "de", "ja", "ko", "id")

TITLE = {
    "player": {"ru": "💰 Ресурсы проданы на маркете", "en": "💰 Resources sold on the market", "es": "💰 Recursos vendidos en el mercado",
               "zh": "💰 资源已在市场售出", "fr": "💰 Ressources vendues sur le marché", "de": "💰 Ressourcen auf dem Markt verkauft",
               "ja": "💰 マーケットで資源が売れました", "ko": "💰 마켓에서 자원이 판매되었습니다", "id": "💰 Sumber daya terjual di pasar"},
    "city": {"ru": "🏙 Город купил ваш лот", "en": "🏙 The City bought your lot", "es": "🏙 La Ciudad compró tu lote",
             "zh": "🏙 城市收购了您的商品", "fr": "🏙 La Ville a acheté votre lot", "de": "🏙 Die Stadt hat dein Los gekauft",
             "ja": "🏙 市があなたの出品を購入しました", "ko": "🏙 시가 판매 물품을 구매했습니다", "id": "🏙 Kota membeli lot Anda"},
}
BODY = {
    "ru": "{buyer} купил {amount} ед. «{res}» за {gross_ton} GRAM ({gross_city} $CITY).\nВам начислено после налога: {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
    "en": "{buyer} bought {amount} × «{res}» for {gross_ton} GRAM ({gross_city} $CITY).\nYou received after tax: {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
    "es": "{buyer} compró {amount} ud. de «{res}» por {gross_ton} GRAM ({gross_city} $CITY).\nRecibiste tras impuestos: {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
    "zh": "{buyer} 以 {gross_ton} GRAM（{gross_city} $CITY）购买了 {amount} 单位「{res}」。\n税后到账：{net_ton} GRAM（{net_city} $CITY）{bonus}。{credit}",
    "fr": "{buyer} a acheté {amount} u. de « {res} » pour {gross_ton} GRAM ({gross_city} $CITY).\nVous avez reçu après impôt : {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
    "de": "{buyer} hat {amount} Einh. «{res}» für {gross_ton} GRAM ({gross_city} $CITY) gekauft.\nDu hast nach Steuern erhalten: {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
    "ja": "{buyer} が「{res}」{amount} 単位を {gross_ton} GRAM（{gross_city} $CITY）で購入しました。\n税引き後の受取額：{net_ton} GRAM（{net_city} $CITY）{bonus}。{credit}",
    "ko": "{buyer}이(가) 「{res}」 {amount}개를 {gross_ton} GRAM({gross_city} $CITY)에 구매했습니다.\n세후 지급액: {net_ton} GRAM({net_city} $CITY){bonus}.{credit}",
    "id": "{buyer} membeli {amount} unit «{res}» seharga {gross_ton} GRAM ({gross_city} $CITY).\nAnda menerima setelah pajak: {net_ton} GRAM ({net_city} $CITY){bonus}.{credit}",
}
CITY = {"ru": "Город", "en": "The City", "es": "La Ciudad", "zh": "城市", "fr": "La Ville", "de": "Die Stadt",
        "ja": "市", "ko": "시", "id": "Kota"}
SOMEONE = {"ru": "Покупатель", "en": "A buyer", "es": "Un comprador", "zh": "一位买家", "fr": "Un acheteur", "de": "Ein Käufer",
           "ja": "購入者", "ko": "구매자", "id": "Seorang pembeli"}
BONUS = {"ru": " на бонусный баланс", "en": " to your bonus balance", "es": " en tu saldo de bonificación", "zh": "（计入奖励余额）",
         "fr": " sur votre solde bonus", "de": " auf dein Bonusguthaben", "ja": "（ボーナス残高へ）", "ko": " (보너스 잔액으로)",
         "id": " ke saldo bonus Anda"}
CREDIT = {"ru": "\nНа погашение кредита направлено: {ton} GRAM ({city} $CITY).",
          "en": "\nAuto-paid to your credit: {ton} GRAM ({city} $CITY).",
          "es": "\nDestinado a tu crédito: {ton} GRAM ({city} $CITY).",
          "zh": "\n已自动偿还贷款：{ton} GRAM（{city} $CITY）。",
          "fr": "\nVersé au remboursement de votre crédit : {ton} GRAM ({city} $CITY).",
          "de": "\nAutomatisch für deinen Kredit verwendet: {ton} GRAM ({city} $CITY).",
          "ja": "\nローン返済に充当：{ton} GRAM（{city} $CITY）。",
          "ko": "\n대출 상환에 사용: {ton} GRAM({city} $CITY).",
          "id": "\nDibayarkan otomatis ke kredit Anda: {ton} GRAM ({city} $CITY)."}


def _city(x: float) -> str:
    """$CITY with up to 2 decimals, no trailing zeros: 27, 22.95."""
    return f"{round(float(x) * 1000, 2):g}"


def _pick(d: Dict[str, str], lang: str) -> str:
    return d.get(lang) or d["en"]


def render(lang: str, *, city: bool, buyer_name: Optional[str], amount: Any, res: str, gross_ton: float,
           net_ton: float, credit_ton: float = 0.0, to_bonus: bool = False) -> tuple:
    lang = lang if lang in LANGS else "en"
    if city:
        buyer = _pick(CITY, lang)
    else:
        name = str(buyer_name or "").strip().lstrip("@")
        buyer = f"@{name}" if name else _pick(SOMEONE, lang)
    credit = _pick(CREDIT, lang).format(ton=f"{credit_ton:.4f}", city=_city(credit_ton)) if credit_ton and credit_ton > 0 else ""
    amt = int(amount) if float(amount) == int(float(amount)) else amount
    body = _pick(BODY, lang).format(
        buyer=buyer, amount=amt, res=res, gross_ton=f"{gross_ton:.4f}", gross_city=_city(gross_ton),
        net_ton=f"{net_ton:.4f}", net_city=_city(net_ton), bonus=_pick(BONUS, lang) if to_bonus else "", credit=credit)
    return _pick(TITLE["city" if city else "player"], lang), body


async def notify_sale(db, seller_doc: Dict[str, Any], *, city: bool, buyer_name: Optional[str], amount: Any,
                      resource: str, gross_ton: float, net_ton: float, credit_ton: float = 0.0, to_bonus: bool = False,
                      payload: Optional[Dict[str, Any]] = None, background: bool = False) -> None:
    from core.notif_i18n import user_lang
    lang = user_lang(seller_doc)
    try:
        from core.chest_notify import resource_name
        res = await resource_name(db, resource, lang)
    except Exception:
        res = resource
    title, body = render(lang, city=city, buyer_name=buyer_name, amount=amount, res=res, gross_ton=gross_ton,
                         net_ton=net_ton, credit_ton=credit_ton, to_bonus=to_bonus)
    pl = {"resource_type": resource, "amount": amount, "received_ton": net_ton, "gross_ton": gross_ton,
          "buyer": "city" if city else (buyer_name or ""), **(payload or {})}
    from core import notify as _n
    kw = dict(title=title, message=body, type_key="market_sold", priority="success", payload=pl, pretranslated=True)
    if background:
        _n.notify_user_background(db, seller_doc, **kw)
    else:
        await _n.notify_user(db, seller_doc, **kw)
