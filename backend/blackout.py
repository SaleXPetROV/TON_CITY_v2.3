"""Блэкаут острова — the whole city goes dark, the players light it again district by district.

How it goes
-----------
• Every few days (Админка → «Блэкаут»; or «Начать сейчас») the island loses power for `duration_hours`.
• Each of the 4 districts needs its own set of resources (what the players already produce). Need is scaled by the
  number of players who own a business, so a small and a big server both have to work together.
• A player gives resources from his warehouse to a district («Сдать в сеть»). It is live: every gift is pushed over
  the WebSocket, the map lights up, the feed shows «@nick: +40 ⚡ в Район 2».
• A district is lit the moment its last resource is filled:
    – every contributor of that district gets reward_pct % of the value of what he gave (bonus $CITY) + City Pass XP;
    – the top-3 contributors get their names on the district tower (map) until that district is lit again,
      and their buildings shine gold on the map;
    – the district shines: its businesses produce +lit_bonus_pct % for lit_bonus_days.
• Time is over and a district is still dark: its businesses produce −fail_penalty_pct % for fail_days,
  contributors of that district get refund_pct % of the value back.

Collections: blackout_events (one per blackout), blackout_contrib (one per gift), blackout_players (per player and
blackout: points, by district). Settings: admin_settings {type: "blackout"}.
"""
from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DISTRICTS = {
    1: {"key": "core", "x": 18.4, "y": 18.4},
    2: {"key": "north", "x": 19.1, "y": 4.9},
    3: {"key": "west", "x": 7.2, "y": 27.1},
    4: {"key": "east", "x": 30.7, "y": 26.6},
}
TIER1 = ["energy", "scrap", "quartz", "cu", "traffic", "cooling", "biomass"]
TIER2 = ["chips", "neurocode", "nft", "vr_experience", "logistics", "profit_ton", "repair_kits"]

DEFAULTS: Dict[str, Any] = {
    "enabled": False,          # the event is switched on in Админка → «События» → «Блэкаут острова»; off = nothing at all
    "auto": False,             # start by itself every interval_days (else only «Начать сейчас»)
    "interval_days": 4,
    "duration_hours": 24,
    "per_player_units": 10,    # tier-1 units of each resource a district needs per player with a business
    "min_units": 60,
    "reward_pct": 120,         # of the value of what was given, when the district is lit (bonus $CITY)
    "refund_pct": 60,          # of the value, when the district stayed dark
    "xp_per_100": 5,           # City Pass XP per 100 $CITY of value given (paid when lit)
    "xp_max": 300,
    "fail_penalty_pct": 10,
    "fail_days": 7,
    "lit_bonus_pct": 5,
    "lit_bonus_days": 3,
    "top_n": 3,
    "telegram": True,          # tell the players with a business in Telegram when it starts
    "next_at": None,
}

