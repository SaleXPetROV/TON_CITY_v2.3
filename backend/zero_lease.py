"""Level-0 (test) business 3-day lease + 48h market-lot soft-expiration.

Lifecycle additions on top of ``zero_business.py``:
  * A claimed level-0 business carries ``expires_at`` = claim_time + 3 days.
  * 12h before expiry the owner gets a localized "lease expiring" notice.
  * At expiry the business is removed, its plot becomes free again, the auto
    marketplace lot is delisted and all the owner's active resource orders tied
    to it are cancelled (resources returned). The owner then gets a notice.
  * Any resource lot that sits unsold on the market for >= 48h is auto-cancelled
    and its resources returned to the seller with a "goods returned" notice.
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

ZERO_LEASE_DAYS = 3
# Пороги напоминаний об окончании аренды (в часах до истечения): за 24ч, 12ч и 3ч.
ZERO_LEASE_WARN_THRESHOLDS = [24, 12, 3]
ZERO_LEASE_WARN_HOURS = 12  # для обратной совместимости (текст/старые вызовы)
MARKET_LOT_MAX_HOURS = 48
# Level-0 sellers: the system auto-buys their unsold resource lots after 24h.
ZERO_BUYBACK_HOURS = 24


def _now():
    return datetime.now(timezone.utc)


def _parse_iso(v):
    if not v:
        return None
    try:
        s = str(v).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def compute_expires_at(now=None) -> str:
    now = now or _now()
    return (now + timedelta(days=ZERO_LEASE_DAYS)).isoformat()


def _biz_name(business: dict, lang: str) -> str:
    from business_config import BUSINESSES, BUSINESS_KEY_MAP
    bt = business.get("business_type")
    cfg = BUSINESSES.get(BUSINESS_KEY_MAP.get(bt, bt)) or BUSINESSES.get(bt) or {}
    names = cfg.get("name", {}) or {}
    return names.get(lang) or names.get("en") or names.get("ru") or bt


def _res_name(resource: str, lang: str) -> str:
    from business_config import RESOURCE_TYPES
    meta = RESOURCE_TYPES.get(resource, {}) or {}
    return meta.get(f"name_{lang}") or meta.get("name_en") or meta.get("name_ru") or resource


async def _find_owner_user(db, business: dict):
    owner = business.get("owner")
    if not owner:
        return None
    return await db.users.find_one(
        {"$or": [{"id": owner}, {"wallet_address": owner}]}, {"_id": 0}
    )


# ─────────────────────────── 3-day lease job ────────────────────────────────

async def process_zero_lease(db) -> dict:
    """Напоминания за 24ч/12ч/3ч до конца аренды; удаление бизнеса + освобождение
    участка по истечении. Перед проходом возвращает в работу ошибочно изъятые,
    но ещё арендованные бизнесы 0-го уровня."""
    now = _now()
    warned = 0
    expired = 0

    # 0) Восстановить в работу бизнесы 0-го уровня, которые были ошибочно изъяты
    #    (например, старым джобом неактивности), но аренда ещё действует.
    restored = await restore_wrongly_seized_zero_leases(db)

    cursor = db.businesses.find({
        "level": 0,
        "is_zero_business": True,
        "is_trial": {"$ne": True},
        "expires_at": {"$ne": None},
    })
    async for biz in cursor:
        exp = _parse_iso(biz.get("expires_at"))
        if not exp:
            continue
        if exp <= now:
            try:
                await _expire_zero_business(db, biz)
                expired += 1
            except Exception as e:
                logger.error(f"process_zero_lease expire failed for {biz.get('id')}: {e}")
            continue
        # Напоминания на порогах 24ч / 12ч / 3ч. Каждый порог отправляется один раз;
        # уже отправленные пороги храним в массиве zero_lease_warns.
        try:
            sent = set(int(h) for h in (biz.get("zero_lease_warns") or []))
        except (TypeError, ValueError):
            sent = set()
        hours_left = (exp - now).total_seconds() / 3600.0
        due = [h for h in ZERO_LEASE_WARN_THRESHOLDS if h not in sent and hours_left <= h]
        if not due:
            continue
        # Отправляем только САМЫЙ близкий подходящий порог (наименьший),
        # остальные пройденные пороги помечаем отправленными без дублей.
        threshold = min(due)
        try:
            from core.notify import notify_user
            from core.notif_i18n import user_lang
            user = await _find_owner_user(db, biz)
            if user:
                lang = user_lang(user)
                await notify_user(
                    db, user, title=None, message=None,
                    type_key="zero_lease_expiring", priority="high",
                    i18n_key="zero_lease_expiring",
                    i18n_vars={"biz": _biz_name(biz, lang), "hours": threshold},
                )
            await db.businesses.update_one(
                {"id": biz["id"]},
                {"$set": {"zero_lease_warned": True},
                 "$addToSet": {"zero_lease_warns": {"$each": list(due)}}},
            )
            warned += 1
        except Exception as e:
            logger.error(f"process_zero_lease warn failed for {biz.get('id')}: {e}")
    if warned or expired or restored:
        logger.info(f"process_zero_lease: warned={warned}, expired={expired}, restored={restored}")
    return {"warned": warned, "expired": expired, "restored": restored}


async def restore_wrongly_seized_zero_leases(db) -> int:
    """Вернуть в работу бизнесы 0-го уровня, которые были помечены изъятыми/на
    продаже (is_seized/on_sale/status=on_sale/is_active=False), но срок аренды
    ещё не истёк. Снимаем флаги изъятия с бизнеса и с его листинга (сам листинг
    остаётся активным — арендованный бизнес всегда стоит на маркетплейсе)."""
    now = _now()
    restored = 0
    cursor = db.businesses.find({
        "level": 0,
        "is_zero_business": True,
        "is_trial": {"$ne": True},
        "expires_at": {"$ne": None},
        "$or": [
            {"is_seized": True},
            {"on_sale": True},
            {"status": "on_sale"},
            {"is_active": False},
        ],
    })
    async for biz in cursor:
        exp = _parse_iso(biz.get("expires_at"))
        if not exp or exp <= now:
            # Аренда истекла — восстановлением не занимаемся, это сделает expiry.
            continue
        biz_id = biz.get("id")
        await db.businesses.update_one(
            {"id": biz_id},
            {
                "$set": {"is_active": True, "on_sale": False, "status": "active",
                         "work_status": "idle", "work_status_reason": None},
                "$unset": {"is_seized": "", "seizure_reason": "", "seized_at": "",
                           "former_owner": "", "former_level": ""},
            },
        )
        # Снимаем флаги изъятия с авто-листинга (он должен остаться активным).
        await db.land_listings.update_many(
            {"business_id": biz_id},
            {"$unset": {"is_seized": "", "seizure_reason": "",
                        "former_owner_id": "", "former_level": ""}},
        )
        restored += 1
    if restored:
        logger.info(f"restore_wrongly_seized_zero_leases: восстановлено {restored} арендованных бизнесов 0-го уровня")
    return restored


async def _expire_zero_business(db, biz: dict) -> None:
    """Remove an expired level-0 business, free its plot, cancel its lots."""
    business_id = biz.get("id")
    owner = biz.get("owner")
    plot_id = biz.get("plot_id")
    produces = None
    try:
        from business_config import BUSINESSES, BUSINESS_KEY_MAP
        bt = biz.get("business_type")
        cfg = BUSINESSES.get(BUSINESS_KEY_MAP.get(bt, bt)) or BUSINESSES.get(bt) or {}
        produces = cfg.get("produces")
    except Exception:
        produces = None

    user = await _find_owner_user(db, biz)

    # Reclaim the tier-3 lease welcome bonus (if any): the lease ended without the
    # user buying the business out to level 1, so the +5 TON is taken back from the
    # bonus balance (or whatever is left if it holds less than 5 TON).
    try:
        import zero_business as _zb
        await _zb.clawback_lease_bonus(db, owner, biz)
    except Exception as e:
        logger.error(f"_expire_zero_business clawback failed for {business_id}: {e}")

    # 1) Delist the auto level-0 marketplace lot(s) for this business.
    await db.land_listings.delete_many({"business_id": business_id})

    # 2) Cancel the owner's active resource sale orders tied to this business /
    #    the resource it produced — return the reserved resources to the owner.
    if owner:
        q = {"seller_id": owner, "status": "active"}
        or_terms = [{"business_id": business_id}]
        if produces:
            or_terms.append({"resource_type": produces})
        q["$or"] = or_terms
        async for lot in db.market_listings.find(q, {"_id": 0}):
            rtype = lot.get("resource_type")
            amt = lot.get("amount", 0) or 0
            if user and rtype and amt > 0:
                await db.users.update_one(
                    {"$or": [{"id": owner}, {"wallet_address": owner}]},
                    {"$inc": {f"resources.{rtype}": amt}},
                )
            await db.market_listings.update_one(
                {"id": lot["id"]},
                {"$set": {"status": "cancelled", "cancelled_at": _now().isoformat(),
                          "cancelled_reason": "zero_lease_expired"}},
            )

    # 3) Remove the business and free the plot (cell becomes "Свободно").
    await db.businesses.delete_one({"id": business_id})
    if plot_id:
        await db.plots.delete_one({"id": plot_id})
    else:
        await db.plots.delete_many({"business_id": business_id})

    # 4) Drop it from the user's owned-businesses list.
    if owner:
        await db.users.update_one(
            {"$or": [{"id": owner}, {"wallet_address": owner}]},
            {"$pull": {"businesses_owned": business_id}},
        )

    # 5) Notify the former owner (localized, on-screen + Telegram + mini-app link).
    try:
        from core.notify import notify_user
        from core.notif_i18n import user_lang
        if user:
            lang = user_lang(user)
            await notify_user(
                db, user, title=None, message=None,
                type_key="zero_lease_expired", priority="high",
                i18n_key="zero_lease_expired",
                i18n_vars={"biz": _biz_name(biz, lang)},
            )
    except Exception as e:
        logger.error(f"_expire_zero_business notify failed for {business_id}: {e}")

    logger.info(f"⏳ zero-lease expired: removed business {business_id}, freed plot {plot_id}")


# ──────────────────────── 48h market-lot expiry job ─────────────────────────

async def process_market_lot_expiry(db) -> dict:
    """Auto-cancel resource lots older than 48h and return resources to seller."""
    now = _now()
    cutoff = now - timedelta(hours=MARKET_LOT_MAX_HOURS)
    returned = 0
    cursor = db.market_listings.find({"status": "active"})
    async for lot in cursor:
        # Skip system / bot / tutorial lots — only real player resource lots expire.
        if lot.get("is_bot") or lot.get("tutorial"):
            continue
        created = _parse_iso(lot.get("created_at"))
        if not created or created > cutoff:
            continue
        rtype = lot.get("resource_type")
        amount = lot.get("amount", 0) or 0
        seller_id = lot.get("seller_id")
        # Return the reserved resources to the seller's warehouse.
        if seller_id and rtype and amount > 0:
            seller = await db.users.find_one(
                {"$or": [{"id": seller_id}, {"email": lot.get("seller_email")},
                         {"wallet_address": seller_id}]}, {"_id": 0},
            )
            if seller:
                filt = {"id": seller_id}
                if not seller.get("id") == seller_id and seller.get("email"):
                    filt = {"email": seller.get("email")}
                await db.users.update_one(
                    {"$or": [{"id": seller_id}, {"email": lot.get("seller_email")},
                             {"wallet_address": seller_id}]},
                    {"$inc": {f"resources.{rtype}": amount}},
                )
        await db.market_listings.update_one(
            {"id": lot["id"]},
            {"$set": {"status": "cancelled", "cancelled_at": now.isoformat(),
                      "cancelled_reason": "expired_48h"}},
        )
        returned += 1
        # Notify the seller (localized "goods returned" tip).
        try:
            from core.notify import notify_user
            from core.notif_i18n import user_lang
            seller_doc = await db.users.find_one(
                {"$or": [{"id": seller_id}, {"email": lot.get("seller_email")},
                         {"wallet_address": seller_id}]}, {"_id": 0},
            )
            if seller_doc:
                lang = user_lang(seller_doc)
                await notify_user(
                    db, seller_doc, title=None, message=None,
                    type_key="market_lot_returned", priority="info",
                    i18n_key="market_lot_returned",
                    i18n_vars={"res": _res_name(rtype, lang), "amount": int(amount)},
                )
        except Exception as e:
            logger.error(f"process_market_lot_expiry notify failed for {lot.get('id')}: {e}")
    if returned:
        logger.info(f"process_market_lot_expiry: returned {returned} lots (>48h)")
    return {"returned": returned}



# ───────────────── Level-0 seller auto-buyback (24h) ─────────────────────────

ZERO_BUYBACK_NOTIF = {
    "en": {"title": "🤖 Resources auto-bought by the system",
           "message": "Your lot of {amount} {res} wasn't sold within 24h, so the system bought it at your listed price. +{ton} TON credited to your bonus balance."},
    "ru": {"title": "🤖 Ресурсы выкуплены системой",
           "message": "Ваш лот {amount} {res} не был продан за 24 часа, поэтому система выкупила его по вашей цене. Начислено +{ton} TON на бонусный баланс."},
    "es": {"title": "🤖 Recursos comprados automáticamente por el sistema",
           "message": "Tu lote de {amount} {res} no se vendió en 24h, así que el sistema lo compró a tu precio. +{ton} TON a tu saldo de bonificación."},
    "zh": {"title": "🤖 系统自动回购资源",
           "message": "您的 {amount} {res} 在24小时内未售出，系统已按您的挂牌价回购。+{ton} TON 已计入您的奖励余额。"},
    "fr": {"title": "🤖 Ressources rachetées automatiquement par le système",
           "message": "Votre lot de {amount} {res} n'a pas été vendu en 24 h ; le système l'a acheté à votre prix. +{ton} TON crédités sur votre solde bonus."},
    "de": {"title": "🤖 Ressourcen automatisch vom System gekauft",
           "message": "Dein Los mit {amount} {res} wurde nicht innerhalb von 24 Std. verkauft, daher hat das System es zu deinem Preis gekauft. +{ton} TON auf dein Bonusguthaben gutgeschrieben."},
    "ja": {"title": "🤖 システムが資源を自動買い取り",
           "message": "{amount} {res} のロットが24時間以内に売れなかったため、システムが提示価格で買い取りました。ボーナス残高に +{ton} TON を付与しました。"},
    "ko": {"title": "🤖 시스템이 자원을 자동 매입",
           "message": "{amount} {res} 로트가 24시간 내 판매되지 않아 시스템이 등록 가격으로 매입했습니다. 보너스 잔액에 +{ton} TON 지급."},
    "id": {"title": "🤖 Sumber daya dibeli otomatis oleh sistem",
           "message": "Lot {amount} {res} Anda tidak terjual dalam 24 jam, jadi sistem membelinya sesuai harga Anda. +{ton} TON masuk ke saldo bonus."},
}


async def process_zero_level_buyback(db) -> dict:
    """Auto-buy unsold resource lots of LEVEL-0 sellers after 24h.

    Only lots whose seller STILL holds a level-0 business at buyback time are
    bought (a seller who has upgraded to level 1 is left to the normal 48h
    expiry). The lot is bought at its listed price; proceeds go to the seller's
    bonus balance (matching the level-0 sale rule). A localized notice is sent.
    """
    import uuid as _uuid
    import zero_business as _zb
    now = _now()
    cutoff = now - timedelta(hours=ZERO_BUYBACK_HOURS)
    bought = 0
    cursor = db.market_listings.find({"status": "active"})
    async for lot in cursor:
        if lot.get("is_bot") or lot.get("tutorial"):
            continue
        created = _parse_iso(lot.get("created_at"))
        if not created or created > cutoff:
            continue
        rtype = lot.get("resource_type")
        amount = lot.get("amount", 0) or 0
        seller_id = lot.get("seller_id")
        if not (rtype and amount > 0 and seller_id):
            continue
        seller = await db.users.find_one(
            {"$or": [{"id": seller_id}, {"email": lot.get("seller_email")},
                     {"wallet_address": seller_id}]}, {"_id": 0},
        )
        if not seller:
            continue
        # Gate: seller must STILL be a level-0 holder right now.
        seller_ids = [x for x in (seller.get("id"), seller.get("wallet_address"), seller.get("email")) if x]
        try:
            if not await _zb.has_zero_business(db, seller_ids):
                continue
        except Exception as e:
            logger.error(f"zero-buyback level check failed for {lot.get('id')}: {e}")
            continue

        price_per_unit = float(lot.get("price_per_unit", 0) or 0)
        total_ton = round(amount * price_per_unit, 6)

        # Mark the lot as bought back by the system (atomic guard on status).
        upd = await db.market_listings.update_one(
            {"id": lot["id"], "status": "active"},
            {"$set": {"status": "sold", "sold_at": now.isoformat(),
                      "sold_reason": "auto_buyback_24h", "auto_buyback": True,
                      "buyer_username": "System"}},
        )
        if upd.modified_count != 1:
            continue  # someone bought it concurrently

        # Credit the seller's BONUS balance (level-0 sale rule).
        if total_ton > 0:
            await db.users.update_one(
                {"id": seller.get("id")} if seller.get("id") else
                {"$or": [{"wallet_address": seller_id}, {"email": lot.get("seller_email")}]},
                {"$inc": {"bonus_balance": total_ton}},
            )

        # Record a transaction tied to the seller so it shows in admin history.
        try:
            await db.transactions.insert_one({
                "id": str(_uuid.uuid4()),
                "tx_type": "auto_buyback",
                "seller_id": seller.get("id") or seller_id,
                "user_id": seller.get("id") or seller_id,
                "amount": total_ton,
                "resource_type": rtype,
                "resource_amount": amount,
                "price_per_unit": price_per_unit,
                "to_bonus": True,
                "status": "completed",
                "description": f"System auto-buyback of {amount} {rtype} (24h unsold, level-0 seller)",
                "created_at": now.isoformat(),
            })
        except Exception as e:
            logger.error(f"zero-buyback tx insert failed for {lot.get('id')}: {e}")

        bought += 1

        # Localized notification to the seller.
        try:
            from core.notify import notify_user
            from core.notif_i18n import user_lang
            lang = user_lang(seller)
            if lang not in ZERO_BUYBACK_NOTIF:
                lang = "en"
            txt = ZERO_BUYBACK_NOTIF[lang]
            await notify_user(
                db, seller,
                title=txt["title"],
                message=txt["message"].format(amount=int(amount), res=_res_name(rtype, lang),
                                              ton=round(total_ton, 4)),
                type_key="zero_auto_buyback", priority="info",
            )
        except Exception as e:
            logger.error(f"zero-buyback notify failed for {lot.get('id')}: {e}")

    if bought:
        logger.info(f"process_zero_level_buyback: bought {bought} level-0 lots (>24h)")
    return {"bought": bought}
