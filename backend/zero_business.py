"""Level-0 (застолблённый) business onboarding mechanic — shared helpers.

Lifecycle:
  * A user with ZERO real businesses AND `has_graduated_zero != True` may claim
    ("застолбить") exactly ONE business from the map for 0 TON at level 0.
  * While a level-0 business is held, the user cannot buy/build anything else,
    cannot take credit, and resource-sale proceeds go to `bonus_balance`.
  * Upgrading level 0 -> 1 costs the current map price in $CITY paid strictly
    from the REAL balance, removes the auto marketplace lot, and sets
    `has_graduated_zero = True` (permanent — no more level-0 claims ever).
  * The claimed business is auto-listed on the marketplace at map_price * 1.2.
    Proceeds from that lot go to the ADMIN, not the claimer. The lot cannot be
    delisted. When bought, the buyer receives a normal level-1 business (empty
    storage), the old owner loses it (and can claim again), and gets a notice.
"""

ZERO_PRICE_MULTIPLIER = 1.2
CITY_PER_TON = 1000


def owner_query(user_ids):
    ids = [i for i in user_ids if i]
    return {"owner": {"$in": ids}} if ids else {"owner": "__no_such_owner__"}


async def _real_businesses(db, user_ids):
    docs = await db.businesses.find(
        {**owner_query(user_ids), "is_trial": {"$ne": True}},
        {"_id": 0, "id": 1, "level": 1, "is_zero_business": 1},
    ).to_list(200)
    return docs


async def count_real_businesses(db, user_ids) -> int:
    return len(await _real_businesses(db, user_ids))


async def get_zero_business(db, user_ids):
    """Return the user's level-0 business doc (full) or None."""
    return await db.businesses.find_one(
        {**owner_query(user_ids), "level": 0, "is_trial": {"$ne": True}},
        {"_id": 0},
    )


async def has_zero_business(db, user_ids) -> bool:
    return (await get_zero_business(db, user_ids)) is not None


async def can_stake_zero(db, user_doc, user_ids) -> bool:
    """Eligible to claim a level-0 business: exactly 0 real businesses AND never
    graduated (never upgraded a level-0 to level-1)."""
    if user_doc and user_doc.get("has_graduated_zero"):
        return False
    return (await count_real_businesses(db, user_ids)) == 0


async def should_credit_bonus(db, user_ids) -> bool:
    """Resource-sale proceeds go to bonus_balance when the seller has NO
    businesses at all, OR holds at least one level-0 business."""
    docs = await _real_businesses(db, user_ids)
    if len(docs) == 0:
        return True
    return any((d.get("level", 1) == 0) for d in docs)


async def create_zero_listing(db, business, seller_user_id, seller_username, uuid_mod, datetime_mod, timezone_mod):
    """Auto-create the marketplace lot for a freshly claimed level-0 business.
    Price is FIXED at map_price * 1.2 at claim time. Returns the listing id.
    The `business` payload mirrors a normal sale listing (translated name,
    icon, tier, produces + production/day, consumes) so buyers see full data."""
    from business_config import get_production, get_consumption_breakdown
    try:
        from core.helpers import resolve_business_config
    except Exception:
        resolve_business_config = None
    map_price = float(business.get("zero_map_price", 0) or 0)
    price = round(map_price * ZERO_PRICE_MULTIPLIER, 6)
    listing_id = str(uuid_mod.uuid4())
    _bt = business.get("business_type")
    _cfg = (resolve_business_config(_bt) if resolve_business_config else {}) or {}
    _biz_payload = {
        "type": _bt,
        "level": 1,  # shown to buyers as a normal level-1 business
        "durability": 100,
        "xp": 0,
        "connections": 0,
        "icon": _cfg.get("icon", business.get("icon", "")),
        "name": _cfg.get("name", business.get("name", {})),
        "tier": _cfg.get("tier", business.get("tier", 1)),
        "produces": _cfg.get("produces", ""),
        "production_per_day": get_production(_bt, 1),
        "consumes": get_consumption_breakdown(_bt, 1),
    }
    listing = {
        "id": listing_id,
        "plot_id": business.get("plot_id"),
        "city_id": business.get("island_id") or business.get("city_id") or "ton_island",
        "city_name": "GRAM Island",
        "x": business.get("x"),
        "y": business.get("y"),
        "seller_id": seller_user_id,
        "seller_user_id": seller_user_id,
        "seller_username": seller_username or "Anonymous",
        "business_id": business.get("id"),
        "price": price,
        "original_price": map_price,
        "tax_amount": 0.0,
        "seller_receives": 0.0,
        "is_zero_business": True,
        "admin_proceeds": True,
        "locked_delist": True,
        "business": _biz_payload,
        "status": "active",
        "created_at": datetime_mod.now(timezone_mod.utc).isoformat(),
    }
    await db.land_listings.insert_one(listing.copy())
    return listing_id, price