# ─────────────────────────────── texts (9 languages) ───────────────────────────────
T: Dict[str, Dict[str, tuple]] = {
    "start": {
        "ru": ("⚡ Блэкаут острова!", "Остров GRAM погас. У города {hours} ч, чтобы зажечь районы — сдайте ресурсы в городскую сеть. Лучшие поставщики района получат имя на его башне."),
        "en": ("⚡ Island blackout!", "GRAM Island went dark. The city has {hours} h to light its districts — give resources to the city grid. The top suppliers of a district get their names on its tower."),
        "es": ("⚡ ¡Apagón en la isla!", "La isla GRAM se apagó. La ciudad tiene {hours} h para encender sus distritos: entrega recursos a la red. Los mejores proveedores tendrán su nombre en la torre."),
        "zh": ("⚡ 岛屿停电！", "GRAM 岛陷入黑暗。城市有 {hours} 小时点亮各区——向城市电网上交资源。各区贡献最多的玩家名字将出现在区塔上。"),
        "fr": ("⚡ Black-out sur l’île !", "L’île GRAM s’est éteinte. La ville a {hours} h pour rallumer ses quartiers : donnez des ressources au réseau. Les meilleurs fournisseurs auront leur nom sur la tour."),
        "de": ("⚡ Blackout auf der Insel!", "Die GRAM-Insel ist dunkel. Die Stadt hat {hours} Std., um ihre Bezirke zu erleuchten – gib Ressourcen ans Stadtnetz. Die besten Lieferanten kommen auf den Turm."),
        "ja": ("⚡ 島が停電！", "GRAM島が真っ暗に。街には{hours}時間あります——資源を電力網に届けて地区を灯そう。上位の提供者は地区のタワーに名前が載ります。"),
        "ko": ("⚡ 섬 정전!", "GRAM 섬이 꺼졌습니다. 도시는 {hours}시간 안에 구역을 밝혀야 합니다 — 도시 전력망에 자원을 보내세요. 최고 공급자의 이름이 구역 타워에 새겨집니다."),
        "id": ("⚡ Pulau padam!", "Pulau GRAM gelap. Kota punya {hours} jam untuk menyalakan distriknya — serahkan sumber daya ke jaringan kota. Pemasok teratas namanya terpasang di menara."),
    },
    "lit": {
        "ru": ("✨ {district} снова светится!", "Вы помогли зажечь район. Награда: +{reward} $CITY и +{xp} XP City Pass."),
        "en": ("✨ {district} is shining again!", "You helped light the district. Reward: +{reward} $CITY and +{xp} City Pass XP."),
        "es": ("✨ ¡{district} vuelve a brillar!", "Ayudaste a encender el distrito. Recompensa: +{reward} $CITY y +{xp} XP de City Pass."),
        "zh": ("✨ {district} 重新亮起！", "你帮助点亮了该区。奖励：+{reward} $CITY，+{xp} City Pass 经验。"),
        "fr": ("✨ {district} brille à nouveau !", "Vous avez aidé à rallumer le quartier. Récompense : +{reward} $CITY et +{xp} XP City Pass."),
        "de": ("✨ {district} leuchtet wieder!", "Du hast geholfen, den Bezirk zu erleuchten. Belohnung: +{reward} $CITY und +{xp} City-Pass-XP."),
        "ja": ("✨ {district}に再び灯りが！", "地区の点灯に貢献しました。報酬：+{reward} $CITY、City Pass XP +{xp}。"),
        "ko": ("✨ {district}에 다시 불이 켜졌습니다!", "구역 점등에 기여했습니다. 보상: +{reward} $CITY, City Pass XP +{xp}."),
        "id": ("✨ {district} menyala lagi!", "Kamu membantu menyalakan distrik. Hadiah: +{reward} $CITY dan +{xp} XP City Pass."),
    },
    "hero": {
        "ru": ("🏆 Ваше имя на башне!", "Вы в тройке главных поставщиков: {district}. Имя на башне района и золотая подсветка вашего здания — до следующего блэкаута."),
        "en": ("🏆 Your name is on the tower!", "You are in the top 3 suppliers of {district}. Your name stays on the district tower and your building shines gold until the next blackout."),
        "es": ("🏆 ¡Tu nombre está en la torre!", "Estás entre los 3 mejores proveedores de {district}. Tu nombre en la torre y tu edificio dorado hasta el próximo apagón."),
        "zh": ("🏆 你的名字登上了塔！", "你是{district}前三名供应者。直到下次停电，你的名字留在区塔上，建筑闪耀金光。"),
        "fr": ("🏆 Votre nom est sur la tour !", "Vous êtes dans le top 3 des fournisseurs de {district}. Votre nom reste sur la tour et votre bâtiment brille en or jusqu’au prochain black-out."),
        "de": ("🏆 Dein Name steht auf dem Turm!", "Du bist unter den Top 3 Lieferanten von {district}. Dein Name bleibt auf dem Turm und dein Gebäude leuchtet golden bis zum nächsten Blackout."),
        "ja": ("🏆 タワーにあなたの名前！", "{district}の上位3名の提供者です。次の停電まで名前が地区タワーに載り、建物が金色に輝きます。"),
        "ko": ("🏆 타워에 이름이 새겨졌습니다!", "{district} 상위 3명 공급자입니다. 다음 정전까지 이름이 타워에 남고 건물이 금빛으로 빛납니다."),
        "id": ("🏆 Namamu di menara!", "Kamu 3 besar pemasok {district}. Namamu tetap di menara dan bangunanmu bersinar emas sampai pemadaman berikutnya."),
    },
    "dark": {
        "ru": ("🌑 {district} остался в темноте", "Город не успел. Бизнесы района работают на {pct}% медленнее {days} дн. Вам вернули {refund} $CITY за сданные ресурсы."),
        "en": ("🌑 {district} stayed dark", "The city ran out of time. Businesses of the district work {pct}% slower for {days} days. You got {refund} $CITY back for what you gave."),
        "es": ("🌑 {district} quedó a oscuras", "No dio tiempo. Los negocios del distrito trabajan un {pct}% más lento durante {days} días. Te devolvimos {refund} $CITY."),
        "zh": ("🌑 {district} 仍处于黑暗", "时间到了。该区企业在 {days} 天内减产 {pct}%。已退还你 {refund} $CITY。"),
        "fr": ("🌑 {district} est resté dans le noir", "Le temps est écoulé. Les entreprises du quartier tournent {pct}% plus lentement pendant {days} jours. {refund} $CITY vous ont été rendus."),
        "de": ("🌑 {district} blieb dunkel", "Die Zeit ist um. Betriebe des Bezirks arbeiten {days} Tage {pct}% langsamer. Du hast {refund} $CITY zurückbekommen."),
        "ja": ("🌑 {district}は暗いまま", "時間切れです。地区のビジネスは{days}日間{pct}%遅くなります。{refund} $CITYが返却されました。"),
        "ko": ("🌑 {district}은(는) 어둠 속에", "시간이 다 되었습니다. 구역 사업체가 {days}일간 {pct}% 느려집니다. {refund} $CITY가 반환되었습니다."),
        "id": ("🌑 {district} tetap gelap", "Waktu habis. Bisnis distrik bekerja {pct}% lebih lambat selama {days} hari. {refund} $CITY dikembalikan."),
    },
}
DNAME: Dict[str, Dict[int, str]] = {
    "ru": {1: "Центральное ядро", 2: "Северный хаб", 3: "Западный район", 4: "Восточный район"},
    "en": {1: "Central Core", 2: "North Hub", 3: "West District", 4: "East District"},
    "es": {1: "Núcleo Central", 2: "Centro Norte", 3: "Distrito Oeste", 4: "Distrito Este"},
    "zh": {1: "中央核心", 2: "北部枢纽", 3: "西区", 4: "东区"},
    "fr": {1: "Cœur central", 2: "Pôle Nord", 3: "Quartier Ouest", 4: "Quartier Est"},
    "de": {1: "Zentraler Kern", 2: "Nord-Hub", 3: "West-Bezirk", 4: "Ost-Bezirk"},
    "ja": {1: "セントラルコア", 2: "ノースハブ", 3: "西地区", 4: "東地区"},
    "ko": {1: "중앙 코어", 2: "북부 허브", 3: "서부 구역", 4: "동부 구역"},
    "id": {1: "Inti Pusat", 2: "Hub Utara", 3: "Distrik Barat", 4: "Distrik Timur"},
}


