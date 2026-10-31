"""Изъятие бизнесов за неактивность на рынке.

Пользователь считается АКТИВНЫМ, если за последние 10 дней выполнено хотя бы одно:
  • купил на рынке (P2P, tx_type="market_purchase") не менее 40 ед. товара, ИЛИ
  • продал на рынке не менее 100 ед. товара.

Если НИ ОДНО условие не выполнено — пользователь неактивен, и его бизнесы
изымаются: останавливаются (не производят и не потребляют) и выставляются на
Маркетплейс от имени GRAM CITY с тем же уровнем, что был у владельца.

Цена листинга (core.seizure.seizure_price_breakdown) — по уровню:
  стоимость 1-го уровня = рыночная цена клетки на карте острова
      (islands.cells.price_ton), но не ниже базовой стоимости постройки;
  + все улучшения со 2-го уровня до текущего: $CITY / 1000
      + товар для улучшения × его текущая цена на рынке.
Никогда не 1 TON «по умолчанию». Уже выставленные изъятые бизнесы (старые —
сброшенные на 1-й уровень и/или за 1 TON) получают обратно уровень и цену по нему
при запуске сервера и при каждом запуске изъятия (reprice_underpriced_listings).

Распределение выручки при продаже изъятого бизнеса (см. server.py buyout):
  • бывший нулевой бизнес (level 0) → 100% государству (бывший владелец ничего);
  • бизнес 1+ уровня → 30% бывшему владельцу, остальное государству.

Нулевые бизнесы уже стоят на Маркетплейсе (создаются при застолблении), поэтому
повторно НЕ листятся — только меняется статус и бизнес останавливается.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Set, Tuple

logger = logging.getLogger(__name__)

WINDOW_DAYS = 10
MARKET_BUY_MIN = 40      # куплено ед. за WINDOW_DAYS дней
MARKET_SELL_MIN = 100    # продано ед. за WINDOW_DAYS дней
SYSTEM_SELLER_ID = "SYSTEM_GRAM_CITY"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_identifiers(u: Dict[str, Any]) -> Set[str]:
    ids = {u.get("id"), u.get("wallet_address"), u.get("email"), u.get("username")}
    ids.discard(None)
    ids.discard("")
    return ids


async def compute_active_user_ids(db) -> Tuple[Set[str], Dict[str, float], Dict[str, float]]:
    """Вернуть (множество активных идентификаторов, карта покупок, карта продаж).

    Идентификаторы берутся из транзакций (buyer_id/seller_id) — это могут быть
    user.id или wallet. Активность пользователя проверяется по пересечению его
    идентификаторов с этим множеством.
    """
    cutoff = (_now() - timedelta(days=WINDOW_DAYS)).isoformat()
    buy_map: Dict[str, float] = {}
    sell_map: Dict[str, float] = {}

    buy_pipeline = [
        {"$match": {"tx_type": "market_purchase", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$buyer_id", "units": {"$sum": "$resource_amount"}}},
    ]
    sell_pipeline = [
        {"$match": {"tx_type": "market_purchase", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$seller_id", "units": {"$sum": "$resource_amount"}}},
    ]

    active: Set[str] = set()
    async for row in db.transactions.aggregate(buy_pipeline):
        uid = row.get("_id")
        units = float(row.get("units") or 0)
        if uid:
            buy_map[uid] = units
            if units >= MARKET_BUY_MIN:
                active.add(uid)
    async for row in db.transactions.aggregate(sell_pipeline):
        uid = row.get("_id")
        units = float(row.get("units") or 0)
        if uid:
            sell_map[uid] = units
            if units >= MARKET_SELL_MIN:
                active.add(uid)
    return active, buy_map, sell_map


async def get_activity_stats(db) -> Dict[str, Any]:
    """Статистика для админки: сколько всего/активных/неактивных пользователей."""
    active_ids, _buy, _sell = await compute_active_user_ids(db)
    total = 0
    active = 0
    async for u in db.users.find({}, {"_id": 0, "id": 1, "wallet_address": 1, "email": 1, "username": 1}):
        total += 1
        if _user_identifiers(u) & active_ids:
            active += 1
    return {
        "total": total,
        "active": active,
        "inactive": max(0, total - active),
        "window_days": WINDOW_DAYS,
        "buy_threshold": MARKET_BUY_MIN,
        "sell_threshold": MARKET_SELL_MIN,
    }


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _base_cost_ton(business: Dict[str, Any]) -> float:
    from core.seizure import _cfg
    return _num(_cfg(business.get("business_type"))[0].get("base_cost_ton")) or 5.0


async def _price_breakdown(db, business: Dict[str, Any], level: int = None) -> Dict[str, Any]:
    from core.seizure import seizure_price_breakdown
    return await seizure_price_breakdown(db, business, level)


async def _map_price_for_business(db, business: Dict[str, Any], level: int = None) -> float:
    """Fair list price (TON) of a seized business: value of level 1 (map price of its cell, not below the base build
    cost) + all its upgrades ($CITY + resources at the current market price)."""
    return (await _price_breakdown(db, business, level))["total"]


async def reprice_underpriced_listings(db) -> int:
    """Active seized-for-inactivity listings get the fair price by level. Old listings were put up as level 1 (the
    business reset to level 1) and often at the 1 TON fallback: the business gets back its level and the price for it."""
    fixed = 0
    async for lst in db.land_listings.find({"seizure_reason": "inactivity", "status": "active",
                                            "seller_id": SYSTEM_SELLER_ID}, {"_id": 0}):
        try:
            former = int(lst.get("former_level") if lst.get("former_level") is not None else 1)
        except (TypeError, ValueError):
            former = 1
        if former <= 0 or (lst.get("business") or {}).get("level") == 0 or lst.get("price_manual"):
            continue                                       # a price set by the admin by hand is kept
        biz = await db.businesses.find_one({"id": lst.get("business_id")}, {"_id": 0}) or {}
        level = max(former, int(biz.get("level") or 1))
        src = {**{k: lst.get(k) for k in ("x", "y", "plot_id")},
               **{k: v for k, v in biz.items() if v is not None},
               "business_type": biz.get("business_type") or (lst.get("business") or {}).get("type")}
        bd = await _price_breakdown(db, src, level)
        fair = bd["total"]
        same_level = int((lst.get("business") or {}).get("level") or 1) == level and int(biz.get("level") or 1) == level
        if same_level and _num(lst.get("price")) + 1e-6 >= fair:
            continue                                       # the price is frozen once fair
        upd = {"price": fair, "original_price": fair, "seller_receives": fair, "price_breakdown": bd,
               "business.level": level, "repriced_at": _now().isoformat()}
        r = await db.land_listings.update_one({"id": lst["id"], "status": "active"}, {"$set": upd})
        if not r.modified_count:
            continue
        if biz:
            await db.businesses.update_one({"id": biz["id"], "is_seized": True}, {"$set": {"level": level}})
        fixed += 1
        logger.info(f"seized listing {lst['id']}: level {level}, price {lst.get('price')} → {fair} TON")
    return fixed


async def _notify_former_owner(db, owner: Dict[str, Any], biz_name: str):
    try:
        from core.notify import notify_user
        await notify_user(
            db,
            owner,
            "Бизнес изъят за неактивность",
            f"Ваш бизнес «{biz_name}» изъят за неактивность на рынке и выставлен на "
            f"Маркетплейс. Чтобы оставаться активным, покупайте не менее {MARKET_BUY_MIN} ед. "
            f"или продавайте не менее {MARKET_SELL_MIN} ед. товара за {WINDOW_DAYS} дней.",
            type_key="system",
            priority="warning",
        )
    except Exception as e:
        logger.debug(f"seizure notify failed: {e}")


async def seize_inactive_businesses(db) -> Dict[str, int]:
    """Изъять бизнесы у неактивных пользователей. Идемпотентно."""
    try:
        repriced = await reprice_underpriced_listings(db)
    except Exception as e:
        logger.error(f"reprice seized listings failed: {e}")
        repriced = 0
    active_ids, _buy, _sell = await compute_active_user_ids(db)

    seized_zero = 0
    seized_regular = 0
    checked = 0

    # Кэш пользователей, чтобы не читать по многу раз.
    user_cache: Dict[str, Dict[str, Any]] = {}

    async def _resolve_owner(owner_key: str):
        if owner_key in user_cache:
            return user_cache[owner_key]
        u = await db.users.find_one(
            {"$or": [{"id": owner_key}, {"wallet_address": owner_key}, {"email": owner_key}]},
            {"_id": 0},
        )
        user_cache[owner_key] = u
        return u

    query = {
        "is_trial": {"$ne": True},
        "tutorial": {"$ne": True},
        "is_seized": {"$ne": True},
        "on_sale": {"$ne": True},
        "status": {"$ne": "on_sale"},
        "paused_reason": {"$ne": "bankruptcy"},
        # НЕ трогаем арендованные бизнесы 0-го уровня — у них своя механика
        # 3-дневной аренды (zero_lease.process_zero_lease). Иначе новый игрок
        # без рыночной активности сразу терял бы только что застолблённый бизнес.
        "is_zero_business": {"$ne": True},
        "level": {"$ne": 0},
    }

    async for biz in db.businesses.find(query):
        checked += 1
        owner_key = biz.get("owner") or biz.get("owner_wallet")
        if not owner_key:
            continue
        owner = await _resolve_owner(owner_key)
        if not owner:
            continue
        if owner.get("is_admin"):
            continue
        # Не изымаем у пользователей, всё ещё проходящих обучение.
        if owner.get("tutorial_active"):
            continue
        # Активен — пропускаем все его бизнесы.
        if _user_identifiers(owner) & active_ids:
            continue

        level = int(biz.get("level", 1) or 0)
        is_zero = bool(biz.get("is_zero_business")) or level == 0
        biz_id = biz.get("id")
        now_iso = _now().isoformat()
        cfg_name = biz.get("business_type", "business")

        base_set = {
            "on_sale": True,
            "status": "on_sale",
            "is_active": False,
            "is_seized": True,
            "seizure_reason": "inactivity",
            "seized_at": now_iso,
            "former_owner": owner_key,
            "former_level": level,
        }

        if is_zero:
            # Уже стоит на Маркетплейсе — повторно не листим, только останавливаем.
            await db.businesses.update_one({"id": biz_id}, {"$set": base_set})
            # Пометим существующий листинг, чтобы выкуп знал причину.
            await db.land_listings.update_many(
                {"business_id": biz_id, "status": "active"},
                {"$set": {
                    "is_seized": True,
                    "seizure_reason": "inactivity",
                    "former_owner_id": owner_key,
                    "former_level": 0,
                }},
            )
            seized_zero += 1
            try:
                import zero_business as _zb
                await _zb.clawback_lease_bonus(db, owner_key, biz)
                await db.businesses.update_one({"id": biz_id}, {"$unset": {"lease_ton_bonus": ""}})
            except Exception as e:
                logger.error(f"seize clawback failed for {biz_id}: {e}")
            await _notify_former_owner(db, owner, cfg_name)
            continue

        # Бизнес 1+ уровня: на Маркетплейс с ТЕМ ЖЕ уровнем, цена — по уровню и прокачке.
        breakdown = await _price_breakdown(db, biz, level)
        map_price = breakdown["total"]
        listing_id = str(uuid.uuid4())
        city_id = biz.get("island_id") or biz.get("city_id") or "ton_island"
        listing = {
            "id": listing_id,
            "plot_id": biz.get("plot_id"),
            "city_id": city_id,
            "city_name": "GRAM Island",
            "x": biz.get("x"),
            "y": biz.get("y"),
            "seller_id": SYSTEM_SELLER_ID,
            "seller_username": "GRAM CITY",
            "business_id": biz_id,
            "price": map_price,
            "original_price": map_price,
            "tax_amount": 0.0,
            "seller_receives": map_price,
            "price_breakdown": breakdown,
            "is_seized": True,
            "seizure_reason": "inactivity",
            "former_owner_id": owner_key,
            "former_level": level,
            "business": {
                "type": biz.get("business_type"),
                "level": level,
                "connections": len(biz.get("connected_businesses", []) or []),
                "xp": 0,
            },
            "status": "active",
            "created_at": now_iso,
        }
        await db.land_listings.insert_one(listing.copy())

        set_doc = dict(base_set)
        set_doc.update({"listing_id": listing_id})
        await db.businesses.update_one({"id": biz_id}, {"$set": set_doc})
        if biz.get("plot_id"):
            await db.plots.update_one(
                {"id": biz["plot_id"]},
                {"$set": {"on_sale": True, "listing_id": listing_id}},
            )
        seized_regular += 1
        await _notify_former_owner(db, owner, cfg_name)

    result = {"seized_zero": seized_zero, "seized_regular": seized_regular, "checked": checked, "repriced": repriced}
    logger.info(f"seize_inactive_businesses: {result}")
    return result
