"""Доставка по контрактам: a contract delivery is a truck that drives along the island's roads.

At the contract's clearing the money moves as before, the goods leave the supplier's warehouse and go on the road:
a SHIPMENT drives from the supplier's business to the buyer's business along the real streets of the map (every tile
that is not a lot and not a park is a road). It arrives after `tiles × min_per_tile` minutes (clamped), then the goods
land in the buyer's warehouse (whatever fits; the rest waits at the gate until there is room).

  • Blackout (only when the admin starts one; by default the city is lit): a dark district's streets take ×1.5 as long —
    the truck keeps driving, slower, and its arrival time moves on accordingly.
  • Paid speed-up: the buyer or the supplier can make a truck arrive NOW for `speedup_city_per_min` $CITY per minute
    that is left (at least `speedup_min_fee`). The money goes to the project's treasury (ledger kind delivery_speedup).
  • Map: the buyer and the supplier see their truck AND its road; everybody else sees only the trucks moving
    (no road). The client gets departed/arrives + the road's corner points and moves the truck itself — no polling of
    positions, no load on the server or the map.
  • A business whose every input is covered by active contracts runs its shifts by itself (auto-shift).

Collections: shipments. Settings: admin_settings type "deliveries".
"""
from __future__ import annotations

import logging
import math
import uuid
import heapq
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CITY = 1000.0
LANGS = ("ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id")

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "min_per_tile": 3.0,         # minutes a truck needs for one road tile
    "min_minutes": 10,
    "max_minutes": 240,
    "speedup_enabled": True,
    "speedup_city_per_min": 2.0,  # $CITY per minute left
    "speedup_min_fee": 10.0,
    "blackout_delays": True,     # a blackout (started by the admin) slows trucks on dark streets
    "blackout_slowdown": 1.5,    # …a dark tile takes this many times longer; the truck keeps driving
    "others_on_map": 60,         # how many trucks of other players a map shows at most
    "auto_shift": True,
}
NUM = {"min_per_tile": (0.1, 60), "min_minutes": (0, 1440), "max_minutes": (1, 2880), "speedup_city_per_min": (0, 100000),
       "speedup_min_fee": (0, 1000000), "others_on_map": (0, 500), "blackout_slowdown": (1, 5)}
BOOL = ("enabled", "speedup_enabled", "blackout_delays", "auto_shift")
OPEN = ("in_transit", "waiting_room")

T = {
    "arr_t": {"ru": "🚚 Груз прибыл", "en": "🚚 Cargo arrived", "es": "🚚 Llegó la carga", "zh": "🚚 货物已到达", "fr": "🚚 Cargaison arrivée",
              "de": "🚚 Ladung angekommen", "ja": "🚚 荷物が到着", "ko": "🚚 화물 도착", "id": "🚚 Muatan tiba"},
    "arr_m": {"ru": "{qty} {res} от @{seller} — на складе.", "en": "{qty} {res} from @{seller} is in your warehouse.",
              "es": "{qty} {res} de @{seller} ya está en tu almacén.", "zh": "来自 @{seller} 的 {qty} 个{res}已入库。",
              "fr": "{qty} {res} de @{seller} est dans votre entrepôt.", "de": "{qty} {res} von @{seller} ist im Lager.",
              "ja": "@{seller} からの{res} {qty} 個が倉庫に入りました。", "ko": "@{seller}의 {res} {qty}개가 창고에 들어왔습니다.",
              "id": "{qty} {res} dari @{seller} sudah di gudangmu."},
    "room_t": {"ru": "📦 Груз ждёт у ворот", "en": "📦 Cargo is waiting at the gate", "es": "📦 La carga espera en la puerta",
               "zh": "📦 货物在门口等待", "fr": "📦 La cargaison attend au portail", "de": "📦 Ladung wartet am Tor",
               "ja": "📦 荷物が門で待っています", "ko": "📦 화물이 문 앞에서 대기 중", "id": "📦 Muatan menunggu di gerbang"},
    "room_m": {"ru": "{qty} {res} от @{seller} не помещаются на склад. Освободите место — груз разгрузится сам.",
               "en": "{qty} {res} from @{seller} don't fit in the warehouse. Free some room — it unloads by itself.",
               "es": "{qty} {res} de @{seller} no caben en el almacén. Libera espacio y se descargará solo.",
               "zh": "来自 @{seller} 的 {qty} 个{res}放不进仓库。腾出空间后会自动卸货。",
               "fr": "{qty} {res} de @{seller} ne rentrent pas dans l’entrepôt. Libérez de la place — le déchargement se fera seul.",
               "de": "{qty} {res} von @{seller} passen nicht ins Lager. Mach Platz — sie werden von selbst entladen.",
               "ja": "@{seller} からの{res} {qty} 個が倉庫に入りません。空きを作れば自動で荷下ろしされます。",
               "ko": "@{seller}의 {res} {qty}개가 창고에 들어가지 않습니다. 공간을 비우면 자동으로 하역됩니다.",
               "id": "{qty} {res} dari @{seller} tidak muat di gudang. Kosongkan tempat — akan dibongkar sendiri."},
    "open": {"ru": "Контракты", "en": "Contracts", "es": "Contratos", "zh": "合同", "fr": "Contrats", "de": "Verträge", "ja": "契約",
             "ko": "계약", "id": "Kontrak"},
}