OPEN = {"ru": "⚡ Открыть блэкаут", "en": "⚡ Open the blackout", "es": "⚡ Abrir el apagón", "zh": "⚡ 打开停电", "fr": "⚡ Ouvrir le black-out",
        "de": "⚡ Blackout öffnen", "ja": "⚡ 停電を開く", "ko": "⚡ 정전 열기", "id": "⚡ Buka pemadaman"}


def _open(lang: str, **extra) -> Dict[str, Any]:
    return {"open_path": "/blackout", "open_label": OPEN.get(lang, OPEN["en"]), **extra}


def _lang(user: Optional[dict]) -> str:
    l = str((user or {}).get("language") or "en")[:2].lower()
    return l if l in DNAME else "en"


def text(key: str, lang: str, **kw) -> tuple:
    t, m = T[key].get(lang) or T[key]["en"]
    return t.format(**kw), m.format(**kw)


def dname(d: int, lang: str) -> str:
    return (DNAME.get(lang) or DNAME["en"]).get(int(d), f"#{d}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _dt(v) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def value_of(resource: str) -> float:
    from market_maker import base_city
    return base_city(resource)


# ─────────────────────────────── settings ───────────────────────────────
async def get_settings(db) -> Dict[str, Any]:
    doc = await db.admin_settings.find_one({"type": "blackout"}, {"_id": 0, "type": 0}) or {}
    return {**DEFAULTS, **doc}


NUM = {"interval_days": (1, 60), "duration_hours": (1, 168), "per_player_units": (1, 10000), "min_units": (1, 1_000_000),
       "reward_pct": (0, 500), "refund_pct": (0, 100), "xp_per_100": (0, 1000), "xp_max": (0, 100000),
       "fail_penalty_pct": (0, 50), "fail_days": (0, 30), "lit_bonus_pct": (0, 50), "lit_bonus_days": (0, 30), "top_n": (1, 10)}


async def save_settings(db, body: Dict[str, Any]) -> Dict[str, Any]:
    s = await get_settings(db)
    for k, (lo, hi) in NUM.items():
        if k in body and body[k] is not None:
            s[k] = max(lo, min(hi, float(body[k]) if k in ("interval_days",) else int(float(body[k]))))
    for k in ("enabled", "auto", "telegram"):
        if k in body:
            s[k] = bool(body[k])
    if not s["enabled"]:
        s["auto"] = False
    if s["auto"] and not s.get("next_at"):
        s["next_at"] = _iso(_now() + timedelta(hours=random.uniform(1, 12)))
    if not s["auto"]:
        s["next_at"] = None
    await db.admin_settings.update_one({"type": "blackout"}, {"$set": {**s, "type": "blackout"}}, upsert=True)
    invalidate_mult()
    if not s["enabled"]:                              # switched off: a running blackout ends without a penalty
        ev = await current(db)
        if ev:
            await finish(db, ev, reason="cancel")
    return s


async def ensure_indexes(db) -> None:
    try:
        await db.blackout_events.create_index("id", unique=True)
        await db.blackout_events.create_index("status")
        await db.blackout_contrib.create_index([("event_id", 1), ("at", -1)])
        await db.blackout_players.create_index([("event_id", 1), ("user_id", 1)], unique=True)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"blackout indexes: {e}")


# ─────────────────────────────── start ───────────────────────────────
async def active_players(db) -> int:
    try:
        owners = await db.businesses.distinct("owner", {"level": {"$gte": 1}})
        return max(1, len([o for o in owners if o]))
    except Exception:  # noqa: BLE001
        return 1