async def grant_zero_consumption(db, user_id, business_type):
    """On claiming a level-0 business, credit the user the business's DAILY
    consumption norm of the resource(s) it needs (e.g. consumes 24 energy/day
    -> grant 24 energy) so it can run immediately. TON-denominated pseudo lines
    (e.g. profit_ton) are excluded — only real tradeable resources are granted."""
    from business_config import get_consumption_breakdown
    _EXCLUDED = {"profit_ton", "ton", "city", "gram"}
    breakdown = get_consumption_breakdown(business_type, 1) or {}
    inc = {f"resources.{res}": amt for res, amt in breakdown.items() if amt and res not in _EXCLUDED}
    if inc:
        await db.users.update_one({"id": user_id}, {"$inc": inc})
    return breakdown


# ─── Localized notification: "your level-0 business was bought on the market" ──
ZERO_BOUGHT_NOTIF = {
    "en": {
        "title": "🏢 Business bought on the Marketplace",
        "message": "Your level-0 business was purchased by another player on the Marketplace. You can now claim a new free business on the map.",
    },
    "ru": {
        "title": "🏢 Бизнес выкуплен на Маркетплейсе",
        "message": "Ваш бизнес нулевого уровня был выкуплен другим игроком на Маркетплейсе. Теперь вы можете снова застолбить бесплатный бизнес на карте.",
    },
    "es": {
        "title": "🏢 Negocio comprado en el Mercado",
        "message": "Otro jugador compró tu negocio de nivel 0 en el Mercado. Ahora puedes reclamar un nuevo negocio gratis en el mapa.",
    },
    "zh": {
        "title": "🏢 企业在市场上被买走",
        "message": "您的0级企业被其他玩家在市场上买走了。您现在可以在地图上重新认领一个免费企业。",
    },
    "fr": {
        "title": "🏢 Entreprise achetée sur le Marché",
        "message": "Votre entreprise de niveau 0 a été achetée par un autre joueur sur le Marché. Vous pouvez maintenant réclamer une nouvelle entreprise gratuite sur la carte.",
    },
    "de": {
        "title": "🏢 Unternehmen auf dem Marktplatz gekauft",
        "message": "Dein Level-0-Unternehmen wurde von einem anderen Spieler auf dem Marktplatz gekauft. Du kannst jetzt ein neues kostenloses Unternehmen auf der Karte beanspruchen.",
    },
    "ja": {
        "title": "🏢 ビジネスがマーケットで購入されました",
        "message": "あなたのレベル0ビジネスが他のプレイヤーにマーケットプレイスで購入されました。マップで新しい無料ビジネスを再び取得できます。",
    },
    "ko": {
        "title": "🏢 마켓에서 비즈니스가 판매됨",
        "message": "당신의 레벨 0 비즈니스가 마켓플레이스에서 다른 플레이어에게 구매되었습니다. 이제 지도에서 새로운 무료 비즈니스를 다시 선점할 수 있습니다.",
    },
    "id": {
        "title": "🏢 Bisnis dibeli di Marketplace",
        "message": "Bisnis level-0 Anda dibeli oleh pemain lain di Marketplace. Sekarang Anda dapat mengklaim bisnis gratis baru di peta.",
    },
}


async def notify_zero_bought(db, owner_user, uuid_mod, datetime_mod, timezone_mod, manager=None):
    """Insert a localized notification for the former owner + WS push."""
    if not owner_user:
        return
    lang = (owner_user.get("language") or "en")
    if lang not in ZERO_BOUGHT_NOTIF:
        lang = "en"
    txt = ZERO_BOUGHT_NOTIF[lang]
    notif = {
        "id": str(uuid_mod.uuid4()),
        "user_id": owner_user.get("id", ""),
        "type": "zero_business_bought",
        "title": txt["title"],
        "message": txt["message"],
        "priority": "high",
        "read": False,
        "created_at": datetime_mod.now(timezone_mod.utc).isoformat(),
    }
    await db.notifications.insert_one(notif.copy())
    if manager is not None:
        try:
            await manager.send_to_user(owner_user.get("id", ""), {"type": "notification_new"})
        except Exception:
            pass
