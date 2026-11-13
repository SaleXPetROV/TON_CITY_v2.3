"""The player's own numbers for Willy GRAM's answers ({balance_main}, {spoil_tonight}…).

Read-only: nothing here ever changes the player's data. Every value is a ready string (Russian number format);
the answer template is translated first and the numbers are put in after, so the translation is cached once
for every player."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

# name → what it means (shown in the admin editor next to the text field)
PLAYER_VARS: Dict[str, str] = {
    "name": "Имя игрока",
    "balance_main": "Основной счёт, $CITY",
    "balance_bonus": "Бонусный счёт, $CITY",
    "balance_gram": "Основной счёт в GRAM",
    "frozen": "Заморожено под тендеры, $CITY",
    "biz_count": "Сколько у игрока бизнесов",
    "biz_name": "Первый бизнес игрока (название)",
    "biz_level": "Уровень первого бизнеса",
    "zero_left": "Сколько осталось аренды бизнеса 0 уровня (напр. «1 д 4 ч»)",
    "zero_until": "Когда кончится аренда бизнеса 0 уровня (дата МСК)",
    "shift_state": "Смена: «идёт» / «не запущена»",
    "worst_dur": "Самая низкая прочность среди бизнесов, %",
    "worst_biz": "Бизнес с самой низкой прочностью",
    "wh_used": "Занято на складе (с весами)",
    "wh_cap": "Вместимость склада",
    "wh_free": "Свободно на складе",
    "top_res": "Чего больше всего на складе (название)",
    "top_res_n": "Сколько этого ресурса",
    "spoil_tonight": "Сколько испортится сегодня в час порчи, ед.",
    "spoil_last": "Сколько испортилось в прошлый раз, ед.",
    "spoil_last_at": "Когда была прошлая порча (дата МСК)",
    "lots": "Сколько лотов на рынке",
    "lot_slots": "Сколько лотов можно выставить",
    "bought_10d": "Куплено на рынке за окно активности, шт.",
    "sold_10d": "Продано на рынке за окно активности, шт.",
    "overdue": "Просроченных кредитов",
    "pass_level": "Уровень City Pass",
    "buffs_active": "Включённые бафы и усилители (список)",
    "t3_reward": "Наградный ресурс эшелона 3 на складе (название или «нет»)",
    "ref_count": "Сколько друзей пришло по ссылке",
    "ref_link": "Реферальная ссылка игрока",
    "twofa": "2FA/Passkey: «включена» / «не включена»",
    "wallet": "Кошелёк: «подключён» / «не подключён»",
    "telegram": "Telegram: «привязан» / «не привязан»",
    "user_id": "ID игрока",
}

MSK = timezone(timedelta(hours=3))

# words that go into the numbers (the template is translated, the values are put in after → they need their language)
WORDS: Dict[str, Dict[str, str]] = {
    "running":   {"ru": "идёт", "en": "running", "es": "en marcha", "zh": "进行中", "fr": "en cours", "de": "läuft", "ja": "稼働中", "ko": "진행 중", "id": "berjalan"},
    "stopped":   {"ru": "не запущена", "en": "not started", "es": "no iniciado", "zh": "未开始", "fr": "pas lancé", "de": "nicht gestartet", "ja": "未開始", "ko": "시작 안 함", "id": "belum dimulai"},
    "on":        {"ru": "включена", "en": "on", "es": "activada", "zh": "已开启", "fr": "activée", "de": "aktiv", "ja": "有効", "ko": "켜짐", "id": "aktif"},
    "off":       {"ru": "не включена", "en": "off", "es": "desactivada", "zh": "未开启", "fr": "désactivée", "de": "nicht aktiv", "ja": "無効", "ko": "꺼짐", "id": "tidak aktif"},
    "linked":    {"ru": "подключён", "en": "connected", "es": "conectada", "zh": "已连接", "fr": "connecté", "de": "verbunden", "ja": "接続済み", "ko": "연결됨", "id": "terhubung"},
    "unlinked":  {"ru": "не подключён", "en": "not connected", "es": "no conectada", "zh": "未连接", "fr": "non connecté", "de": "nicht verbunden", "ja": "未接続", "ko": "연결 안 됨", "id": "belum terhubung"},
    "tg_on":     {"ru": "привязан", "en": "linked", "es": "vinculado", "zh": "已绑定", "fr": "lié", "de": "verknüpft", "ja": "連携済み", "ko": "연동됨", "id": "tertaut"},
    "tg_off":    {"ru": "не привязан", "en": "not linked", "es": "no vinculado", "zh": "未绑定", "fr": "non lié", "de": "nicht verknüpft", "ja": "未連携", "ko": "연동 안 됨", "id": "belum tertaut"},
    "none":      {"ru": "нет", "en": "none", "es": "ninguno", "zh": "无", "fr": "aucun", "de": "keins", "ja": "なし", "ko": "없음", "id": "tidak ada"},
    "no_biz":    {"ru": "нет бизнеса", "en": "no business", "es": "sin negocio", "zh": "没有企业", "fr": "pas d'entreprise", "de": "kein Unternehmen", "ja": "ビジネスなし", "ko": "비즈니스 없음", "id": "belum ada bisnis"},
    "empty":     {"ru": "склад пуст", "en": "warehouse is empty", "es": "almacén vacío", "zh": "仓库为空", "fr": "entrepôt vide", "de": "Lager leer", "ja": "倉庫は空", "ko": "창고 비어 있음", "id": "gudang kosong"},
    "no_buffs":  {"ru": "ничего не включено", "en": "nothing active", "es": "nada activo", "zh": "未启用任何效果", "fr": "rien d'actif", "de": "nichts aktiv", "ja": "有効なものなし", "ko": "활성화된 것 없음", "id": "tidak ada yang aktif"},
    "d":         {"ru": "д", "en": "d", "es": "d", "zh": "天", "fr": "j", "de": "T", "ja": "日", "ko": "일", "id": "h"},
    "h":         {"ru": "ч", "en": "h", "es": "h", "zh": "小时", "fr": "h", "de": "Std", "ja": "時間", "ko": "시간", "id": "j"},
    "m":         {"ru": "мин", "en": "min", "es": "min", "zh": "分钟", "fr": "min", "de": "Min", "ja": "分", "ko": "분", "id": "mnt"},
}


def _w(key: str, lang: str) -> str:
    d = WORDS.get(key) or {}
    return d.get(lang) or d.get("en") or key


def _n(x: float, d: int = 2, lang: str = "ru") -> str:
    x = round(float(x or 0), d)
    if lang in ("en", "zh", "ja", "ko"):
        s = f"{x:,.{d}f}"
        return s[: -(d + 1)] if d and s.endswith("." + "0" * d) else s
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    if d and s.endswith("," + "0" * d):
        s = s[: -(d + 1)]
    return s


def _dt(iso: Any) -> datetime:
    if isinstance(iso, datetime):
        return iso if iso.tzinfo else iso.replace(tzinfo=timezone.utc)
    d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _left(td: timedelta, lang: str = "ru") -> str:
    s = max(0, int(td.total_seconds()))
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    D, H, M = _w("d", lang), _w("h", lang), _w("m", lang)
    if d:
        return f"{d} {D} {h} {H}"
    if h:
        return f"{h} {H} {m} {M}"
    return f"{m} {M}"


async def player_vars(db, user: Dict[str, Any], lang: str = "ru") -> Dict[str, str]:
    from routes.wiki import _account
    from business_config import BUSINESSES, RESOURCE_TYPES
    out: Dict[str, str] = {"user_id": str(user.get("id") or ""), "name": user.get("username") or user.get("display_name") or "—"}
    try:
        a = await _account(db, user)
    except Exception:
        a = {"bizs": [], "stock": [], "lots": 0, "act": (0, 0), "overdue": 0, "passkeys": 0, "pass_level": 0}

    def rname(r: str) -> str:
        try:
            from wiki_content.effects import RES
            return (RES.get(r) or {}).get(lang) or (RES.get(r) or {}).get("en") or (RESOURCE_TYPES.get(r) or {}).get("name_ru") or r
        except Exception:
            return r

    def bname(code: str) -> str:
        try:
            from wiki_content.effects import BIZ
            if code in BIZ:
                return BIZ[code].get(lang) or BIZ[code]["en"]
        except Exception:
            pass
        n = (BUSINESSES.get(code) or {}).get("name") or {}
        return n.get(lang) or n.get("en") or code

    def N(x, d=2):
        return _n(x, d, lang)

    main = float(user.get("balance_ton") or 0) * 1000
    out["balance_main"] = N(main)
    out["balance_gram"] = N(float(user.get("balance_ton") or 0), 4)
    out["balance_bonus"] = N(float(user.get("bonus_balance") or 0))
    out["frozen"] = N(float(user.get("frozen_city_for_tenders") or 0))
    bizs = a.get("bizs") or []
    out["biz_count"] = str(len(bizs))
    b = a.get("biz")
    out["biz_name"] = bname(b["type"]) if b else _w("no_biz", lang)
    out["biz_level"] = str(b["level"]) if b else "—"
    out["shift_state"] = _w("running", lang) if a.get("shift") else _w("stopped", lang)
    zero = next((x for x in bizs if int(x.get("level") or 0) == 0 and x.get("expires_at")), None)
    if zero:
        try:
            exp = _dt(zero["expires_at"])
            out["zero_left"] = _left(exp - datetime.now(timezone.utc), lang)
            out["zero_until"] = exp.astimezone(MSK).strftime("%d.%m %H:%M")
        except Exception:
            out["zero_left"] = out["zero_until"] = "—"
    else:
        out["zero_left"] = out["zero_until"] = "—"
    w = a.get("worst")
    out["worst_dur"] = str(int(float(w.get("durability", 100) or 0))) if w else "—"
    out["worst_biz"] = bname(w.get("business_type")) if w else "—"
    stock = a.get("stock") or []
    out["top_res"] = rname(stock[0][0]) if stock else _w("empty", lang)
    out["top_res_n"] = N(stock[0][1], 0) if stock else "0"
    out["lots"] = str(a.get("lots") or 0)
    out["lot_slots"] = str(max(1, len(bizs)))
    bought, sold = a.get("act") or (0, 0)
    out["bought_10d"], out["sold_10d"] = str(bought), str(sold)
    out["overdue"] = str(a.get("overdue") or 0)
    out["pass_level"] = str(a.get("pass_level") or 0)
    # warehouse + tonight's spoilage (the very formula of the nightly job)
    try:
        import core.warehouse as _wh
        import warehouse_spoilage as _ws
        all_biz = await _wh.user_businesses(db, user)
        cap = _wh.total_capacity(all_biz, await _wh.buff_map_for(db, all_biz))
        listed = await _wh.listed_used(db, user)
        used = _wh.used_by_resources(user.get("resources")) + listed
        out["wh_used"], out["wh_cap"], out["wh_free"] = N(used, 0), N(cap, 0), N(max(0, cap - used), 0)
        cfg = await _ws.get_settings(db)
        p = _ws.plan(user.get("resources"), cap, listed, cfg) if cfg.get("enabled", True) else None
        out["spoil_tonight"] = N(p["lost_units"], 1) if p else "0"
    except Exception:
        out.setdefault("wh_used", "—")
        out.setdefault("wh_cap", "—")
        out.setdefault("wh_free", "—")
        out["spoil_tonight"] = "—"
    try:
        n = await db.notifications.find_one({"user_id": user.get("id"), "type": "warehouse_spoilage"}, {"_id": 0},
                                            sort=[("created_at", -1)])
        if n:
            out["spoil_last"] = N((n.get("payload") or {}).get("lost_units") or 0, 1)
            out["spoil_last_at"] = _dt(n["created_at"]).astimezone(MSK).strftime("%d.%m %H:%M")
        else:
            out["spoil_last"], out["spoil_last_at"] = "0", "—"
    except Exception:
        out["spoil_last"], out["spoil_last_at"] = "—", "—"
    # buffs: resource buffs still running
    try:
        now = datetime.now(timezone.utc)
        act = []
        for x in user.get("active_resource_buffs") or []:
            try:
                if x.get("expires_at") and _dt(x["expires_at"]) <= now:
                    continue
            except Exception:
                pass
            act.append(f"{x.get('buff_icon', '')} {rname(x.get('resource_id', '')) if x.get('resource_id') else x.get('buff_name', '')}".strip())
        out["buffs_active"] = ", ".join(act) if act else _w("no_buffs", lang)
    except Exception:
        out["buffs_active"] = "—"
    res = user.get("resources") or {}
    tut = [k[: -len("_tutorial")] for k, v in res.items() if str(k).endswith("_tutorial") and float(v or 0) >= 1]
    out["t3_reward"] = ", ".join(rname(r) for r in tut) if tut else _w("none", lang)
    try:
        out["ref_count"] = str(await db.users.count_documents({"referrerId": user.get("id")}))
    except Exception:
        out["ref_count"] = "0"
    try:
        from core.ref_links import referral_link
        out["ref_link"] = await referral_link(db, user.get("id"))
    except Exception:
        out["ref_link"] = "—"
    out["twofa"] = _w("on", lang) if (user.get("is_2fa_enabled") or a.get("passkeys")) else _w("off", lang)
    out["wallet"] = _w("linked", lang) if user.get("wallet_address") else _w("unlinked", lang)
    out["telegram"] = _w("tg_on", lang) if (user.get("telegram_chat_id") or user.get("telegram_id")) else _w("tg_off", lang)
    return out


def sample_vars() -> Dict[str, str]:
    """Example values for the admin preview when no player is chosen."""
    return {"name": "Игрок", "balance_main": "1 250", "balance_bonus": "340", "balance_gram": "1,25", "frozen": "0",
            "biz_count": "1", "biz_name": "Солнечная станция", "biz_level": "0", "zero_left": "1 д 4 ч",
            "zero_until": "15.11 21:14", "shift_state": "идёт", "worst_dur": "46", "worst_biz": "Солнечная станция",
            "wh_used": "820", "wh_cap": "1 000", "wh_free": "180", "top_res": "Энергия", "top_res_n": "640",
            "spoil_tonight": "82", "spoil_last": "75,5", "spoil_last_at": "12.11 21:00", "lots": "1", "lot_slots": "1",
            "bought_10d": "12", "sold_10d": "60", "overdue": "0", "pass_level": "3", "buffs_active": "ничего не включено",
            "t3_reward": "Нейро-ядро", "ref_count": "2", "ref_link": "https://t.me/…?start=…", "twofa": "не включена",
            "wallet": "подключён", "telegram": "привязан", "user_id": "…"}