def plan_needs(players: int, s: Dict[str, Any], seed: int) -> Dict[str, Dict[str, int]]:
    """What each district needs. Districts 2–4: three tier-1 resources; the Core: two tier-1 and one tier-2."""
    rnd = random.Random(seed)
    per, mn = int(s["per_player_units"]), int(s["min_units"])
    units = max(mn, per * players)
    pool = TIER1[:]
    rnd.shuffle(pool)
    out: Dict[str, Dict[str, int]] = {}
    for i, d in enumerate((2, 3, 4)):
        picks = [pool[(i * 2 + k) % len(pool)] for k in range(3)]
        out[str(d)] = {r: int(round(units * rnd.uniform(0.85, 1.15))) for r in dict.fromkeys(picks)}
    core = rnd.sample(TIER1, 2)
    t2 = rnd.choice(TIER2)
    out["1"] = {core[0]: int(round(units * 1.2)), core[1]: int(round(units * 1.2)),
                t2: max(3, int(round(units / 25)))}
    return out


ALL_RES = TIER1 + TIER2


def clean_needs(raw: Any) -> Dict[str, Dict[str, int]]:
    """Needs typed by the admin: {"1": {"energy": 120, ...}, ...} — 4 districts, 1–5 known resources each, ≥ 1 unit."""
    if not isinstance(raw, dict):
        raise ValueError("Неверный список ресурсов")
    out: Dict[str, Dict[str, int]] = {}
    for d in ("1", "2", "3", "4"):
        x = raw.get(d) or raw.get(int(d)) or {}
        if not isinstance(x, dict):
            raise ValueError(f"Район {d}: неверный список")
        need = {}
        for r, q in x.items():
            if r not in ALL_RES:
                raise ValueError(f"Район {d}: неизвестный ресурс {r}")
            q = int(float(q))
            if q < 1 or q > 100_000_000:
                raise ValueError(f"Район {d}: количество {r} — от 1")
            need[r] = q
        if not need or len(need) > 5:
            raise ValueError(f"Район {d}: нужен от 1 до 5 ресурсов")
        out[d] = need
    return out


async def current(db) -> Optional[Dict[str, Any]]:
    return await db.blackout_events.find_one({"status": "active"}, {"_id": 0})


async def start(db, by: str = "auto", hours: Optional[float] = None,
                needs: Optional[Dict[str, Dict[str, int]]] = None) -> Dict[str, Any]:
    if await current(db):
        raise ValueError("Блэкаут уже идёт")
    s = await get_settings(db)
    if not s.get("enabled"):
        raise ValueError("Блэкаут выключен: включите его в «События» → «Блэкаут острова»")
    players = await active_players(db)
    seed = random.randint(1, 10 ** 9)
    needs = clean_needs(needs) if needs else plan_needs(players, s, seed)
    now = _now()
    dur = float(hours or s["duration_hours"])
    ev = {
        "id": str(uuid.uuid4()), "status": "active", "started_at": _iso(now), "ends_at": _iso(now + timedelta(hours=dur)),
        "by": by, "players": players, "seed": seed,
        "districts": {d: {"need": need, "got": {r: 0 for r in need}, "lit_at": None, "heroes": []} for d, need in needs.items()},
        "settings": {k: s[k] for k in ("reward_pct", "refund_pct", "xp_per_100", "xp_max", "fail_penalty_pct", "fail_days",
                                        "lit_bonus_pct", "lit_bonus_days", "top_n")},
        "participants": 0, "units": 0, "value": 0.0,
    }
    await db.blackout_events.insert_one(dict(ev))
    if s.get("auto"):
        await db.admin_settings.update_one({"type": "blackout"}, {"$set": {"next_at": None}})
    _bg(_announce_start(db, ev, s))
    await push(db, "blackout_start")
    logger.info(f"⚡ Blackout started by {by}: {players} players, needs {needs}")
    return ev


_BG: set = set()


def _bg(coro) -> None:
    t = asyncio.get_event_loop().create_task(coro)
    _BG.add(t)
    t.add_done_callback(_BG.discard)