class DeliveryError(Exception):
    def __init__(self, code: str, **extra):
        super().__init__(code)
        self.code = code
        self.extra = extra


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: Optional[datetime] = None) -> str:
    return (d or _now()).isoformat()


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


def _lang(u: Optional[dict]) -> str:
    lg = ((u or {}).get("language") or "en")[:2]
    return lg if lg in LANGS else "en"


def tr(key: str, lang: str, **kw) -> str:
    t = T[key].get(lang) or T[key]["en"]
    try:
        return t.format(**kw)
    except (KeyError, IndexError):
        return t


def res_name(r: str, lang: str) -> str:
    try:
        from wiki_content.effects import RES
        x = RES.get(r) or {}
        return x.get(lang) or x.get("en") or r
    except Exception:  # noqa: BLE001
        return r


async def get_settings(db) -> Dict[str, Any]:
    doc = await db.admin_settings.find_one({"type": "deliveries"}, {"_id": 0}) or {}
    s = dict(DEFAULTS)
    s.update({k: v for k, v in doc.items() if k in DEFAULTS})
    return s


async def save_settings(db, body: Dict[str, Any]) -> Dict[str, Any]:
    s = await get_settings(db)
    for k, (lo, hi) in NUM.items():
        if k in body and body[k] not in (None, ""):
            v = float(body[k])
            if not lo <= v <= hi:
                raise ValueError(k)
            s[k] = int(v) if k in ("min_minutes", "max_minutes", "others_on_map") else v
    for k in BOOL:
        if k in body:
            s[k] = bool(body[k])
    if s["min_minutes"] > s["max_minutes"]:
        raise ValueError("min_minutes")
    await db.admin_settings.update_one({"type": "deliveries"}, {"$set": {**s, "type": "deliveries"}}, upsert=True)
    return s


async def ensure_indexes(db) -> None:
    try:
        await db.shipments.create_index("id", unique=True)
        await db.shipments.create_index([("status", 1), ("arrives_at", 1)])
        await db.shipments.create_index("buyer_id")
        await db.shipments.create_index("seller_id")
        await db.shipments.create_index("contract_id")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"shipments indexes: {e}")


# ───────────────────────────── the road graph ─────────────────────────────
@lru_cache(maxsize=1)
def _roads() -> Dict[str, Any]:
    """Road tiles of the island (not a lot, not a park), each with the district it belongs to (the nearest lot's)."""
    from city_island import load_layout
    lay = load_layout()
    n = int(lay["grid"])
    cover, slots = {}, {}
    for s in lay["slots"]:
        slots[(s["x"], s["y"])] = s
        for i in range(s["w"]):
            for j in range(s["h"]):
                cover[(s["x"] + i, s["y"] + j)] = s
    parks = {tuple(p) if isinstance(p, (list, tuple)) else tuple(int(v) for v in str(p).split(",")) for p in lay["parks"]}
    road = {(x, y) for x in range(n) for y in range(n) if (x, y) not in cover and (x, y) not in parks}
    centres = [((s["x"] + s["w"] / 2.0, s["y"] + s["h"] / 2.0), int(s["district"])) for s in lay["slots"]]
    dist = {}
    for (x, y) in road:
        best, bd = None, 1e9
        for (cx, cy), d in centres:
            dd = (cx - x - 0.5) ** 2 + (cy - y - 0.5) ** 2
            if dd < bd:
                bd, best = dd, d
        dist[(x, y)] = best or 1
    return {"n": n, "road": road, "slots": slots, "district": dist}


