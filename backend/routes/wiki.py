"""«Справочник» — the game wiki: in the game, on the site (/wiki), as .md and llms.txt, and for Willy GRAM.

One article feeds every place: the in-game screen, the web page, the .md file and the support assistant.

Article (db.wiki_articles)
    slug, section, order, icon
    screens  — the screens whose «?» lists it (map, resources, trading, …; never «Бизнесы»)
    needs    — checks of «Что нужно» (CHECKS below), run on the player's account right now
    show     — «Показать на деле»: {route, steps: [{sel: [testid selectors], tap: bool}]}; texts per language
    related  — «Читайте также»
    i18n     — {lang: {t: title, s: summary, b: body, show: [step texts]}} for the 9 languages
    origin   — "seed" (comes with the code, refreshed by a newer seed) | "admin" (edited in the admin — never overwritten)
Every save keeps the previous text in db.wiki_versions.

Body markup (one block per line): `# heading`, `- bullet`, `1. step`, `> note`, `[[table:NAME]]` (a live table),
`= Term | meaning` (glossary). Inline: **bold**, [[slug|text]] (a link to an article), {{var}} (a live number:
taxes, prices, terms — read from the game settings at the moment of showing, so the translations never go stale).

  GET  /api/wiki/index?lang=            sections + article cards
  GET  /api/wiki/article/{slug}?lang=   one article, numbers filled in, live tables
  GET  /api/wiki/screen/{screen}?lang=  the articles of one screen (the «?» sheet)
  GET  /api/wiki/search?q=&lang=        search (title > summary > text, every language)
  GET  /api/wiki/check/{slug}?lang=     «Что нужно» for the signed-in player
  POST /api/wiki/feedback               «Статья помогла?»
  GET  /api/wiki/md/{slug}.md           Markdown of an article (site: /wiki/<slug>.md)
  GET  /api/wiki/llms.txt               the whole wiki as one text (site: /llms.txt)
  GET  /api/wiki/sitemap.xml            the site map of /wiki
  Admin (Russian): GET/POST /api/admin/wiki, PUT/DELETE /api/admin/wiki/{slug}, GET …/{slug}/versions,
                   POST /api/admin/wiki/translate (LibreTranslate drafts of 8 languages)
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from core.dependencies import get_current_user, get_current_admin
from core.models import User

logger = logging.getLogger(__name__)

LANGS = ["ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"]
SITE = "https://gramcity.app"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lang(v: Optional[str]) -> str:
    v = (v or "en").lower()[:2]
    return v if v in LANGS else "en"


def _pick(i18n: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """The text of one language; missing fields fall back to English, then Russian."""
    out: Dict[str, Any] = {}
    for lg in (lang, "en", "ru"):
        for k, v in ((i18n or {}).get(lg) or {}).items():
            if k not in out and v not in (None, "", []):
                out[k] = v
    return out


# ───────────────────────────── live numbers ─────────────────────────────

_VARS_CACHE: Dict[str, Any] = {"at": 0.0, "v": {}}


async def wiki_vars(db) -> Dict[str, Any]:
    """Every number an article may show, read from the game settings now (cached 60 s)."""
    if time.time() - _VARS_CACHE["at"] < 60 and _VARS_CACHE["v"]:
        return _VARS_CACHE["v"]
    v: Dict[str, Any] = {}

    def pct(x: float) -> str:
        x = round(float(x), 2)
        return str(int(x)) if x == int(x) else str(x)

    # taxes (admin «Налоги»): the sale tax of a resource / a business by its tier
    try:
        ts = await db.admin_settings.find_one({"type": "tax_settings"}, {"_id": 0})
        from server import get_business_sale_tax_rate  # the very function the sale uses
        for t in (1, 2, 3):
            v[f"tax_t{t}"] = pct(await get_business_sale_tax_rate(ts, t) * 100)
    except Exception:
        v.update({"tax_t1": "15", "tax_t2": "23", "tax_t3": "30"})
    try:
        from server import RESALE_COMMISSION, REFERRAL_RATE
        v["plot_resale"] = pct(RESALE_COMMISSION * 100)
        v["ref_pct"] = pct(REFERRAL_RATE * 100)
    except Exception:
        v.update({"plot_resale": "15", "ref_pct": "5"})
    # warehouse spoilage (admin «Порча склада»)
    try:
        import warehouse_spoilage as _ws
        s = await _ws.get_settings(db)
        v["spoil_in"], v["spoil_over"] = pct(s["in_pct"]), pct(s["over_pct"])
        v["spoil_time"] = f"{int(s['hour_msk']):02d}:{int(s['minute_msk']):02d}"
        v["spoil_on"] = bool(s.get("enabled", True))
    except Exception:
        v.update({"spoil_in": "10", "spoil_over": "20", "spoil_time": "21:00", "spoil_on": True})
    # activity rule
    try:
        import inactivity as _ia
        v["act_days"], v["act_buy"], v["act_sell"] = _ia.WINDOW_DAYS, _ia.MARKET_BUY_MIN, _ia.MARKET_SELL_MIN
    except Exception:
        v.update({"act_days": 10, "act_buy": 40, "act_sell": 100})
    # level-0 lease, lots, shifts
    try:
        from zero_lease import ZERO_LEASE_DAYS
        v["lease_days"] = ZERO_LEASE_DAYS
    except Exception:
        v["lease_days"] = 3
    try:
        from market_maker import TIER1_MIN_LOT
        v["t1_lot"] = TIER1_MIN_LOT
    except Exception:
        v["t1_lot"] = 10
    v["lot_hours"] = 48
    v["shift_hours"] = 8
    try:
        from zero_business import ZERO_PRICE_MULTIPLIER
        v["zero_mult"] = str(ZERO_PRICE_MULTIPLIER).replace(".", ",")
    except Exception:
        v["zero_mult"] = "1,2"
    # repairs
    try:
        from routes.repair import REPAIR_COST_PER_PCT
        for t in (1, 2, 3):
            v[f"repair_t{t}"] = REPAIR_COST_PER_PCT.get(t, 1)
    except Exception:
        v.update({"repair_t1": 1, "repair_t2": 5, "repair_t3": 20})
    # credits
    try:
        g = await db.game_settings.find_one({"type": "credit_settings"}, {"_id": 0}) or {}
        v["credit_rate"] = pct(float(g.get("government_interest_rate", 0.15)) * 100)
    except Exception:
        v["credit_rate"] = "15"
    rate = float(v["credit_rate"].replace(",", ".")) / 100
    v["credit_back"] = str(round(1 + 2 * rate, 2)).replace(".", ",")
    v["credit_max"], v["credit_days"], v["bank_rate_max"], v["credit_deduct"] = 30, 7, 40, 40
    # withdrawals
    v["withdraw_fee"], v["withdraw_min"], v["instant_fee_max"] = 3, 1, 5
    # rental
    try:
        import rental as _r
        cfg = await _r.get_config(db)
        v["rent_fee"] = pct(cfg.get("commission_pct", 10))
        v["rent_max_days"] = int(cfg.get("max_days", 30))
    except Exception:
        v.update({"rent_fee": "10", "rent_max_days": 30})
    # alliances, City Pass, daily login
    try:
        import alliances as _al
        a = await _al.get_config(db)
        v["alliance_level"] = int(a.get("create_min_pass_level", 5))
        v["alliance_cost"] = f"{int(a.get('create_cost_city', 5000)):,}".replace(",", " ")
    except Exception:
        v.update({"alliance_level": 5, "alliance_cost": "5 000"})
    try:
        import city_pass as _cp
        cfg = await _cp.get_config(db)
        v["pass_levels"] = int((cfg or {}).get("levels", 30))
    except Exception:
        v["pass_levels"] = 30
    try:
        d = await db.tasks_config.find_one({"key": "daily_rewards"}, {"_id": 0}) or {}
        rw = [int(x) for x in (d.get("rewards") or [5, 10, 20, 35, 50, 75, 150])]
    except Exception:
        rw = [5, 10, 20, 35, 50, 75, 150]
    v["daily_first"], v["daily_last"], v["daily_days"] = rw[0], rw[-1], len(rw)
    v["guide_steps"] = 62
    v["city_per_gram"] = "1000"
    _VARS_CACHE.update(at=time.time(), v=v)
    return v


_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def fill(text: str, v: Dict[str, Any]) -> str:
    return _VAR_RE.sub(lambda m: str(v[m.group(1)]) if m.group(1) in v else m.group(0), text or "")


_VAR1_RE = re.compile(r"\{(\w+)\}")


def fill1(text: str, v: Dict[str, Any]) -> str:
    """Single-brace placeholders of the check texts: {lvl}, {used}…"""
    return _VAR1_RE.sub(lambda m: str(v[m.group(1)]) if m.group(1) in v else m.group(0), text or "")


def tables(names: List[str], lang: str, v: Dict[str, Any]) -> Dict[str, Any]:
    """Live tables used by [[table:NAME]]. Cells may hold {res:<id>} — the app shows the resource's name and icon."""
    from wiki_content.ui import UI
    u = _pick({lg: UI.get(lg, {}) for lg in LANGS}, lang)
    out: Dict[str, Any] = {}
    for n in names:
        if n == "taxes":
            out[n] = {"head": [u["tier"], u["sale_tax"]], "rows": [
                [f"1 · {{res:energy}} {{res:biomass}} {{res:scrap}}…", f"{v['tax_t1']}%"],
                [f"2 · {{res:chips}} {{res:neurocode}}…", f"{v['tax_t2']}%"],
                [f"3 · {{res:neuro_core}} {{res:gold_bill}}…", f"{v['tax_t3']}%"]], "note": u["live_note"]}
        elif n == "weights":
            out[n] = {"head": [u["tier"], u["places"]], "rows": [["1", "1"], ["2", "5"], ["3", "20"]], "note": u["weights_note"]}
        elif n == "durability":
            out[n] = {"head": [u["durability"], u["output"]], "rows": [["50–100%", "100%"], ["1–49%", "80%"], ["0%", u["stops"]]],
                      "note": None}
        elif n == "repair":
            out[n] = {"head": [u["tier"], u["per_pct"]], "rows": [[str(t), f"{v[f'repair_t{t}']} $CITY"] for t in (1, 2, 3)],
                      "note": u["repair_note"]}
        elif n == "t3buffs":
            from wiki_content.effects import RES, T3
            try:
                from routes.buffs import RESOURCE_BUFFS
            except Exception:
                RESOURCE_BUFFS = {}
            out[n] = {"head": [u["res_col"], u["gives"], u["term"]], "rows": [
                [f"{(RESOURCE_BUFFS.get(r) or {}).get('icon', '')} {RES.get(r, {}).get(lang) or r}".strip(), T3[r].get(lang) or T3[r]["en"],
                 u["days"].replace("{d}", str((RESOURCE_BUFFS.get(r) or {}).get("duration_days", "")))] for r in T3], "note": u["t3_note"], "list": True}
        elif n == "boosters":
            from wiki_content.effects import BOOST
            icons = {"auto_shift": "🔁", "warehouse_guard": "🛡", "repair_all": "🔧", "xp_x2": "✨", "streak_shield": "🔰"}
            out[n] = {"head": [u["booster"], u["gives"]], "rows": [[f"{icons[k]} {x['n'].get(lang) or x['n']['en']}", x["d"].get(lang) or x["d"]["en"]]
                                                               for k, x in BOOST.items()], "note": u["boost_note"], "list": True}
        elif n == "patrons":
            from wiki_content.effects import PATRON
            try:
                from business_config import TIER3_BUFFS
            except Exception:
                TIER3_BUFFS = {}
            out[n] = {"head": [u["buff"], u["gives"]], "rows": [[f"{(TIER3_BUFFS.get(k) or {}).get('icon', '')} {x['n'].get(lang) or x['n']['en']}".strip(),
                                                              x["d"].get(lang) or x["d"]["en"]] for k, x in PATRON.items()], "note": u["patron_note"], "list": True}
        elif n == "upgrade_res":
            try:
                from business_config import UPGRADE_COSTS_TABLE, BUSINESSES
            except Exception:
                UPGRADE_COSTS_TABLE, BUSINESSES = {}, {}
            rows = []
            for code, lv in UPGRADE_COSTS_TABLE.items():
                r = (lv.get(2) or {}).get("resource")
                if r and code in BUSINESSES:
                    rows.append([f"{{biz:{code}}}", f"{{res:{r}}}"])
            out[n] = {"head": [u["biz_col"], u["res_col"]], "rows": rows, "note": u["upg_note"]}
        elif n == "credit":
            out[n] = {"head": [u["lender"], u["rate"]], "rows": [[u["state"], f"{v['credit_rate']}%"],
                                                                 [u["bank"], f"≤ {v['bank_rate_max']}%"]], "note": u["live_note"]}
    return out