async def _announce_start(db, ev: Dict[str, Any], s: Dict[str, Any]) -> None:
    """In-app notification to every account; Telegram to the players with a business (if on)."""
    hours = int(round((_dt(ev["ends_at"]) - _dt(ev["started_at"])).total_seconds() / 3600))
    now = _iso(_now())
    owners = set()
    try:
        owners = set(await db.businesses.distinct("owner", {"level": {"$gte": 1}}))
    except Exception:  # noqa: BLE001
        pass
    batch: List[dict] = []
    tg: List[dict] = []
    async for u in db.users.find({"id": {"$nin": [None, ""]}, "is_npc": {"$ne": True}}, {"_id": 0, "id": 1, "language": 1, "telegram_chat_id": 1}):
        lang = _lang(u)
        t, m = text("start", lang, hours=hours)
        if s.get("telegram", True) and u.get("telegram_chat_id") and u["id"] in owners:
            tg.append(u)
            continue
        batch.append({"id": str(uuid.uuid4()), "user_id": u["id"], "title": t, "message": m, "type": "blackout",
                      "priority": "warning", "read": False, "created_at": now, "payload": _open(lang, event_id=ev["id"])})
        if len(batch) >= 500:
            await db.notifications.insert_many(batch)
            batch = []
    if batch:
        await db.notifications.insert_many(batch)
    from core.notify import notify_user
    for u in tg:                                       # ~20/s: well inside Telegram's 30/s
        lang = _lang(u)
        t, m = text("start", lang, hours=hours)
        try:
            await asyncio.wait_for(notify_user(db, u["id"], title=t, message=m, type_key="blackout", priority="warning",
                                               payload=_open(lang, event_id=ev["id"]), pretranslated=True), 20)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"blackout start notify {u['id']}: {e}")
        await asyncio.sleep(0.05)


# ─────────────────────────────── contribute ───────────────────────────────
class BlackoutError(Exception):
    pass


def _remaining(dist: Dict[str, Any], res: str) -> int:
    return max(0, int(dist["need"].get(res, 0)) - int(dist["got"].get(res, 0)))


async def contribute(db, user: Dict[str, Any], district: int, resource: str, qty: int,
                     from_stock: bool = True) -> Dict[str, Any]:
    """A gift to a district. from_stock=False: the units come from elsewhere (credited straight into
    the grid) — nothing is taken from the warehouse."""
    ev = await current(db)
    if not ev:
        raise BlackoutError("no_event")
    if _dt(ev["ends_at"]) <= _now():
        raise BlackoutError("ended")
    d = str(int(district))
    dist = (ev.get("districts") or {}).get(d)
    if not dist:
        raise BlackoutError("bad_district")
    if dist.get("lit_at"):
        raise BlackoutError("already_lit")
    if resource not in dist["need"]:
        raise BlackoutError("not_needed")
    left = _remaining(dist, resource)
    if left <= 0:
        raise BlackoutError("filled")
    uid = user["id"]
    u = await db.users.find_one({"id": uid}, {"_id": 0, "resources": 1, "username": 1, "language": 1})
    if from_stock:
        have = int(float(((u or {}).get("resources") or {}).get(resource, 0) or 0))
        qty = min(int(qty), left, have)
        if qty <= 0:
            raise BlackoutError("no_resource")
        r = await db.users.update_one({"id": uid, f"resources.{resource}": {"$gte": qty}}, {"$inc": {f"resources.{resource}": -qty}})
        if not r.modified_count:
            raise BlackoutError("no_resource")
    else:
        qty = min(int(qty), left)
    r2 = await db.blackout_events.update_one({"id": ev["id"], "status": "active", f"districts.{d}.lit_at": None},
                                             {"$inc": {f"districts.{d}.got.{resource}": qty, "units": qty,
                                                       "value": round(qty * value_of(resource), 4),
                                                       }})
    if not r2.modified_count:                         # lit / ended a moment ago: give it back
        if from_stock:
            await db.users.update_one({"id": uid}, {"$inc": {f"resources.{resource}": qty}})
        raise BlackoutError("already_lit")
    pts = round(qty * value_of(resource), 4)
    name = (u or {}).get("username") or user.get("username") or "player"
    now = _iso(_now())
    await db.blackout_contrib.insert_one({"id": str(uuid.uuid4()), "event_id": ev["id"], "district": int(d), "user_id": uid,
                                          "username": name, "resource": resource, "qty": qty, "points": pts, "at": now})
    res = await db.blackout_players.update_one(
        {"event_id": ev["id"], "user_id": uid},
        {"$inc": {"points": pts, f"by_district.{d}": pts, "units": qty}, "$set": {"username": name, "last_at": now}},
        upsert=True)
    if res.upserted_id is not None:
        await db.blackout_events.update_one({"id": ev["id"]}, {"$inc": {"participants": 1}})
    lit = await _check_lit(db, ev["id"], int(d))
    await push(db, "blackout_gift", {"district": int(d), "user": name, "resource": resource, "qty": qty, "lit": bool(lit)})
    return {"ok": True, "qty": qty, "points": pts, "lit": bool(lit)}


async def _top(db, event_id: str, d: int, n: int) -> List[Dict[str, Any]]:
    rows = []
    async for p in db.blackout_players.find({"event_id": event_id, f"by_district.{d}": {"$gt": 0}},
                                            {"_id": 0, "user_id": 1, "username": 1, "by_district": 1}):
        rows.append({"user_id": p["user_id"], "username": p.get("username"), "points": round(float(p["by_district"][str(d)]), 2)})
    rows.sort(key=lambda x: -x["points"])
    return rows[:n] if n else rows