def _gates(x: int, y: int, w: int, h: int) -> List[Tuple[int, int]]:
    """Road tiles touching a lot (where a truck can stop)."""
    R = _roads()["road"]
    out = []
    for i in range(-1, w + 1):
        for j in range(-1, h + 1):
            inside = 0 <= i < w and 0 <= j < h
            corner = (i in (-1, w)) and (j in (-1, h))
            if inside or corner:
                continue
            p = (x + i, y + j)
            if p in R:
                out.append(p)
    if out:
        return out
    # a lot inside a block (only other lots / parks around it): its gate is the nearest street
    n = _roads()["n"]
    start = [(x + i, y + j) for i in range(w) for j in range(h)]
    seen = set(start)
    q = deque((p, 0) for p in start)
    best = None
    while q:
        p, dd = q.popleft()
        if best is not None and dd > best:
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (p[0] + d[0], p[1] + d[1])
            if nb in seen or not (0 <= nb[0] < n and 0 <= nb[1] < n):
                continue
            seen.add(nb)
            if nb in R:
                best = dd + 1
                out.append(nb)
            else:
                q.append((nb, dd + 1))
    return out


def _corners(path: List[Tuple[int, int]]) -> List[List[int]]:
    """Keep only the points where the road turns (a short list for the client)."""
    if len(path) <= 2:
        return [list(p) for p in path]
    out = [list(path[0])]
    for a, b, c in zip(path, path[1:], path[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(list(b))
    out.append(list(path[-1]))
    return out


@lru_cache(maxsize=4096)
def road_between(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> Dict[str, Any]:
    """The shortest street route from lot `a` (x, y, w, h) to lot `b`: {tiles, corners, districts}."""
    R = _roads()
    src, dst = _gates(*a), set(_gates(*b))
    if not src or not dst:
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        tiles = abs(ax - bx) + abs(ay - by)
        return {"tiles": max(1, tiles), "corners": [[ax, ay], [bx, ay], [bx, by]], "districts": []}
    # shortest by tiles, and among equally short ones the one with the fewest turns: a truck follows the street
    # instead of zig-zagging across a square (a turn costs a little, never a longer road)
    TURN = 0.01
    best = {}
    heap = []
    for p0 in src:
        best[(p0, None)] = 0.0
        heapq.heappush(heap, (0.0, p0, None))
    prev = {}
    end = None
    while heap:
        c, p, d0 = heapq.heappop(heap)
        if c > best.get((p, d0), 1e18):
            continue
        if p in dst:
            end = (p, d0)
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (p[0] + d[0], p[1] + d[1])
            if nb not in R["road"]:
                continue
            nc = c + 1.0 + (TURN if d0 is not None and d != d0 else 0.0)
            if nc < best.get((nb, d), 1e18):
                best[(nb, d)] = nc
                prev[(nb, d)] = (p, d0)
                heapq.heappush(heap, (nc, nb, d))
    if end is None:
        return {"tiles": abs(a[0] - b[0]) + abs(a[1] - b[1]), "corners": [[a[0], a[1]], [b[0], b[1]]], "districts": []}
    path = []
    st = end
    while st is not None:
        path.append(st[0])
        st = prev.get(st)
    path.reverse()
    seen, dists = set(), []
    for p in path:
        d = R["district"].get(p)
        if d and d not in seen:
            seen.add(d)
            dists.append(d)
    return {"tiles": len(path), "corners": _corners(path), "districts": dists}


def _pack(corners: List[List[int]]) -> List[str]:
    """Road points as "x,y" strings: portable (some Mongo-compatible stores reject nested arrays) and compact."""
    return [f"{int(x)},{int(y)}" for x, y in corners]


def _unpack(v) -> List[List[int]]:
    out = []
    for p in v or []:
        if isinstance(p, str):
            x, y = p.split(",")
            out.append([int(x), int(y)])
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            out.append([int(p[0]), int(p[1])])
    return out


def _lot_of(b: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    if not b or b.get("x") is None or b.get("y") is None:
        return None
    s = _roads()["slots"].get((int(b["x"]), int(b["y"])))
    fp = b.get("footprint") or {}
    w = (s or {}).get("w") or fp.get("w") or 1
    h = (s or {}).get("h") or fp.get("h") or 1
    return (int(b["x"]), int(b["y"]), int(w), int(h))


@lru_cache(maxsize=4096)
def _path_of(corners: Tuple[Tuple[int, int], ...]) -> Tuple[Tuple[int, int], ...]:
    """The road tiles again from its turning points (each leg is straight along one axis)."""
    if not corners:
        return ()
    out = [corners[0]]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        dx, dy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
        x, y = ax, ay
        while (x, y) != (bx, by):
            x, y = x + dx, y + dy
            out.append((x, y))
            if len(out) > 10000:
                break
    return tuple(out)


def _tile_districts(sh: Dict[str, Any]) -> List[Optional[int]]:
    path = _path_of(tuple(tuple(p) for p in _unpack(sh.get("corners"))))
    D = _roads()["district"]
    return [D.get(p) for p in path]


def minutes_for(tiles: int, s: Dict[str, Any]) -> int:
    return int(max(s["min_minutes"], min(s["max_minutes"], math.ceil(tiles * float(s["min_per_tile"])))))


async def _business_for(db, user_id: str, resource: str, want: str) -> Optional[Dict[str, Any]]:
    """want='produce' → the supplier's business making the resource; 'consume' → the buyer's business eating it."""
    from business_config import BUSINESSES, BUSINESS_KEY_MAP, get_consumption_breakdown
    best, score = None, -1.0
    async for b in db.businesses.find({"owner": user_id}, {"_id": 0}):
        t = BUSINESS_KEY_MAP.get(b.get("business_type"), b.get("business_type"))
        if want == "produce":
            sc = float(b.get("level") or 0) if (BUSINESSES.get(t) or {}).get("produces") == resource else -1
        else:
            sc = float((get_consumption_breakdown(t, int(b.get("level") or 1)) or {}).get(resource, 0) or 0)
        if sc > score or best is None:
            best, score = b, sc
    return best


# ───────────────────────────── dispatch / arrive ─────────────────────────────
async def dispatch(db, contract: Dict[str, Any], qty: float, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """The goods have left the supplier (tenders clearing took them). Put them on the road to the buyer.
    Returns the shipment — or None when deliveries are off (the caller then credits the buyer at once)."""
    s = await get_settings(db)
    if not s.get("enabled"):
        return None
    now = now or _now()
    res = contract["resource_type"]
    sb = await _business_for(db, contract["seller_id"], res, "produce")
    bb = await _business_for(db, contract["buyer_id"], res, "consume")
    a, b = _lot_of(sb), _lot_of(bb)
    if a and b:
        road = road_between(a, b)
    else:
        road = {"tiles": 20, "corners": [], "districts": []}
    mins = minutes_for(road["tiles"], s)
    sh = {
        "id": str(uuid.uuid4()), "contract_id": contract["id"], "resource": res, "qty": float(qty), "qty_left": float(qty),
        "seller_id": contract["seller_id"], "buyer_id": contract["buyer_id"],
        "seller_name": contract.get("seller_username"), "buyer_name": contract.get("buyer_username"),
        "from": list(a) if a else None, "to": list(b) if b else None, "from_biz": (sb or {}).get("id"), "to_biz": (bb or {}).get("id"),
        "corners": _pack(road["corners"]), "districts": road["districts"], "tiles": road["tiles"], "minutes": mins,
        "departed_at": _iso(now), "arrives_at": _iso(now + timedelta(minutes=mins)), "status": "in_transit",
        "dark": False, "slow": False, "delayed_min": 0, "speedup_paid_city": 0.0, "created_at": _iso(now),
        "pos": 0.0, "pos_n": len(_path_of(tuple(tuple(p) for p in road["corners"]))) or max(1, int(road["tiles"])), "tick_at": _iso(now),
    }
    await db.shipments.insert_one(dict(sh))
    await _ws(sh, "shipment_departed")
    return sh


async def _ws(sh: Dict[str, Any], kind: str) -> None:
    try:
        from core.websocket import manager
        msg = {"type": kind, "shipment_id": sh["id"], "contract_id": sh.get("contract_id")}
        await manager.send_personal(msg, sh["buyer_id"])
        await manager.send_personal(msg, sh["seller_id"])
    except Exception:  # noqa: BLE001
        pass


async def _notify(db, sh: Dict[str, Any], kt: str, km: str, qty: float, priority: str = "info") -> None:
    try:
        u = await db.users.find_one({"id": sh["buyer_id"]}, {"_id": 0})
        if not u:
            return
        lang = _lang(u)
        from core.notify import notify_user
        await notify_user(db, u, title=tr(kt, lang), message=tr(km, lang, qty=int(round(qty)), res=res_name(sh["resource"], lang),
                                                                  seller=sh.get("seller_name") or "—"),
                          type_key="delivery", priority=priority,
                          payload={"shipment_id": sh["id"], "open_path": "/trading?tab=operations", "open_label": tr("open", lang)},
                          pretranslated=True, telegram=False)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"delivery notify: {e}")


async def _unload(db, sh: Dict[str, Any], now: datetime) -> str:
    """Put what fits into the buyer's warehouse; the rest waits at the gate."""
    from core import warehouse as wh
    buyer = await db.users.find_one({"id": sh["buyer_id"]}, {"_id": 0})
    if not buyer:
        await db.shipments.update_one({"id": sh["id"]}, {"$set": {"status": "lost", "closed_at": _iso(now)}})
        return "lost"
    left = float(sh.get("qty_left", sh["qty"]))
    room = max(0.0, float(await wh.room_for(db, buyer, sh["resource"])))
    put = min(left, math.floor(room) if room < left else left)
    if put > 0:
        await db.users.update_one({"id": sh["buyer_id"]}, {"$inc": {f"resources.{sh['resource']}": put}})
    rest = round(left - put, 6)
    if rest <= 1e-9:
        await db.shipments.update_one({"id": sh["id"]}, {"$set": {"status": "delivered", "qty_left": 0, "delivered_at": _iso(now)}})
        await _notify(db, sh, "arr_t", "arr_m", sh["qty"])
        await _ws(sh, "shipment_arrived")
        return "delivered"
    first_wait = sh.get("status") != "waiting_room"
    await db.shipments.update_one({"id": sh["id"]}, {"$set": {"status": "waiting_room", "qty_left": rest, "waiting_since": sh.get("waiting_since") or _iso(now)}})
    if first_wait:
        await _notify(db, sh, "room_t", "room_m", rest, priority="warning")
        await _ws(sh, "shipment_waiting")
    return "waiting_room"


async def _dark_districts(db) -> set:
    try:
        import blackout
        ev = await blackout.current(db)
        return {int(d) for d, x in ((ev or {}).get("districts") or {}).items() if not x.get("lit_at")}
    except Exception:  # noqa: BLE001
        return set()


def _drive(sh: Dict[str, Any], dark: set, k: float, now: datetime) -> Dict[str, Any]:
    """Move the truck on by the time since its last tick and work out when it arrives.
    A tile costs base seconds (the trip's minutes spread over its tiles); a tile in a dark district costs k× as long —
    the truck keeps driving, only slower. Returns {pos (tiles done), n, arrives_at, dark (on a dark tile now),
    slow (a dark tile still ahead), delayed_min}."""
    dists = _tile_districts(sh)
    n = len(dists) or max(1, int(sh.get("tiles") or 1))
    dep = _dt(sh.get("departed_at")) or now
    base = max(1.0, float(sh.get("minutes") or 1) * 60.0) / n
    cost = [base * (k if (dists and dists[i] in dark) else 1.0) for i in range(n)]
    pos = sh.get("pos")
    last = _dt(sh.get("tick_at")) or dep
    if pos is None:                                   # a truck from before this model: where it is by its old timetable
        arr0 = _dt(sh.get("arrives_at")) or now
        span = max(1.0, (arr0 - dep).total_seconds())
        pos = n * min(1.0, max(0.0, (last - dep).total_seconds() / span))
    pos = float(pos)
    left = max(0.0, (now - last).total_seconds())
    while left > 1e-9 and pos < n - 1e-9:
        idx = int(pos)
        need = (idx + 1 - pos) * cost[idx]
        if left >= need:
            left -= need
            pos = float(idx + 1)
        else:
            pos += left / cost[idx]
            left = 0.0
    pos = min(float(n), pos)
    idx = min(n - 1, int(pos))
    rest = 0.0 if pos >= n - 1e-9 else (idx + 1 - pos) * cost[idx] + sum(cost[idx + 1:])
    arr = now + timedelta(seconds=rest)
    plain = dep + timedelta(minutes=float(sh.get("minutes") or 0))
    return {"pos": round(pos, 4), "n": n, "arrives_at": arr, "dark": bool(dists) and pos < n and dists[idx] in dark,
            "slow": bool(dists) and any(d in dark for d in dists[idx:]) and pos < n,
            "delayed_min": round(max(float(sh.get("delayed_min") or 0), (arr - plain).total_seconds() / 60.0, 0.0), 1)}


async def tick(db, now: Optional[datetime] = None) -> Dict[str, int]:
    """Every minute: trucks move on (slower on dark streets), trucks that got there unload, goods at the gate retry."""
    s = await get_settings(db)
    now = now or _now()
    out = {"arrived": 0, "waiting": 0, "slow": 0}
    dark = await _dark_districts(db) if s.get("blackout_delays") else set()
    k = float(s.get("blackout_slowdown") or 1.5)
    done = set()                                      # one unload per shipment per tick
    async for sh in db.shipments.find({"status": "in_transit"}, {"_id": 0}).limit(2000):
        d = _drive(sh, dark, k, now)
        upd = {"tick_at": _iso(now), "pos": d["pos"], "pos_n": d["n"], "arrives_at": _iso(d["arrives_at"]), "dark": d["dark"],
               "slow": d["slow"], "delayed_min": d["delayed_min"]}
        if d["slow"]:
            out["slow"] += 1
        await db.shipments.update_one({"id": sh["id"], "status": "in_transit"}, {"$set": upd})
        if d["pos"] >= d["n"] - 1e-6:
            done.add(sh["id"])
            r = await _unload(db, {**sh, **upd}, now)
            out["arrived" if r == "delivered" else "waiting"] += 1
    async for sh in db.shipments.find({"status": "waiting_room"}, {"_id": 0}).limit(500):
        if sh["id"] in done:
            continue
        r = await _unload(db, sh, now)
        if r == "delivered":
            out["arrived"] += 1
    return out


# ───────────────────────────── paid speed-up ─────────────────────────────
def speedup_price(sh: Dict[str, Any], s: Dict[str, Any], now: Optional[datetime] = None) -> Optional[float]:
    if not s.get("speedup_enabled") or sh.get("status") != "in_transit":
        return None
    left = max(0.0, ((_dt(sh.get("arrives_at")) or _now()) - (now or _now())).total_seconds() / 60.0)
    if left <= 0.5:
        return None
    return round(max(float(s["speedup_min_fee"]), math.ceil(left) * float(s["speedup_city_per_min"])), 2)


async def speedup(db, user: Dict[str, Any], shipment_id: str) -> Dict[str, Any]:
    """«Доставить сейчас»: the buyer or the supplier pays; the money goes to the project's treasury."""
    s = await get_settings(db)
    sh = await db.shipments.find_one({"id": shipment_id}, {"_id": 0})
    if not sh or user["id"] not in (sh["buyer_id"], sh["seller_id"]):
        raise DeliveryError("not_found")
    now = _now()
    price = speedup_price(sh, s, now)
    if price is None:
        raise DeliveryError("cannot")
    # claim first: two quick taps never pay twice
    claim = await db.shipments.update_one({"id": shipment_id, "status": "in_transit", "speeding": {"$ne": True}}, {"$set": {"speeding": True}})
    if not claim.modified_count:
        raise DeliveryError("cannot")
    from core.balance import debit_user_split
    pay = await debit_user_split(db, {"id": user["id"]}, price / CITY)
    if not pay.get("ok"):
        await db.shipments.update_one({"id": shipment_id}, {"$set": {"speeding": False}})
        raise DeliveryError("no_money", price=price)
    await db.admin_stats.update_one({"type": "treasury"}, {"$inc": {"delivery_speedup_ton": price / CITY, "total_tax": price / CITY}}, upsert=True)
    try:
        import ledger
        await ledger.record(db, "delivery_speedup", price / CITY, real_ton=pay.get("from_real", 0), user_id=user["id"], ref=shipment_id,
                            note="Ускорение доставки")
    except Exception:  # noqa: BLE001
        pass
    await db.transactions.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "type": "delivery_speedup", "tx_type": "delivery_speedup",
                                      "amount": -price / CITY, "amount_ton": -price / CITY, "amount_city": -price, "shipment_id": shipment_id,
                                      "resource_type": sh["resource"], "resource_amount": sh["qty"], "status": "completed",
                                      "description": f"Ускорение доставки: {int(sh['qty'])} {res_name(sh['resource'], 'ru')}",
                                      "created_at": _iso(now)})
    await db.shipments.update_one({"id": shipment_id}, {"$set": {"arrives_at": _iso(now), "speeding": False, "dark": False, "slow": False},
                                                        "$inc": {"speedup_paid_city": price}})
    sh = await db.shipments.find_one({"id": shipment_id}, {"_id": 0})
    r = await _unload(db, sh, now)
    return {"ok": True, "paid_city": price, "status": r}


# ───────────────────────────── reads ─────────────────────────────
def _frac(sh: Dict[str, Any]) -> float:
    """How much of the road is behind the truck at `pos_at` (0…1); the client moves it on from there to `arrives_at`."""
    if sh.get("pos") is None:
        return 0.0
    return round(min(1.0, max(0.0, float(sh["pos"]) / max(1, int(sh.get("pos_n") or sh.get("tiles") or 1)))), 4)


def pub(sh: Dict[str, Any], me: Optional[str], s: Dict[str, Any], lang: str, now: datetime, with_road: bool = True) -> Dict[str, Any]:
    side = "in" if sh["buyer_id"] == me else "out" if sh["seller_id"] == me else None
    out = {"id": sh["id"], "contract_id": sh.get("contract_id"), "resource": sh["resource"], "res_name": res_name(sh["resource"], lang),
           "qty": sh["qty"], "qty_left": sh.get("qty_left", sh["qty"]), "status": sh["status"], "side": side,
           "departed_at": sh["departed_at"], "arrives_at": sh["arrives_at"], "minutes": sh.get("minutes"), "dark": bool(sh.get("dark")),
           "slow": bool(sh.get("slow")), "pos": _frac(sh), "pos_at": sh.get("tick_at") or sh["departed_at"],
           "delayed_min": sh.get("delayed_min", 0), "seller_name": sh.get("seller_name"), "buyer_name": sh.get("buyer_name"),
           "from": sh.get("from"), "to": sh.get("to"), "delivered_at": sh.get("delivered_at")}
    if side:
        out["speedup_price"] = speedup_price(sh, s, now)
    if with_road:
        out["corners"] = _unpack(sh.get("corners"))
    return out


async def my_shipments(db, user: Dict[str, Any]) -> Dict[str, Any]:
    s = await get_settings(db)
    now = _now()
    me = user["id"]
    lang = _lang(await db.users.find_one({"id": me}, {"_id": 0, "language": 1}))
    rows = [x async for x in db.shipments.find({"$or": [{"buyer_id": me}, {"seller_id": me}]}, {"_id": 0}).sort("created_at", -1).limit(40)]
    return {"shipments": [pub(x, me, s, lang, now, with_road=False) for x in rows], "server_now": _iso(now),
            "settings": {"speedup_enabled": s["speedup_enabled"], "speedup_city_per_min": s["speedup_city_per_min"],
                         "speedup_min_fee": s["speedup_min_fee"], "blackout_slowdown": s.get("blackout_slowdown", 1.5)}}


async def map_data(db, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trucks on the road. Mine (buyer or supplier) come with their road; the others' trucks come with the road too
    (the client needs it to move the truck along the streets) but the client never draws it."""
    s = await get_settings(db)
    now = _now()
    me = (user or {}).get("id")
    mine, others = [], []
    q = {"status": "in_transit"}
    async for sh in db.shipments.find(q, {"_id": 0}).sort("departed_at", -1).limit(2000):
        if not sh.get("corners"):
            continue
        row = {"id": sh["id"], "corners": _unpack(sh["corners"]), "departed_at": sh["departed_at"], "arrives_at": sh["arrives_at"],
               "pos": _frac(sh), "pos_at": sh.get("tick_at") or sh["departed_at"], "dark": bool(sh.get("dark")),
               "slow": bool(sh.get("slow")), "resource": sh["resource"],
               "from": sh.get("from"), "to": sh.get("to")}            # the two lots: the road is drawn building → building
        if me and me in (sh["buyer_id"], sh["seller_id"]):
            row["side"] = "in" if sh["buyer_id"] == me else "out"
            mine.append(row)
        elif len(others) < int(s["others_on_map"]):
            others.append(row)
    return {"mine": mine, "others": others, "server_now": _iso(now)}


async def contract_fed_business_ids(db) -> set:
    """Businesses whose every input is covered by the owner's active contracts — they run shifts by themselves."""
    s = await get_settings(db)
    if not s.get("auto_shift"):
        return set()
    per: Dict[str, Dict[str, float]] = {}
    async for c in db.tender_contracts.find({"status": "ACTIVE"}, {"_id": 0, "buyer_id": 1, "resource_type": 1, "daily_amount": 1}):
        per.setdefault(c["buyer_id"], {}).setdefault(c["resource_type"], 0.0)
        per[c["buyer_id"]][c["resource_type"]] += float(c.get("daily_amount") or 0)
    if not per:
        return set()
    from business_config import BUSINESS_KEY_MAP, get_consumption_breakdown
    out = set()
    async for b in db.businesses.find({"owner": {"$in": list(per)}}, {"_id": 0, "id": 1, "owner": 1, "business_type": 1, "level": 1}):
        t = BUSINESS_KEY_MAP.get(b.get("business_type"), b.get("business_type"))
        need = {r: float(v) for r, v in (get_consumption_breakdown(t, int(b.get("level") or 1)) or {}).items() if float(v) > 0}
        have = per.get(b["owner"], {})
        if need and all(have.get(r, 0) + 1e-9 >= d for r, d in need.items()):
            out.add(b["id"])
    return out


async def availability(db, btype: str, level: int, lang: str) -> List[Dict[str, Any]]:
    """Before buying a business: can its raw materials be had? (players who make them, market lots, open tenders)"""
    from business_config import BUSINESSES, BUSINESS_KEY_MAP, get_consumption_breakdown
    t = BUSINESS_KEY_MAP.get(btype, btype)
    out = []
    for r, day in (get_consumption_breakdown(t, int(level or 1)) or {}).items():
        if float(day) <= 0:
            continue
        prods = [k for k, c in BUSINESSES.items() if c.get("produces") == r]
        players = len(await db.businesses.distinct("owner", {"business_type": {"$in": prods}, "level": {"$gte": 1}})) if prods else 0
        lots = await db.market_listings.count_documents({"resource_type": r, "status": "active"})
        out.append({"resource": r, "res_name": res_name(r, lang), "per_day": round(float(day), 1), "players": players,
                    "market_lots": lots, "ok": bool(players or lots)})
    return out


async def admin_state(db) -> Dict[str, Any]:
    now = _now()
    since = _iso(now - timedelta(hours=24))
    st = {"in_transit": await db.shipments.count_documents({"status": "in_transit"}),
          "waiting": await db.shipments.count_documents({"status": "waiting_room"}),
          "delivered_24h": await db.shipments.count_documents({"status": "delivered", "delivered_at": {"$gte": since}})}
    sp24 = mins = n = 0.0
    async for x in db.shipments.find({"created_at": {"$gte": since}}, {"_id": 0, "speedup_paid_city": 1, "minutes": 1}):
        sp24 += float(x.get("speedup_paid_city") or 0)
        mins += float(x.get("minutes") or 0)
        n += 1
    tr_doc = await db.admin_stats.find_one({"type": "treasury"}, {"_id": 0, "delivery_speedup_ton": 1}) or {}
    st.update({"speedup_24h_city": round(sp24, 2), "speedup_total_city": round(float(tr_doc.get("delivery_speedup_ton") or 0) * CITY, 2),
               "avg_minutes": round(mins / n, 1) if n else 0})
    s = await get_settings(db)
    rows = [pub(x, None, s, "ru", now, with_road=False) for x in await db.shipments.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)]
    return {"settings": s, "stats": st, "shipments": rows}


# ───────────────────────────── one-time cleanup (round 3 rework) ─────────────────────────────
async def retire_legacy(db) -> Dict[str, int]:
    """The oligarchs (round 2) and the separate supply routes (round 3) were removed: clear what they left in the DB.
    Runs once (flag in admin_settings type "migrations")."""
    flag = await db.admin_settings.find_one({"type": "migrations"}, {"_id": 0}) or {}
    out = {}
    if not flag.get("retire_legacy_notifications"):
        # the bell: notices of the removed routes / oligarchs (their «Снабжение» button leads nowhere now)
        try:
            out["notices"] = (await db.notifications.delete_many({"$or": [
                {"type": {"$regex": "^(supply_route|oligarch)"}},
                {"payload.open_path": {"$in": ["/supply", "/oligarchs"]}}]})).deleted_count
            await db.admin_settings.update_one({"type": "migrations"}, {"$set": {"type": "migrations",
                                                                                 "retire_legacy_notifications": _iso()}}, upsert=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"retire legacy notices: {e}")
    if flag.get("retire_oligarchs_routes"):
        return {k: v for k, v in out.items() if v}
    try:
        out["npc_lots"] = (await db.market_listings.update_many({"seller_id": {"$regex": "^npc-"}, "status": "active"},
                                                                {"$set": {"status": "cancelled", "cancelled_at": _iso()}})).modified_count
        out["npc_chat"] = (await db.chat_messages.delete_many({"$or": [{"sender_id": {"$regex": "^npc-"}},
                                                                       {"recipient_id": {"$regex": "^npc-"}}]})).deleted_count
        out["npc_users"] = (await db.users.delete_many({"id": {"$regex": "^npc-"}, "is_npc": True})).deleted_count
        out["deals"] = (await db.oligarch_deals.update_many({"status": "open"}, {"$set": {"status": "closed"}})).modified_count
        out["routes"] = (await db.supply_routes.update_many({"status": {"$in": ["proposed", "countered", "active", "paused"]}},
                                                            {"$set": {"status": "ended", "end_reason": "removed"}})).modified_count
        await db.admin_settings.update_one({"type": "oligarchs"}, {"$set": {"enabled": False}})
        await db.admin_settings.update_one({"type": "migrations"}, {"$set": {"type": "migrations", "retire_oligarchs_routes": _iso()}}, upsert=True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"retire oligarchs/routes: {e}")
    return out
