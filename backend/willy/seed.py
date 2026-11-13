"""Puts the answer base that comes with the code into db.willy_answers.

• the hand-written answers (willy/answers_ru.py);
• answers built from the game config, so they always match the code: every business (what it makes, what it uses,
  what its upgrade needs), every resource (who makes it, who needs it), every buff of a tier-3 resource, every
  booster and every patron buff.
An answer edited in the admin (origin "admin") is never overwritten; a seed answer is refreshed when SEED_REV grows."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

SEED_REV = 2


def _ru_list(xs: List[str]) -> str:
    xs = [x for x in xs if x]
    if not xs:
        return "—"
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " и " + xs[-1]


def generated() -> List[Dict[str, Any]]:
    from business_config import BUSINESSES, RESOURCE_TYPES, UPGRADE_COSTS_TABLE
    from wiki_content.effects import RES, T3, BOOST, PATRON
    try:
        from routes.buffs import RESOURCE_BUFFS
    except Exception:
        RESOURCE_BUFFS = {}
    try:
        from business_config import TIER3_BUFFS
    except Exception:
        TIER3_BUFFS = {}

    def rn(r):
        return (RES.get(r) or {}).get("ru") or (RESOURCE_TYPES.get(r) or {}).get("name_ru") or r

    def bn(code):
        from wiki_content.effects import BIZ
        n = BIZ.get(code) or (BUSINESSES.get(code) or {}).get("name") or {}
        return n.get("ru") or n.get("en") or code

    out: List[Dict[str, Any]] = []
    # businesses
    for code, b in BUSINESSES.items():
        from wiki_content.effects import BIZ
        name = bn(code)
        en = (BIZ.get(code) or {}).get("en") or (b.get("name") or {}).get("en") or ""
        old = (b.get("name") or {}).get("ru") or ""
        prod = rn(b.get("produces"))
        cons = [f"{rn(r)} ({str(v).replace('.', ',')} на ед.)" for r, v in (b.get("consumes") or {}).items()]
        up = (UPGRADE_COSTS_TABLE.get(code, {}).get(2) or {}).get("resource")
        text = (f"{b.get('icon', '🏭')} {name} — бизнес эшелона {b.get('tier')}. Производит: {prod}. "
                + (f"Тратит в смену: {_ru_list(cons)}. " if cons else "Сырьё не нужно. ")
                + (f"Для улучшения до ур. 2 и выше нужен ещё ресурс «{rn(up)}»." if up else ""))
        q = [f"что производит {name}", f"что делает {name}", f"{name}", f"что тратит {name}", f"сырье для {name}",
             f"что нужно для улучшения {name}", f"какой ресурс нужен для апгрейда {name}", f"{name} что дает",
             f"стоит ли покупать {name}", f"чем полезен {name}"]
        if en:
            q += [en, f"what does {en} produce"]
        if old and old != name:
            q += [old, f"что производит {old}"]
        out.append({"key": f"biz:{code}", "topic": "business", "title": f"{name}: что производит и что тратит",
                    "wiki": "chains", "text": text.strip(), "phrasings": q, "checks": [], "route": None})
    # resources
    for r, info in RESOURCE_TYPES.items():
        name = rn(r)
        makers = [bn(c) for c, b in BUSINESSES.items() if b.get("produces") == r]
        users = [bn(c) for c, b in BUSINESSES.items() if r in (b.get("consumes") or {})]
        ups = [bn(c) for c, lv in UPGRADE_COSTS_TABLE.items() if (lv.get(2) or {}).get("resource") == r]
        tier = info.get("tier")
        text = f"«{name}» — ресурс эшелона {tier}. Производит: {_ru_list(makers)}. Купить можно в Торговле → «Купить». "
        if users:
            text += f"Сырьё для: {_ru_list(users)}. "
        if ups:
            text += f"Нужен для улучшения бизнесов: {_ru_list(ups)}. "
        if r in T3:
            text += f"Можно включить как баф: {T3[r]['ru']}."
        q = [f"где взять {name}", f"где купить {name}", f"кто производит {name}", f"для чего нужен {name}", f"зачем {name}",
             f"что такое {name}", f"{name}", f"откуда брать {name}", f"{name} где достать"]
        out.append({"key": f"res:{r}", "topic": "warehouse", "title": f"{name}: где взять и для чего", "wiki": "resources",
                    "text": text.strip(), "phrasings": q, "checks": [], "route": None})
    # buffs of tier-3 resources
    for r, d in T3.items():
        name, bb = rn(r), RESOURCE_BUFFS.get(r) or {}
        text = (f"{bb.get('icon', '🔮')} {name} как баф: {d['ru']}, {bb.get('duration_days', 7)} дн. на все ваши бизнесы. "
                f"Склад → Усилители → «Активировать» (тратится 1 шт.). Не включается сам. Сейчас включено: {{buffs_active}}.")
        q = [f"что дает {name}", f"баф {name}", f"какой баф у {name}", f"что будет если активировать {name}",
             f"зачем активировать {name}", f"эффект {name}", f"{name} баф сколько дней", f"как работает {name}",
             f"как использовать {name}", f"{name} активировать", f"как включить {name}", f"как активировать {name}",
             f"куда применить {name}", f"бустануть бизнес {name}"]
        out.append({"key": f"t3:{r}", "topic": "warehouse", "title": f"Баф: {name}", "wiki": "t3-buffs", "text": text,
                    "phrasings": q, "checks": [], "route": "/resources"})
    icons = {"auto_shift": "🔁", "warehouse_guard": "🛡", "repair_all": "🔧", "xp_x2": "✨", "streak_shield": "🔰"}
    for k, x in BOOST.items():
        name = x["n"]["ru"]
        text = f"{icons.get(k, '⚡')} {name}: {x['d']['ru']} Включается в Склад → Усилители. Продать нельзя."
        q = [f"что дает {name}", f"{name}", f"усилитель {name}", f"как работает {name}", f"зачем {name}",
             f"как включить {name}", f"{name} что это"]
        out.append({"key": f"boost:{k}", "topic": "warehouse", "title": f"Усилитель: {name}", "wiki": "boosters",
                    "text": text, "phrasings": q, "checks": [], "route": "/resources"})
    for k, x in PATRON.items():
        name = x["n"]["ru"]
        icon = (TIER3_BUFFS.get(k) or {}).get("icon", "✨")
        text = (f"{icon} «{name}» — баф покровителя: {x['d']['ru']} Его выбирает владелец бизнеса-покровителя "
                f"(эшелон 3) для своих подопечных.")
        q = [f"что дает {name}", f"баф {name}", f"{name}", f"что такое {name}", f"{name} покровитель"]
        out.append({"key": f"patron:{k}", "topic": "business", "title": f"Баф покровителя: {name}", "wiki": "patron-buffs",
                    "text": text, "phrasings": q, "checks": [], "route": None})
    return out


def all_seed() -> List[Dict[str, Any]]:
    from .answers_ru import H
    from .answers_gen import all_generated
    return list(H) + generated() + all_generated()


async def seed(db) -> int:
    from . import index as _index
    now = datetime.now(timezone.utc).isoformat()
    cur = {d["key"]: d async for d in db.willy_answers.find({"key": {"$ne": None}}, {"_id": 0, "key": 1, "origin": 1, "seed_rev": 1})}
    from pymongo import UpdateOne
    new, upd, n = [], [], 0
    for a in all_seed():
        doc = {**a, "origin": "seed", "seed_rev": SEED_REV, "updated_at": now}
        doc.setdefault("handoff", False)
        doc.setdefault("agent_only", False)
        c = cur.get(a["key"])
        if not c:
            doc.update(id=str(uuid.uuid4()), enabled=True, status="ok", created_at=now,
                       stats={"shown": 0, "helped": 0, "not_helped": 0})
            new.append(doc)
        elif c.get("origin") == "seed" and int(c.get("seed_rev") or 0) < SEED_REV:
            upd.append(UpdateOne({"key": a["key"]}, {"$set": doc}))
    for i in range(0, len(new), 500):
        await db.willy_answers.insert_many(new[i:i + 500])
    for i in range(0, len(upd), 500):                 # a newer seed refreshes thousands of answers: in batches
        await db.willy_answers.bulk_write(upd[i:i + 500], ordered=False)
    n += len(new) + len(upd)
    if n:
        await _index.bump(db)
    return n