async def _check_lit(db, event_id: str, d: int) -> bool:
    ev = await db.blackout_events.find_one({"id": event_id}, {"_id": 0})
    dist = ev["districts"][str(d)]
    if dist.get("lit_at") or any(_remaining(dist, r) > 0 for r in dist["need"]):
        return False
    s = ev.get("settings") or DEFAULTS
    heroes = await _top(db, event_id, d, int(s.get("top_n", 3)))
    now = _now()
    r = await db.blackout_events.update_one(
        {"id": event_id, f"districts.{d}.lit_at": None},
        {"$set": {f"districts.{d}.lit_at": _iso(now), f"districts.{d}.heroes": heroes,
                  f"districts.{d}.bonus_until": _iso(now + timedelta(days=float(s.get("lit_bonus_days", 3))))}})
    if not r.modified_count:
        return False
    invalidate_mult()
    _bg(_reward_district(db, ev, d, heroes))
    # the whole island lit → the blackout is won
    ev = await db.blackout_events.find_one({"id": event_id}, {"_id": 0})
    if all(x.get("lit_at") for x in ev["districts"].values()):
        await db.blackout_events.update_one({"id": event_id, "status": "active"},
                                            {"$set": {"status": "won", "ended_at": _iso(_now())}})
        await _schedule_next(db)
        await push(db, "blackout_won")
    await push(db, "blackout_lit", {"district": d, "heroes": [h["username"] for h in heroes]})
    return True


async def _reward_district(db, ev: Dict[str, Any], d: int, heroes: List[Dict[str, Any]]) -> None:
    s = ev.get("settings") or DEFAULTS
    from routes.tasks import credit_task_reward_bonus
    hero_ids = {h["user_id"] for h in heroes}
    rows = await _top(db, ev["id"], d, 0)
    for row in rows:
        uid = row["user_id"]
        reward = round(row["points"] * float(s.get("reward_pct", 120)) / 100.0, 2)
        xp = int(min(float(s.get("xp_max", 300)), row["points"] / 100.0 * float(s.get("xp_per_100", 5))))
        try:
            if reward > 0:
                await credit_task_reward_bonus(db, uid, reward, f"Блэкаут: {dname(d, 'ru')} зажжён", tx_type="blackout_reward")
            if xp > 0:
                from city_pass import add_xp
                await add_xp(db, uid, "quest", xp)
            await db.blackout_players.update_one({"event_id": ev["id"], "user_id": uid},
                                                 {"$inc": {"reward": reward, "xp": xp}})
            u = await db.users.find_one({"id": uid}, {"_id": 0, "id": 1, "language": 1, "telegram_chat_id": 1})
            lang = _lang(u)
            t, m = text("lit", lang, district=dname(d, lang), reward=f"{reward:,.2f}".replace(",", " "), xp=xp)
            from core.notify import notify_user
            await notify_user(db, u or uid, title=t, message=m, type_key="blackout", priority="success",
                              payload=_open(lang), pretranslated=True, telegram=False)
            if uid in hero_ids:
                t, m = text("hero", lang, district=dname(d, lang))
                await notify_user(db, u or uid, title=t, message=m, type_key="blackout", priority="success",
                                  payload=_open(lang), pretranslated=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"blackout reward {uid}: {e}")


async def set_needs(db, needs: Dict[str, Any]) -> Dict[str, Any]:
    """The admin changes what the dark districts of the running blackout need. A lit district is not touched;
    a district whose new need is already covered lights up at once."""
    ev = await current(db)
    if not ev:
        raise ValueError("Блэкаута сейчас нет")
    clean = clean_needs({**{d: x["need"] for d, x in ev["districts"].items()}, **(needs or {})})
    upd = {}
    for d, need in clean.items():
        dist = ev["districts"][d]
        if dist.get("lit_at"):
            continue
        upd[f"districts.{d}.need"] = need
        upd[f"districts.{d}.got"] = {r: int(dist["got"].get(r, 0)) for r in need}
    if upd:
        await db.blackout_events.update_one({"id": ev["id"], "status": "active"}, {"$set": upd})
    for d in clean:
        if not ev["districts"][d].get("lit_at"):
            await _check_lit(db, ev["id"], int(d))
    await push(db, "blackout_gift")
    return await current(db) or {}


# ─────────────────────────────── end / schedule ───────────────────────────────
async def _schedule_next(db) -> None:
    s = await get_settings(db)
    if s.get("auto"):
        nxt = _now() + timedelta(days=float(s["interval_days"])) + timedelta(hours=random.uniform(-10, 10))
        await db.admin_settings.update_one({"type": "blackout"}, {"$set": {"next_at": _iso(nxt)}})


