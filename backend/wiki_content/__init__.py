"""The articles of «Справочник» that come with the code (routes/wiki.py seeds them into db.wiki_articles).

Structure lives here; the texts — one module per language (ru.py, en.py, …), the same slugs in each.
Raise SEED_REV when the seed texts change: articles never edited in the admin are then refreshed on start.

show.steps — «Показать на деле»: selectors of real buttons ({bid} — the player's first business, {prod} — its product);
             tap=True: the step waits for the player to press the framed button, otherwise «Далее».
             tools/wiki_selfcheck.py opens every route and checks that each selector is on the page.
"""
import importlib

SEED_REV = 4

SECTIONS = [
    {"id": "start", "icon": "🚀", "t": {"ru": "Начало", "en": "Getting started", "es": "Primeros pasos", "zh": "入门", "fr": "Démarrer", "de": "Erste Schritte", "ja": "はじめに", "ko": "시작하기", "id": "Memulai"}},
    {"id": "land", "icon": "🗺", "t": {"ru": "Земля", "en": "Land", "es": "Terreno", "zh": "土地", "fr": "Terrain", "de": "Land", "ja": "土地", "ko": "토지", "id": "Lahan"}},
    {"id": "business", "icon": "🏭", "t": {"ru": "Бизнес", "en": "Business", "es": "Negocio", "zh": "企业", "fr": "Entreprise", "de": "Unternehmen", "ja": "ビジネス", "ko": "비즈니스", "id": "Bisnis"}},
    {"id": "warehouse", "icon": "📦", "t": {"ru": "Склад", "en": "Warehouse", "es": "Almacén", "zh": "仓库", "fr": "Entrepôt", "de": "Lager", "ja": "倉庫", "ko": "창고", "id": "Gudang"}},
    {"id": "trade", "icon": "⚖️", "t": {"ru": "Торговля", "en": "Trading", "es": "Comercio", "zh": "交易", "fr": "Commerce", "de": "Handel", "ja": "取引", "ko": "거래", "id": "Perdagangan"}},
    {"id": "money", "icon": "💰", "t": {"ru": "Деньги", "en": "Money", "es": "Dinero", "zh": "资金", "fr": "Argent", "de": "Geld", "ja": "お金", "ko": "자금", "id": "Uang"}},
    {"id": "rewards", "icon": "🎁", "t": {"ru": "Награды", "en": "Rewards", "es": "Recompensas", "zh": "奖励", "fr": "Récompenses", "de": "Belohnungen", "ja": "報酬", "ko": "보상", "id": "Hadiah"}},
    {"id": "community", "icon": "💬", "t": {"ru": "Сообщество", "en": "Community", "es": "Comunidad", "zh": "社区", "fr": "Communauté", "de": "Community", "ja": "コミュニティ", "ko": "커뮤니티", "id": "Komunitas"}},
    {"id": "rules", "icon": "📜", "t": {"ru": "Правила и помощь", "en": "Rules and help", "es": "Reglas y ayuda", "zh": "规则与帮助", "fr": "Règles et aide", "de": "Regeln und Hilfe", "ja": "ルールとヘルプ", "ko": "규칙과 도움말", "id": "Aturan dan bantuan"}},
]

_B = "/my-businesses"


def _a(slug, section, icon, screens=(), needs=(), related=(), route=None, steps=()):
    show = {"route": route, "steps": [{"sel": list(s[0]), "tap": bool(s[1])} for s in steps]} if route else None
    return {"slug": slug, "section": section, "icon": icon, "screens": list(screens), "needs": list(needs),
            "related": list(related), "show": show}


BAL = ("[data-testid=header-city-balance]", "[data-testid=sidebar-balance-city]")