# ───────────────────────────── «Что нужно» ─────────────────────────────

async def _account(db, user: Dict[str, Any]) -> Dict[str, Any]:
    """What the checks look at, gathered once."""
    from core.helpers import get_user_identifiers, resolve_owner_keys, owner_businesses_query
    from business_config import BUSINESSES, BUSINESS_KEY_MAP, RESOURCE_TYPES
    from core.business_rules import shift_is_active

    class _U:  # get_user_identifiers takes a User-like object
        id = user.get("id")
        email = user.get("email")
        wallet_address = user.get("wallet_address")
    ui = await get_user_identifiers(db, _U())
    ids = list(ui.get("ids") or [user.get("id")])
    keys = await resolve_owner_keys(db, user.get("id"))
    bizs = await db.businesses.find({**owner_businesses_query(keys), "tutorial": {"$ne": True}, "is_seized": {"$ne": True}},
                                    {"_id": 0}).sort("created_at", 1).to_list(50)
    a: Dict[str, Any] = {"user": user, "ids": ids, "bizs": bizs}
    if bizs:
        b = bizs[0]
        bt = BUSINESS_KEY_MAP.get(b.get("business_type"), b.get("business_type"))
        cfg = BUSINESSES.get(bt) or {}
        a["biz"] = {"id": b.get("id"), "type": bt, "level": int(b.get("level") or 0), "icon": cfg.get("icon") or "🏭",
                    "produces": cfg.get("produces") or ""}
        a["shift"] = any(shift_is_active(x) for x in bizs)
        a["worst"] = min(bizs, key=lambda x: float(x.get("durability", 100) or 0))
    res = user.get("resources") or {}
    stock = [(k, float(n or 0)) for k, n in res.items() if not str(k).endswith("_tutorial") and float(n or 0) >= 1
             and (RESOURCE_TYPES.get(k) or {}).get("tier") in (1, 2, 3)]
    stock.sort(key=lambda kv: -kv[1])
    a["stock"] = stock
    a["lots"] = await db.market_listings.count_documents({"seller_id": {"$in": ids}, "status": "active"})
    a["sold"] = bool(await db.market_listings.find_one({"seller_id": {"$in": ids}, "status": "sold"}, {"_id": 1})
                     or await db.mm_trades.find_one({"user_id": user.get("id"), "side": "buy"}, {"_id": 1}))
    a["overdue"] = await db.credits.count_documents({"borrower_id": {"$in": ids}, "status": "overdue"})
    a["passkeys"] = await db.passkeys.count_documents({"user_id": user.get("id")})
    try:
        import inactivity as _ia
        cutoff = (_now() - timedelta(days=_ia.WINDOW_DAYS)).isoformat()

        async def _sum(field):
            n = 0.0
            async for row in db.transactions.aggregate([
                    {"$match": {"tx_type": "market_purchase", "created_at": {"$gte": cutoff}, field: {"$in": ids}}},
                    {"$group": {"_id": None, "u": {"$sum": "$resource_amount"}}}]):
                n = float(row.get("u") or 0)
            return int(n)
        a["act"] = (await _sum("buyer_id"), await _sum("seller_id"))
    except Exception:
        a["act"] = (0, 0)
    try:
        import city_pass as _cp
        cfg = await _cp.get_config(db)
        p = await _cp._progress_raw(db, user.get("id"), cfg)
        a["pass_level"] = int(_cp._level(cfg, int(p.get("xp") or 0)))
    except Exception:
        a["pass_level"] = 0
    return a