async def finish(db, ev: Dict[str, Any], reason: str = "time") -> None:
    """Time is over (or the admin stopped it): dark districts get the penalty, their contributors a refund."""
    r = await db.blackout_events.update_one({"id": ev["id"], "status": "active"},
                                            {"$set": {"status": "cancelled" if reason == "cancel" else "ended", "ended_at": _iso(_now())}})
    if not r.modified_count:
        return
    s = ev.get("settings") or DEFAULTS
    now = _now()
    from routes.tasks import credit_task_reward_bonus
    for d, dist in ev["districts"].items():
        if dist.get("lit_at"):
            continue
        refund_pct = 100.0 if reason == "cancel" else float(s.get("refund_pct", 60))
        if reason != "cancel" and float(s.get("fail_penalty_pct", 0)) > 0:
            await db.blackout_events.update_one({"id": ev["id"]}, {"$set": {
                f"districts.{d}.dark_until": _iso(now + timedelta(days=float(s.get("fail_days", 7))))}})
        for row in await _top(db, ev["id"], int(d), 0):
            refund = round(row["points"] * refund_pct / 100.0, 2)
            try:
                if refund > 0:
                    await credit_task_reward_bonus(db, row["user_id"], refund, f"Блэкаут: возврат за {dname(int(d), 'ru')}",
                                                   tx_type="blackout_refund")
                    await db.blackout_players.update_one({"event_id": ev["id"], "user_id": row["user_id"]}, {"$inc": {"refund": refund}})
                if reason != "cancel":
                    u = await db.users.find_one({"id": row["user_id"]}, {"_id": 0, "id": 1, "language": 1, "telegram_chat_id": 1})
                    lang = _lang(u)
                    t, m = text("dark", lang, district=dname(int(d), lang), pct=int(s.get("fail_penalty_pct", 10)),
                                days=int(s.get("fail_days", 7)), refund=f"{refund:,.2f}".replace(",", " "))
                    from core.notify import notify_user
                    await notify_user(db, u or row["user_id"], title=t, message=m, type_key="blackout", priority="warning",
                                      payload=_open(lang), pretranslated=True, telegram=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"blackout refund {row['user_id']}: {e}")
    invalidate_mult()
    await _schedule_next(db)
    await push(db, "blackout_end")


async def tick(db) -> Optional[str]:
    """Scheduler (every minute): end a blackout whose time is over; start one when it is due."""
    ev = await current(db)
    if ev:
        if _dt(ev["ends_at"]) <= _now():
            await finish(db, ev)
            return "ended"
        return None
    s = await get_settings(db)
    if s.get("enabled") and s.get("auto") and s.get("next_at") and _dt(s["next_at"]) <= _now():
        await start(db, by="auto")
        return "started"
    return None


# ─────────────────────────────── production effect ───────────────────────────────
_MULT: Dict[str, Any] = {"at": None, "v": {}}


def invalidate_mult() -> None:
    _MULT["at"] = None


async def district_multipliers(db) -> Dict[int, float]:
    """{district: production multiplier} — dark after a lost blackout (−%), shining after a lit one (+%)."""
    now = _now()
    if _MULT["at"] and (now - _MULT["at"]).total_seconds() < 60:
        return _MULT["v"]
    out: Dict[int, float] = {}
    if not (await get_settings(db)).get("enabled"):
        _MULT.update(at=now, v={})
        return {}
    try:
        async for ev in db.blackout_events.find({}, {"_id": 0, "districts": 1, "settings": 1, "started_at": 1}).sort("started_at", -1).limit(6):
            s = ev.get("settings") or DEFAULTS
            for d, dist in (ev.get("districts") or {}).items():
                di = int(d)
                if di in out:
                    continue                          # the newest blackout decides for that district
                du, bu = _dt(dist.get("dark_until")), _dt(dist.get("bonus_until"))
                if du and du > now:
                    out[di] = round(1 - float(s.get("fail_penalty_pct", 10)) / 100.0, 4)
                elif bu and bu > now:
                    out[di] = round(1 + float(s.get("lit_bonus_pct", 5)) / 100.0, 4)
                elif dist.get("lit_at") or du or bu:
                    out[di] = 1.0
    except Exception as e:  # noqa: BLE001
        logger.debug(f"blackout multipliers: {e}")
    _MULT.update(at=now, v={k: v for k, v in out.items() if v != 1.0})
    return _MULT["v"]


# ─────────────────────────────── public state ───────────────────────────────
async def heroes_map(db) -> Dict[str, Any]:
    """Names on the towers: for each district, the heroes of the last blackout that lit it."""
    towers: Dict[str, Any] = {}
    async for ev in db.blackout_events.find({}, {"_id": 0, "id": 1, "districts": 1, "started_at": 1}).sort("started_at", -1).limit(10):
        for d, dist in (ev.get("districts") or {}).items():
            if d in towers or not dist.get("lit_at") or not dist.get("heroes"):
                continue
            towers[d] = {"names": [h.get("username") for h in dist["heroes"]], "ids": [h.get("user_id") for h in dist["heroes"]],
                         "lit_at": dist["lit_at"]}
    return towers


