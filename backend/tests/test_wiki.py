"""«Справочник»: the seed texts are complete in 9 languages, numbers are live, the API answers, admin edits survive."""
import asyncio
import re

import mongomock_motor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes.wiki as W
from wiki_content import ARTICLES, LANGS, SECTIONS, load_texts
from wiki_content.ui import CHECKS, UI


def run(c):
    return asyncio.run(c)


KNOWN_VARS = None


def _vars():
    global KNOWN_VARS
    if KNOWN_VARS is None:
        W._VARS_CACHE.update(at=0, v={})
        KNOWN_VARS = run(W.wiki_vars(mongomock_motor.AsyncMongoMockClient()["w"]))
    return KNOWN_VARS


def test_every_article_in_every_language():
    texts = load_texts()
    slugs = {a["slug"] for a in ARTICLES}
    assert len(slugs) == len(ARTICLES) >= 55
    for lg in LANGS:
        assert set(texts[lg]) == slugs, lg
        for a in ARTICLES:
            x = texts[lg][a["slug"]]
            assert x["t"] and x["s"] and x["b"], (lg, a["slug"])
            steps = len((a["show"] or {}).get("steps", [])) if a["show"] else 0
            assert len(x.get("show", [])) == steps, (lg, a["slug"])


def test_markup_matches_russian_and_vars_are_known():
    texts, v = load_texts(), _vars()
    slugs = {a["slug"] for a in ARTICLES}
    for lg in LANGS:
        for a in ARTICLES:
            ru, x = texts["ru"][a["slug"]], texts[lg][a["slug"]]
            assert re.findall(r"\[\[table:(\w+)\]\]", x["b"]) == re.findall(r"\[\[table:(\w+)\]\]", ru["b"]), (lg, a["slug"])
            for name in re.findall(r"\{\{(\w+)\}\}", x["t"] + x["s"] + x["b"] + " ".join(x.get("show", []))):
                assert name in v, (lg, a["slug"], name)
            for link in re.findall(r"\[\[([\w-]+)\|", x["b"]):
                assert link in slugs, (lg, a["slug"], link)


def test_structure_is_consistent():
    sec = {s["id"] for s in SECTIONS}
    slugs = {a["slug"] for a in ARTICLES}
    for a in ARTICLES:
        assert a["section"] in sec
        assert set(a["related"]) <= slugs, a["slug"]
        assert set(a["needs"]) <= set(CHECKS), a["slug"]
        assert "business" not in a["screens"]          # no «?» on «Бизнесы»
    for cid, tx in CHECKS.items():
        assert set(tx) == set(LANGS), cid
    for lg in LANGS:
        assert set(UI[lg]) == set(UI["ru"]), lg
        assert all(s["t"].get(lg) for s in SECTIONS)


def test_numbers_come_from_settings():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["w"]
        W._VARS_CACHE.update(at=0, v={})
        await db.game_settings.insert_one({"type": "warehouse_spoilage", "in_pct": 12, "over_pct": 25, "hour_msk": 20, "minute_msk": 30})
        v = await W.wiki_vars(db)
        assert (v["spoil_in"], v["spoil_over"], v["spoil_time"]) == ("12", "25", "20:30")
        assert W.fill("в {{spoil_time}} — {{spoil_in}}%", v) == "в 20:30 — 12%"
        t = W.tables(["taxes", "durability", "credit"], "ru", v)
        assert t["taxes"]["head"] == ["Эшелон", "Налог с продажи"] and len(t["taxes"]["rows"]) == 3
        W._VARS_CACHE.update(at=0, v={})
    run(go())