ARTICLES = [
    # 🚀 Начало
    _a("quick-start", "start", "🚀", (), ("has_business", "shift_running", "sold_once", "biz_level1"), ("first-days", "earning", "balances")),
    _a("balances", "start", "💳", ("history",), (), ("deposit", "withdraw", "history"), _B, [(BAL, False)]),
    _a("earning", "start", "💹", (), (), ("sell", "tenders", "rental")),
    _a("interface", "start", "🧭", (), (), ("notifications", "support"), _B,
       [(("[data-testid=bottom-nav]", "[data-testid=sidebar-nav-map]"), False), (("[data-testid=header-burger-btn]", "[data-testid=sidebar-nav-wiki]"), False)]),
    _a("first-days", "start", "📅", (), ("has_business", "shift_running", "sold_once", "biz_level1"), ("zero-business", "upgrade", "shift")),
    _a("notifications", "start", "🔔", ("settings",), ("telegram_linked",), ("spoilage", "shift"), "/settings",
       [(("[data-testid=settings-smart-notifications]",), False)]),
    # 🗺 Земля
    _a("maps", "land", "🗺", ("maps", "map"), (), ("plots", "zero-business"), "/maps", [(("[data-testid=city-card-ton_island]", "[data-testid^=city-card-]"), False)]),
    _a("zero-business", "land", "🏝", ("map",), ("can_claim_zero",), ("first-days", "upgrade", "zero-limits"), "/ton-island",
       [(("[data-testid=map-sale-btn]",), True)]),
    _a("plots", "land", "📐", ("map",), (), ("buy-business", "districts")),
    _a("buy-business", "land", "🏗", ("map", "marketplace"), ("no_zero_business", "main_balance"), ("tiers", "plots", "business-sale"), "/marketplace",
       [(("[data-testid=marketplace-tabs]",), False)]),
    _a("districts", "land", "🏙", ("map", "maps"), (), ("plots", "buy-business")),
    # 🏭 Бизнес
    _a("tiers", "business", "🏷", (), (), ("chains", "resources", "buy-business")),
    _a("shift", "business", "▶️", (), ("has_business", "shift_running"), ("raw-materials", "durability", "boosters"), _B,
       [(("[data-testid=work-status-{bid}]",), False), (("[data-testid=start-shift-btn-{bid}]", "[data-testid=work-status-{bid}]"), False)]),
    _a("raw-materials", "business", "🧰", ("resources",), ("has_business",), ("buy", "chains", "shift"), _B,
       [(("[data-testid=income-chip-{bid}]",), False), (("[data-testid=expense-chip-{bid}]",), False)]),
    _a("durability", "business", "🔧", (), ("has_business", "durability_ok"), ("shift", "boosters"), _B,
       [(("[data-testid=durability-value-{bid}]", "[data-testid=work-status-{bid}]"), False), (("[data-testid=action-repair-{bid}]",), False)]),
    _a("upgrade", "business", "⬆️", (), ("has_business", "main_balance"), ("zero-business", "t3-buffs", "deposit"), _B,
       [(("[data-testid=action-upgrade-{bid}]",), False)]),
    _a("chains", "business", "🔗", ("map",), (), ("tiers", "raw-materials", "resources")),
    _a("patron-buffs", "business", "✨", (), (), ("t3-buffs", "contracts", "tiers")),
    _a("skins", "business", "🎨", (), (), ("partner-tasks",)),
    _a("business-sale", "business", "🏷", ("marketplace",), ("biz_level1", "no_overdue"), ("taxes", "credit", "rental"), "/marketplace",
       [(("[data-testid=marketplace-tabs]",), False)]),
    _a("rental", "business", "🤝", ("marketplace",), ("biz_level1",), ("business-sale", "earning")),
    _a("seizure", "business", "⚠️", (), ("activity_ok", "no_overdue"), ("activity-rule", "credit")),
    # 📦 Склад
    _a("resources", "warehouse", "📦", ("resources",), (), ("capacity", "tiers", "chains"), "/resources",
       [(("[data-testid=resources-warehouse]", "[data-testid=resources-open-businesses]"), False)]),
    _a("capacity", "warehouse", "📏", ("resources",), (), ("spoilage", "upgrade", "sell"), "/resources",
       [(("[data-testid=resources-warehouse]", "[data-testid=resources-open-businesses]"), False)]),
    _a("warehouse-value", "warehouse", "💰", ("resources",), (), ("analytics", "sell"), "/resources", [(("[data-testid=resources-warehouse-value]",), False)]),
    _a("spoilage", "warehouse", "🕘", ("resources",), (), ("sell", "boosters", "capacity"), "/resources", [(("[data-testid=resources-warehouse]",), False)]),
    _a("boosters", "warehouse", "⚡", ("resources", "city-pass"), (), ("t3-buffs", "city-pass", "patron-buffs"), "/resources", [(("[data-testid=resources-tab-boosters]",), True)]),
    _a("t3-buffs", "warehouse", "🔮", ("resources", "city-pass"), (), ("boosters", "upgrade", "first-days"), "/resources", [(("[data-testid=resources-tab-boosters]",), True)]),
    # ⚖️ Торговля
    _a("buy", "trade", "🛒", ("trading",), (), ("sell", "raw-materials", "taxes"), "/trading",
       [(("[data-testid=tutorial-trading-tab-buy]",), False), (("[data-testid=buy-filters-open]",), False)]),
    _a("sell", "trade", "🏷", ("trading",), ("product_in_stock", "free_lot_slot"), ("edit-lot", "city-market", "taxes"), "/trading?tab=my",
       [(("[data-testid=tutorial-create-lot-btn]",), True)]),
    _a("edit-lot", "trade", "✏️", ("trading",), ("has_lot",), ("sell", "city-market"), "/trading?tab=my", [(("[data-testid^=my-lot-]", "[data-testid=tutorial-create-lot-btn]"), False)]),
    _a("city-market", "trade", "🏙", ("trading",), (), ("sell", "zero-business")),
    _a("tenders", "trade", "📑", ("trading",), (), ("contracts", "earning"), "/trading",
       [(("[data-testid=operations-tab]",), True), (("[data-testid=tenders-tab-exchange]",), False)]),
    _a("contracts", "trade", "🚚", ("trading",), (), ("tenders", "patron-buffs")),
    _a("analytics", "trade", "📈", ("trading", "analytics"), (), ("sell", "warehouse-value"), _B, [(("[data-testid=biz-side-analytics]",), True)]),
    _a("taxes", "trade", "🧾", ("trading",), (), ("sell", "business-sale", "referrals")),
    # 💰 Деньги
    _a("deposit", "money", "⬇️", ("history",), ("wallet_linked",), ("withdraw", "balances"), _B, [(BAL, True)]),
    _a("withdraw", "money", "⬆️", ("history",), ("main_balance", "twofa", "wallet_linked"), ("security", "banks", "balances"), _B, [(BAL, True)]),
    _a("security", "money", "🛡", ("security", "settings"), ("twofa",), ("withdraw", "safety"), "/security",
       [(("[data-testid=enable-2fa-btn]",), False), (("[data-testid=add-passkey-btn]",), False)]),
    _a("history", "money", "📜", ("history",), (), ("balances", "taxes"), "/history", [(("[data-testid=tx-type-filter]",), False)]),
    _a("credit", "money", "🏦", ("credit",), ("biz_level1", "no_overdue"), ("banks", "seizure", "upgrade"), "/credit", [(("[data-testid=apply-credit-btn]",), False)]),
    _a("banks", "money", "🏛", ("credit",), (), ("credit", "withdraw", "tiers")),
    # 🎁 Награды
    _a("daily-login", "rewards", "📆", ("tasks",), (), ("quests", "city-pass"), "/tasks", [(("[data-testid=daily-login-card]",), False)]),
    _a("quests", "rewards", "🎯", ("tasks",), (), ("daily-login", "city-pass"), "/tasks", [(("[data-testid=quest-daily]", "[data-testid^=quest-progress-]"), False)]),
    _a("partner-tasks", "rewards", "🤝", ("tasks",), (), ("quests", "skins"), "/tasks", [(("[data-testid=tasks-tab-partners]",), False)]),
    _a("city-pass", "rewards", "🎫", ("city-pass",), (), ("boosters", "quests", "alliances"), "/city-pass", [(("[data-testid=pass-header]",), False)]),
    _a("referrals", "rewards", "👥", (), (), ("taxes", "earning"), _B, [(("[data-testid=header-referrals-btn]",), True)]),
    # 💬 Сообщество
    _a("chat", "community", "💬", ("chat", "community"), (), ("alliances", "safety"), "/chat", [(("[data-testid=chat-channels]",), False)]),
    _a("leagues", "community", "🏆", ("community",), (), ("quests", "leaderboard"), "/community",
       [(("[data-testid=league-div-prev]",), False), (("[data-testid=league-mode]",), False)]),
    _a("alliances", "community", "🛡", ("community",), ("pass_level", "has_business"), ("city-pass", "chat"), "/community",
       [(("[data-testid=community-tab-alliance]",), False)]),
    _a("leaderboard", "community", "📊", ("leaderboard", "community"), (), ("leagues",)),
    _a("profile", "community", "👤", (), (), ("alliances", "leagues"), _B, [(("[data-testid=header-profile]", "[data-testid=sidebar-balance-city]"), False)]),
    # 📜 Правила и помощь
    _a("activity-rule", "rules", "⏳", (), ("activity_ok",), ("seizure", "buy", "sell")),
    _a("zero-limits", "rules", "🔒", ("map",), (), ("zero-business", "upgrade")),
    _a("safety", "rules", "🚨", ("security", "chat"), ("twofa",), ("security", "support")),
    _a("faq", "rules", "❓", (), (), ("support", "glossary")),
    _a("glossary", "rules", "🔤", (), (), ("faq",)),
    _a("support", "rules", "🆘", (), (), ("faq", "safety"), _B, [(("[data-testid=header-burger-btn]", "[data-testid=sidebar-support-btn]"), False)]),
]

LANGS = ["ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"]


def load_texts():
    out = {}
    for lg in LANGS:
        try:
            out[lg] = importlib.import_module(f"wiki_content.{lg}").A
        except ModuleNotFoundError:
            out[lg] = {}
    return out