def _pub_event(ev: Dict[str, Any]) -> Dict[str, Any]:
    dists = {}
    total_need = total_got = 0
    for d, dist in ev["districts"].items():
        need = {r: int(v) for r, v in dist["need"].items()}
        got = {r: min(int(dist["got"].get(r, 0)), need[r]) for r in need}
        # progress weighs every resource equally (a tier-2 unit counts as much as its share)
        pct = sum(got[r] / need[r] for r in need) / max(1, len(need)) * 100
        total_need += 1
        total_got += pct / 100
        dists[d] = {"id": int(d), "key": DISTRICTS[int(d)]["key"], "need": need, "got": got, "pct": round(pct, 1),
                    "lit_at": dist.get("lit_at"), "heroes": [{"username": h.get("username"), "points": h.get("points")} for h in dist.get("heroes") or []],
                    "dark_until": dist.get("dark_until"), "bonus_until": dist.get("bonus_until"),
                    "value": {r: value_of(r) for r in need}}
    return {"id": ev["id"], "status": ev["status"], "started_at": ev["started_at"], "ends_at": ev["ends_at"],
            "ended_at": ev.get("ended_at"), "players": ev.get("players"), "participants": ev.get("participants", 0),
            "units": ev.get("units", 0), "districts": dists, "pct": round(total_got / max(1, total_need) * 100, 1),
            "settings": ev.get("settings") or {}}


async def state(db, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not (await get_settings(db)).get("enabled"):
        return {"server_time": _iso(_now()), "enabled": False, "active": None, "last": None, "towers": {}, "multipliers": {}}
    ev = await current(db)
    last = None
    if not ev:
        last = await db.blackout_events.find_one({"status": {"$in": ["won", "ended"]}}, {"_id": 0}, sort=[("started_at", -1)])
    out: Dict[str, Any] = {"server_time": _iso(_now()), "enabled": True, "active": _pub_event(ev) if ev else None,
                           "last": _pub_event(last) if last else None, "towers": await heroes_map(db),
                           "multipliers": {str(k): v for k, v in (await district_multipliers(db)).items()}}
    s = await get_settings(db)
    out["next_at"] = s.get("next_at") if s.get("auto") else None
    the = ev or last
    if the:
        feed = []
        async for c in db.blackout_contrib.find({"event_id": the["id"]}, {"_id": 0, "username": 1, "district": 1, "resource": 1,
                                                                       "qty": 1, "at": 1}).sort("at", -1).limit(25):
            feed.append(c)
        out["feed"] = feed
        board = []
        async for p in db.blackout_players.find({"event_id": the["id"]}, {"_id": 0, "username": 1, "points": 1, "user_id": 1}).sort("points", -1).limit(10):
            board.append({"username": p.get("username"), "points": round(float(p.get("points") or 0), 2),
                          "me": bool(user and p.get("user_id") == user.get("id"))})
        out["board"] = board
        # leaders of each district (the tower is per district — so is its race)
        by_d: Dict[str, List[Dict[str, Any]]] = {}
        async for p in db.blackout_players.find({"event_id": the["id"]}, {"_id": 0, "username": 1, "by_district": 1, "user_id": 1}):
            for d, pts in (p.get("by_district") or {}).items():
                if float(pts or 0) > 0:
                    by_d.setdefault(d, []).append({"username": p.get("username"), "points": round(float(pts), 2),
                                                   "me": bool(user and p.get("user_id") == user.get("id"))})
        out["board_by_district"] = {d: sorted(v, key=lambda x: -x["points"])[:10] for d, v in by_d.items()}
        if user:
            # «your district»: where this player's businesses stand
            try:
                mine = await db.businesses.distinct("district_id", {"owner": user["id"]})
                out["my_districts"] = sorted({int(x) for x in mine if x})
            except Exception:  # noqa: BLE001
                out["my_districts"] = []
            me = await db.blackout_players.find_one({"event_id": the["id"], "user_id": user["id"]}, {"_id": 0}) or {}
            u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "resources": 1}) or {}
            needed = set(TIER1)                       # (all tier-1 too)
            for dist in the["districts"].values():
                needed.update(dist["need"].keys())
            out["me"] = {"points": round(float(me.get("points") or 0), 2), "units": me.get("units", 0),
                         "by_district": me.get("by_district") or {}, "reward": me.get("reward", 0), "xp": me.get("xp", 0),
                         "refund": me.get("refund", 0),
                         "have": {r: int(float((u.get("resources") or {}).get(r, 0) or 0)) for r in needed}}
    return out


# ─────────────────────────────── live push ───────────────────────────────
_PUSH: Dict[str, Any] = {"t": 0.0, "pending": False}


async def push(db, kind: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Tell every open app: something changed. Gifts are sent at most ~2 times a second (each with its own detail);
    the clients fetch /api/blackout themselves (with their own «me»)."""
    import time as _time
    now = _time.monotonic()
    if kind == "blackout_gift" and now - _PUSH["t"] < 0.4:
        return                                         # a burst of gifts: the clients' poll catches up
    _PUSH["t"] = now
    try:
        from core.websocket import manager
        await manager.broadcast({"type": "blackout", "event": kind, "data": data or {}})
    except Exception as e:  # noqa: BLE001
        logger.debug(f"blackout push: {e}")