def test_checks_logic():
    v = _vars()
    a = {"user": {"id": "u", "balance_ton": 0}, "bizs": [{"level": 0, "durability": 40}], "biz": {"type": "helios", "level": 0, "id": "b", "produces": "energy"},
         "shift": False, "worst": {"durability": 40, "business_type": "helios"}, "stock": [("energy", 30.0)], "lots": 1,
         "sold": False, "overdue": 0, "passkeys": 0, "act": (0, 120), "pass_level": 2}
    st = {c: W._check(c, a, v)["state"] for c in CHECKS}
    assert st["has_business"] == "ok" and st["biz_level1"] == "fail" and st["shift_running"] == "fail"
    assert st["free_lot_slot"] == "fail"           # 1 business → 1 slot, already used
    assert st["durability_ok"] == "fail" and st["activity_ok"] == "ok" and st["pass_level"] == "fail"
    assert st["no_zero_business"] == "fail" and st["main_balance"] == "fail" and st["twofa"] == "fail"
    assert W._check("product_in_stock", a, v)["vars"]["res_name"] == "{res:energy}"


def _app(db, monkeypatch, admin=False):
    from core.dependencies import get_current_user, get_current_admin
    from core.models import User
    app = FastAPI()
    r, ar = W.create_wiki_router(db)
    app.include_router(r)
    app.include_router(ar)
    me = User(id="u1", email="t@example.com", username="t")
    app.dependency_overrides[get_current_user] = lambda: me
    app.dependency_overrides[get_current_admin] = lambda: me
    return TestClient(app)


def test_api_seed_read_search_check_and_admin(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["w"]
    W._CACHE.update(at=0, docs=[])
    W._VARS_CACHE.update(at=0, v={})
    assert run(W.seed(db)) == len(ARTICLES)
    run(db.users.insert_one({"id": "u1", "resources": {"energy": 40}, "balance_ton": 0}))
    c = _app(db, monkeypatch)
    idx = c.get("/api/wiki/index?lang=de").json()
    assert len(idx["sections"]) == 9 and idx["count"] == len(ARTICLES)
    art = c.get("/api/wiki/article/spoilage?lang=ru").json()
    assert "{{" not in art["body"] and art["show"]["steps"][0]["text"]
    assert c.get("/api/wiki/article/nope").status_code == 404
    hits = c.get("/api/wiki/search", params={"q": "почему пропал товар", "lang": "ru"}).json()["items"]
    assert hits and hits[0]["slug"] in ("faq", "spoilage")
    scr = {x["slug"] for x in c.get("/api/wiki/screen/resources?lang=en").json()["items"]}
    assert {"spoilage", "boosters", "capacity"} <= scr
    ck = c.get("/api/wiki/check/sell?lang=ru").json()
    assert [x["id"] for x in ck["checks"]] == ["product_in_stock", "free_lot_slot"]
    assert ck["checks"][0]["state"] == "ok"
    md = c.get("/api/wiki/md/credit.md?lang=en").text
    assert md.startswith("# ") and "| Lender | Rate |" in md
    assert "## " in c.get("/api/wiki/llms.txt?lang=ru").text
    assert "<loc>https://gramcity.app/wiki/faq</loc>" in c.get("/api/wiki/sitemap.xml").text
    # an admin edit is kept, a newer seed does not overwrite it, the old text is in the versions
    body = {"i18n": {"ru": {"t": "Порча товара", "s": "x", "b": "Текст", "show": ["шаг"]}}}
    assert c.put("/api/admin/wiki/spoilage", json=body).json()["ok"]
    assert len(c.get("/api/admin/wiki/spoilage/versions").json()["items"]) == 1
    import wiki_content
    monkeypatch.setattr(wiki_content, "SEED_REV", 999)
    run(W.seed(db))
    W._CACHE["at"] = 0
    assert c.get("/api/wiki/article/spoilage?lang=ru").json()["title"] == "Порча товара"
    # hide = unpublished, not gone
    c.delete("/api/admin/wiki/faq")
    W._CACHE["at"] = 0
    assert c.get("/api/wiki/article/faq").status_code == 404
    assert c.post("/api/admin/wiki", json={"slug": "new-one", "section": "rules"}).json()["slug"] == "new-one"
    W._CACHE.update(at=0, docs=[])