def _check(cid: str, a: Dict[str, Any], v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One check → {id, state: ok|fail|info, vars: {...}, fix: slug}. Texts are added by the caller."""
    u, biz = a["user"], a.get("biz")
    if cid == "has_business":
        return {"id": cid, "state": "ok" if biz else "fail", "fix": "zero-business", "vars": {"lvl": biz["level"] if biz else 0, "biz": biz["type"] if biz else ""}}
    if cid == "biz_level1":
        ok = any(int(b.get("level") or 0) >= 1 for b in a["bizs"])
        return {"id": cid, "state": "ok" if ok else "fail", "fix": "upgrade" if biz else "zero-business", "vars": {"biz": biz["type"] if biz else "", "lvl": biz["level"] if biz else 0}}
    if cid == "shift_running":
        return {"id": cid, "state": "ok" if a.get("shift") else "fail", "fix": "shift" if biz else "zero-business", "vars": {}}
    if cid == "product_in_stock":
        top = a["stock"][0] if a["stock"] else None
        return {"id": cid, "state": "ok" if top else "fail", "fix": "shift", "vars": {"res": top[0] if top else "", "res_name": f"{{res:{top[0]}}}" if top else "", "n": int(top[1]) if top else 0}}
    if cid == "free_lot_slot":
        mx = max(1, len(a["bizs"]))
        return {"id": cid, "state": "ok" if a["lots"] < mx else "fail", "fix": "edit-lot", "vars": {"used": a["lots"], "max": mx}}
    if cid == "has_lot":
        return {"id": cid, "state": "ok" if a["lots"] else "fail", "fix": "sell", "vars": {"n": a["lots"]}}
    if cid == "sold_once":
        return {"id": cid, "state": "ok" if a["sold"] else "fail", "fix": "sell", "vars": {}}
    if cid == "main_balance":
        bal = round(float(u.get("balance_ton") or 0) * 1000, 2)
        return {"id": cid, "state": "ok" if bal > 0 else "fail", "fix": "deposit", "vars": {"v": f"{bal:,.2f}".replace(",", " ")}}
    if cid == "wallet_linked":
        return {"id": cid, "state": "ok" if u.get("wallet_address") else "fail", "fix": "deposit", "vars": {}}
    if cid == "twofa":
        return {"id": cid, "state": "ok" if (u.get("is_2fa_enabled") or a["passkeys"]) else "fail", "fix": "security", "vars": {}}
    if cid == "no_overdue":
        return {"id": cid, "state": "ok" if not a["overdue"] else "fail", "fix": "credit", "vars": {"n": a["overdue"]}}
    if cid == "durability_ok":
        w = a.get("worst")
        if not w:
            return {"id": cid, "state": "info", "fix": None, "vars": {"pct": "—", "biz": ""}}
        d = float(w.get("durability", 100) or 0)
        return {"id": cid, "state": "ok" if d >= 50 else "fail", "fix": "durability", "vars": {"pct": int(d), "biz": w.get("business_type")}}
    if cid == "activity_ok":
        b, s = a["act"]
        ok = b >= v["act_buy"] or s >= v["act_sell"]
        return {"id": cid, "state": "ok" if ok else ("fail" if a["bizs"] else "info"), "fix": "buy" if not ok else None,
                "vars": {"b": b, "s": s, "bmin": v["act_buy"], "smin": v["act_sell"], "days": v["act_days"]}}
    if cid == "telegram_linked":
        return {"id": cid, "state": "ok" if u.get("telegram_chat_id") else "fail", "fix": "notifications", "vars": {}}
    if cid == "pass_level":
        need = int(v["alliance_level"])
        return {"id": cid, "state": "ok" if a["pass_level"] >= need else "fail", "fix": "city-pass", "vars": {"need": need, "lvl": a["pass_level"]}}
    if cid == "no_zero_business":
        z = any(int(b.get("level") or 0) == 0 for b in a["bizs"])
        return {"id": cid, "state": "ok" if not z else "fail", "fix": "upgrade", "vars": {}}
    if cid == "can_claim_zero":
        ok = not a["bizs"] and not u.get("has_graduated_zero")
        return {"id": cid, "state": "ok" if ok else "info", "fix": None, "vars": {"has": 1 if a["bizs"] else 0}}
    return None


# ───────────────────────────── seed ─────────────────────────────

async def seed(db) -> int:
    """Put the articles that come with the code into the base. An article edited in the admin is never overwritten."""
    from wiki_content import ARTICLES, SEED_REV, load_texts
    texts = load_texts()
    n = 0
    for order, meta in enumerate(ARTICLES):
        slug = meta["slug"]
        i18n = {lg: texts[lg][slug] for lg in LANGS if slug in texts.get(lg, {})}
        doc = {**meta, "order": order, "i18n": i18n, "origin": "seed", "seed_rev": SEED_REV, "published": True}
        cur = await db.wiki_articles.find_one({"slug": slug}, {"_id": 0, "origin": 1, "seed_rev": 1})
        if not cur:
            doc["created_at"] = doc["updated_at"] = _now().isoformat()
            await db.wiki_articles.insert_one(doc)
            n += 1
        elif cur.get("origin") == "seed" and int(cur.get("seed_rev") or 0) < SEED_REV:
            doc["updated_at"] = _now().isoformat()
            await db.wiki_articles.update_one({"slug": slug}, {"$set": doc})
            n += 1
    _CACHE["at"] = 0
    return n


_CACHE: Dict[str, Any] = {"at": 0.0, "docs": []}


async def _all(db) -> List[Dict[str, Any]]:
    if time.time() - _CACHE["at"] < 20 and _CACHE["docs"]:
        return _CACHE["docs"]
    docs = await db.wiki_articles.find({"published": {"$ne": False}}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda d: (_SECTION_ORDER.get(d.get("section"), 99), int(d.get("order") or 0)))
    _CACHE.update(at=time.time(), docs=docs)
    return docs


def _sections():
    from wiki_content import SECTIONS
    return SECTIONS


_SECTION_ORDER: Dict[str, int] = {}


def _card(d: Dict[str, Any], lang: str, v: Dict[str, Any]) -> Dict[str, Any]:
    t = _pick(d.get("i18n") or {}, lang)
    body = fill(t.get("b", ""), v)
    return {"slug": d["slug"], "section": d.get("section"), "icon": d.get("icon"), "title": fill(t.get("t", d["slug"]), v),
            "summary": fill(t.get("s", ""), v), "minutes": max(1, round(len(body.split()) / 160)),
            "updated_at": d.get("updated_at"), "new": bool(d.get("new_until") and str(d["new_until"]) > _now().isoformat())}


def _md(d: Dict[str, Any], lang: str, v: Dict[str, Any]) -> str:
    """Markdown of one article (site .md, llms.txt, Willy GRAM)."""
    t = _pick(d.get("i18n") or {}, lang)
    body = fill(t.get("b", ""), v)
    tbl_names = re.findall(r"\[\[table:(\w+)\]\]", body)
    tb = tables(tbl_names, lang, v)
    names = {}
    try:
        from business_config import RESOURCE_TYPES
        names = {k: (m.get("name_ru") if lang == "ru" else m.get("name_en")) for k, m in RESOURCE_TYPES.items()}
    except Exception:
        pass

    bnames = {}
    try:
        from business_config import BUSINESSES
        bnames = {k: (m.get("name") or {}).get("ru" if lang == "ru" else "en") or k for k, m in BUSINESSES.items()}
    except Exception:
        pass

    def res(s):
        s = re.sub(r"\{biz:(\w+)\}", lambda m: bnames.get(m.group(1), m.group(1)), s)
        return re.sub(r"\{res:(\w+)\}", lambda m: names.get(m.group(1), m.group(1)), s)

    out = [f"# {fill(t.get('t', d['slug']), v)}", "", fill(t.get("s", ""), v), ""]
    for line in body.split("\n"):
        m = re.match(r"\[\[table:(\w+)\]\]", line.strip())
        if m and m.group(1) in tb:
            x = tb[m.group(1)]
            out += ["| " + " | ".join(x["head"]) + " |", "|" + "---|" * len(x["head"])]
            out += ["| " + " | ".join(res(c) for c in r) + " |" for r in x["rows"]]
            if x.get("note"):
                out += ["", f"_{x['note']}_"]
            continue
        line = re.sub(r"\[\[([\w-]+)\|([^\]]+)\]\]", lambda m: f"[{m.group(2)}]({SITE}/wiki/{m.group(1)})", line)
        if line.startswith("= "):
            term, _, mean = line[2:].partition("|")
            line = f"- **{term.strip()}** — {mean.strip()}"
        out.append(line)
    return "\n".join(out).strip() + "\n"


def _idf(docs: List[Dict[str, Any]], words: List[str], lang: str) -> Dict[str, float]:
    """Rare words weigh more («пропал» says more than «товар»)."""
    import math
    out = {}
    for w in words:
        df = sum(1 for d in docs if any(w in " ".join(((d.get("i18n") or {}).get(lg) or {}).get(k) or "" for k in ("t", "s", "b")).lower()
                                         for lg in (lang, "en", "ru")))
        out[w] = math.log((len(docs) + 1) / (df + 0.5)) if df else 0.0
    return out


def _score(d: Dict[str, Any], words: List[str], lang: str, idf: Optional[Dict[str, float]] = None) -> float:
    s = 0.0
    for lg in (lang, "en", "ru"):
        t = (d.get("i18n") or {}).get(lg) or {}
        title, summ, body = (t.get("t") or "").lower(), (t.get("s") or "").lower(), (t.get("b") or "").lower()
        w8 = 1.0 if lg == lang else 0.5
        for w in words:
            k = (idf or {}).get(w, 1.0) * w8
            if w in title:
                s += 6 * k
            if w in summ:
                s += 3 * k
            if w in body:
                s += (1 + min(3, body.count(w)) * 0.3) * k
    return s


def _snippet(text: str, words: List[str]) -> str:
    low = text.lower()
    pos = min([low.find(w) for w in words if low.find(w) >= 0] or [0])
    a = max(0, pos - 50)
    s = re.sub(r"\[\[table:\w+\]\]|\[\[[\w-]+\|([^\]]+)\]\]|\*\*|^[-#>=] |\n[-#>=] |\n\d+\. ", lambda m: m.group(1) or " ", text[a:a + 160])
    s = s.replace(" | ", " — ")
    return ("…" if a else "") + re.sub(r"\s+", " ", s).strip() + "…"


# ───────────────────────────── API ─────────────────────────────

_STOP = {"как", "что", "где", "почему", "зачем", "когда", "это", "мой", "моя", "мне", "меня", "мои", "для", "или", "нет", "не", "на", "в", "и", "с", "по",
         "how", "what", "where", "why", "when", "the", "is", "my", "do", "does", "can", "to", "of", "and", "a", "in", "on", "for", "i"}


class FeedbackIn(BaseModel):
    slug: str
    helpful: bool


class ArticleIn(BaseModel):
    slug: Optional[str] = None
    section: Optional[str] = None
    icon: Optional[str] = None
    screens: Optional[List[str]] = None
    needs: Optional[List[str]] = None
    related: Optional[List[str]] = None
    show: Optional[Dict[str, Any]] = None
    i18n: Optional[Dict[str, Dict[str, Any]]] = None
    published: Optional[bool] = None
    order: Optional[int] = None
    mark_new: Optional[bool] = None


class TranslateIn(BaseModel):
    t: str = ""
    s: str = ""
    b: str = ""
    show: List[str] = []


def create_wiki_router(db):
    router = APIRouter(prefix="/api/wiki", tags=["wiki"])
    admin = APIRouter(prefix="/api/admin/wiki", tags=["wiki-admin"])

    async def _prep():
        if not _SECTION_ORDER:
            for i, s in enumerate(_sections()):
                _SECTION_ORDER[s["id"]] = i
        return await _all(db), await wiki_vars(db)

    @router.get("/index")
    async def wiki_index(lang: str = "en"):
        lang = _lang(lang)
        docs, v = await _prep()
        secs = []
        for s in _sections():
            arts = [_card(d, lang, v) for d in docs if d.get("section") == s["id"]]
            secs.append({"id": s["id"], "icon": s["icon"], "title": s["t"].get(lang) or s["t"]["en"], "articles": arts})
        return {"lang": lang, "sections": secs, "count": len(docs)}

    @router.get("/article/{slug}")
    async def wiki_article(slug: str, lang: str = "en"):
        lang = _lang(lang)
        docs, v = await _prep()
        d = next((x for x in docs if x["slug"] == slug), None)
        if not d:
            raise HTTPException(status_code=404, detail="not_found")
        t = _pick(d.get("i18n") or {}, lang)
        body = fill(t.get("b", ""), v)
        show = d.get("show") or None
        if show and show.get("steps"):
            texts = [fill(x, v) for x in (t.get("show") or [])]
            show = {**show, "steps": [{**st, "text": texts[i] if i < len(texts) else ""} for i, st in enumerate(show["steps"])]}
        rel = [_card(x, lang, v) for s in (d.get("related") or []) for x in docs if x["slug"] == s]
        sec = next((s for s in _sections() if s["id"] == d.get("section")), None)
        return {**_card(d, lang, v), "body": body, "tables": tables(re.findall(r"\[\[table:(\w+)\]\]", body), lang, v),
                "needs": d.get("needs") or [], "show": show, "related": rel, "screens": d.get("screens") or [],
                "section_title": (sec["t"].get(lang) or sec["t"]["en"]) if sec else "", "section_icon": sec["icon"] if sec else "",
                "titles": {x["slug"]: _card(x, lang, v)["title"] for x in docs}}

    @router.get("/screen/{screen}")
    async def wiki_screen(screen: str, lang: str = "en"):
        lang = _lang(lang)
        docs, v = await _prep()
        return {"items": [_card(d, lang, v) for d in docs if screen in (d.get("screens") or [])]}

    @router.get("/search")
    async def wiki_search(q: str = "", lang: str = "en"):
        lang = _lang(lang)
        docs, v = await _prep()
        words = [w for w in re.findall(r"\w+", (q or "").lower()) if len(w) >= 2 and w not in _STOP][:8]
        # Russian/other endings: also try the stem (drop the last 2 letters of long words)
        words += [w[:-2] for w in words if len(w) >= 7]
        # Chinese / Japanese / Korean are written without spaces: search by pairs of characters
        for w in list(words):
            if re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", w) and len(w) > 2:
                words += [w[i:i + 2] for i in range(len(w) - 1)]
        words = list(dict.fromkeys(words))[:16]
        if not words:
            return {"items": []}
        idf = _idf(docs, words, lang)
        scored = sorted(((_score(d, words, lang, idf), d) for d in docs), key=lambda x: -x[0])
        best = scored[0][0] if scored else 0
        items = []
        for sc, d in scored:
            if sc <= 0 or sc < best * 0.3 or len(items) >= 8:
                break
            c = _card(d, lang, v)
            body = fill(_pick(d.get("i18n") or {}, lang).get("b", ""), v)
            items.append({**c, "snippet": _snippet(c["summary"] + "\n" + body, words), "words": words})
        return {"items": items}

    @router.get("/check/{slug}")
    async def wiki_check(slug: str, lang: str = "en", current_user: User = Depends(get_current_user)):
        from wiki_content.ui import CHECKS
        lang = _lang(lang)
        docs, v = await _prep()
        d = next((x for x in docs if x["slug"] == slug), None)
        if not d:
            raise HTTPException(status_code=404, detail="not_found")
        user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="user not found")
        a = await _account(db, user)
        out = []
        for cid in d.get("needs") or []:
            c = _check(cid, a, v)
            if not c:
                continue
            tx = _pick({lg: CHECKS.get(cid, {}).get(lg, {}) for lg in LANGS}, lang)
            key = {"ok": "ok", "fail": "fail", "info": "info"}[c["state"]]
            c["label"] = fill1(tx.get("t", cid), {**v, **c["vars"]})
            c["detail"] = fill1(tx.get(key) or tx.get("ok") or "", {**v, **c["vars"]})
            if c.get("fix"):
                fd = next((x for x in docs if x["slug"] == c["fix"]), None)
                c["fix_title"] = _card(fd, lang, v)["title"] if fd else ""
            out.append(c)
        biz = a.get("biz") or {}
        return {"checks": out, "ok": all(c["state"] != "fail" for c in out), "at": _now().isoformat(),
                "vars": {"bid": biz.get("id", ""), "prod": biz.get("produces", ""), "res": (a["stock"][0][0] if a["stock"] else "")}}

    @router.post("/feedback")
    async def wiki_feedback(data: FeedbackIn, request: Request):
        await db.wiki_feedback.insert_one({"slug": data.slug[:80], "helpful": bool(data.helpful), "at": _now().isoformat()})
        await db.wiki_articles.update_one({"slug": data.slug[:80]}, {"$inc": {"fb_yes" if data.helpful else "fb_no": 1}})
        return {"ok": True}

    @router.get("/md/{slug}.md")
    async def wiki_md(slug: str, lang: str = "ru"):
        docs, v = await _prep()
        d = next((x for x in docs if x["slug"] == slug), None)
        if not d:
            raise HTTPException(status_code=404, detail="not_found")
        return PlainTextResponse(_md(d, _lang(lang), v), media_type="text/markdown; charset=utf-8")

    @router.get("/llms.txt")
    async def wiki_llms(lang: str = "ru"):
        lang = _lang(lang)
        docs, v = await _prep()
        head = {"ru": "# GRAM City — Справочник\n\n> Экономическая игра в Telegram: бизнесы, ресурсы, рынок. Валюта $CITY (1 GRAM = 1000 $CITY). Ниже — все статьи Справочника.\n",
                "en": "# GRAM City — Wiki\n\n> An economy game in Telegram: businesses, resources, a market. Currency $CITY (1 GRAM = 1000 $CITY). All wiki articles follow.\n"}
        parts = [head.get(lang, head["en"]), ""]
        for s in _sections():
            parts.append(f"## {s['icon']} {s['t'].get(lang) or s['t']['en']}\n")
            for d in docs:
                if d.get("section") == s["id"]:
                    c = _card(d, lang, v)
                    parts.append(f"- [{c['title']}]({SITE}/wiki/{d['slug']}.md): {c['summary']}")
            parts.append("")
        parts.append("\n---\n")
        for d in docs:
            parts.append(_md(d, lang, v).replace("\n# ", "\n## "))
            parts.append(f"Source: {SITE}/wiki/{d['slug']}\n")
        return PlainTextResponse("\n".join(parts), media_type="text/plain; charset=utf-8")

    @router.get("/sitemap.xml")
    async def wiki_sitemap():
        docs, _ = await _prep()
        urls = [f"{SITE}/wiki"] + [f"{SITE}/wiki/{d['slug']}" for d in docs]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml += "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n"
        return Response(xml, media_type="application/xml")

    # ── admin (Russian) ──
    @admin.get("")
    async def admin_list(_: User = Depends(get_current_admin)):
        docs = await db.wiki_articles.find({}, {"_id": 0}).to_list(500)
        docs.sort(key=lambda d: (_SECTION_ORDER.get(d.get("section"), 99), int(d.get("order") or 0)))
        from wiki_content.ui import CHECKS
        return {"items": docs, "sections": [{"id": s["id"], "icon": s["icon"], "title": s["t"]["ru"]} for s in _sections()],
                "checks": [{"id": k, "title": x.get("ru", {}).get("t", k)} for k, x in CHECKS.items()],
                "vars": await wiki_vars(db), "langs": LANGS}

    def _clean(data: ArticleIn) -> Dict[str, Any]:
        upd: Dict[str, Any] = {}
        for k in ("section", "icon", "screens", "needs", "related", "show", "published", "order"):
            val = getattr(data, k)
            if val is not None:
                upd[k] = val
        if data.i18n is not None:
            upd["i18n"] = {lg: {k: (x.get(k) if k != "show" else [str(s)[:300] for s in (x.get("show") or [])])
                                for k in ("t", "s", "b", "show") if x.get(k) not in (None,)}
                           for lg, x in data.i18n.items() if lg in LANGS}
        if data.mark_new:
            upd["new_until"] = (_now() + timedelta(days=14)).isoformat()
        return upd

    async def _version(slug: str, by: str):
        cur = await db.wiki_articles.find_one({"slug": slug}, {"_id": 0})
        if cur:
            await db.wiki_versions.insert_one({"slug": slug, "at": _now().isoformat(), "by": by, "doc": cur})

    @admin.post("")
    async def admin_create(data: ArticleIn, me: User = Depends(get_current_admin)):
        slug = re.sub(r"[^a-z0-9-]", "", (data.slug or "").lower())[:60]
        if not slug or not data.section:
            raise HTTPException(status_code=400, detail="Нужны адрес статьи (латиницей) и раздел")
        if await db.wiki_articles.find_one({"slug": slug}, {"_id": 1}):
            raise HTTPException(status_code=400, detail="Статья с таким адресом уже есть")
        doc = {"slug": slug, "icon": "📄", "screens": [], "needs": [], "related": [], "show": None, "published": True,
               "order": 999, "i18n": {}, **_clean(data), "origin": "admin", "created_at": _now().isoformat(),
               "updated_at": _now().isoformat(), "updated_by": me.id}
        await db.wiki_articles.insert_one(doc)
        _CACHE["at"] = 0
        return {"ok": True, "slug": slug}

    @admin.put("/{slug}")
    async def admin_save(slug: str, data: ArticleIn, me: User = Depends(get_current_admin)):
        if not await db.wiki_articles.find_one({"slug": slug}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="Статья не найдена")
        await _version(slug, me.id)
        upd = {**_clean(data), "origin": "admin", "updated_at": _now().isoformat(), "updated_by": me.id}
        await db.wiki_articles.update_one({"slug": slug}, {"$set": upd})
        _CACHE["at"] = 0
        return {"ok": True}

    @admin.delete("/{slug}")
    async def admin_delete(slug: str, me: User = Depends(get_current_admin)):
        await _version(slug, me.id)
        # seed articles are hidden, not removed — otherwise the next start would bring them back
        await db.wiki_articles.update_one({"slug": slug}, {"$set": {"published": False, "origin": "admin", "updated_at": _now().isoformat()}})
        _CACHE["at"] = 0
        return {"ok": True}

    @admin.get("/{slug}/versions")
    async def admin_versions(slug: str, _: User = Depends(get_current_admin)):
        rows = await db.wiki_versions.find({"slug": slug}, {"_id": 0}).sort("at", -1).to_list(30)
        return {"items": rows}

    @admin.post("/translate")
    async def admin_translate(data: TranslateIn, _: User = Depends(get_current_admin)):
        """Drafts of the 8 other languages from the Russian text (LibreTranslate). Markup and {{numbers}} are kept."""
        import translation_service as ts
        if not ts.libretranslate_configured():
            raise HTTPException(status_code=503, detail="LibreTranslate не настроен (LIBRETRANSLATE_URL)")

        async def tr(text: str, lg: str) -> str:
            if not text.strip():
                return ""
            out = []
            for line in text.split("\n"):
                m = re.match(r"^(\s*(?:#|-|>|\d+\.|=)\s+)?(.*)$", line)
                pre, rest = (m.group(1) or ""), m.group(2)
                if not rest.strip() or re.fullmatch(r"\[\[table:\w+\]\]", rest.strip()):
                    out.append(line)
                    continue
                keep: List[str] = []
                rest = re.sub(r"\[\[[^\]]+\]\]", lambda mm: (keep.append(mm.group(0)), f"{{{{w{len(keep) - 1}}}}}")[1], rest)
                if pre.strip() == "=":
                    term, _, mean = rest.partition("|")
                    t2 = await ts.translate_libre_protected(term.strip(), lg, "ru")
                    m2 = await ts.translate_libre_protected(mean.strip(), lg, "ru")
                    rest = f"{t2} | {m2}"
                else:
                    rest = await ts.translate_libre_protected(rest, lg, "ru")
                rest = re.sub(r"\{\{w(\d+)\}\}", lambda mm: keep[int(mm.group(1))], rest)
                out.append(pre + rest)
            return "\n".join(out)

        drafts: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        for lg in LANGS:
            if lg == "ru":
                continue
            try:
                drafts[lg] = {"t": await tr(data.t, lg), "s": await tr(data.s, lg), "b": await tr(data.b, lg),
                              "show": [await tr(x, lg) for x in data.show]}
            except Exception as e:
                errors[lg] = str(e)[:200]
        return {"drafts": drafts, "errors": errors}

    return router, admin
