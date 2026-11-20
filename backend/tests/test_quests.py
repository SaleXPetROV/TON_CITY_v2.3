"""Tests for the in-game quest engine (backend/quests.py).

Runs against an in-memory Mongo (mongomock-motor), no server needed:
    pip install mongomock-motor
    cd backend && python -m pytest tests/test_quests.py -q
"""
import asyncio

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
from fastapi import HTTPException  # noqa: E402

import quests  # noqa: E402


def run(coro):
    return asyncio.run(coro)


async def _fresh_db(with_business=True, uid="u1"):
    db = mongomock_motor.AsyncMongoMockClient()["test_quests"]
    quests.init(db)
    quests._tpl_cache["items"] = []
    quests._seeded = False
    quests._indexes_ready = False
    await db.users.insert_one({"id": uid, "email": f"{uid}@x.io", "language": "ru",
                               "balance_ton": 1.0, "bonus_balance": 0.0, "xp": 0})
    if with_business:
        await db.businesses.insert_one({"id": f"b-{uid}", "owner": uid, "business_type": "helios", "level": 1})
    return db


def test_period_keys_are_msk_day_and_iso_week():
    assert quests.period_key("onboarding") == "once"
    assert len(quests.period_key("daily")) == 10
    assert "-W" in quests.period_key("weekly")


def test_event_progress_ready_and_atomic_claim():
    async def go():
        db = await _fresh_db()
        await quests.quest_event("u1", "market_list", 1)
        ov = await quests.build_overview("u1", "ru")
        ob = {x["id"]: x for x in ov["onboarding"]["items"]}
        assert ob["ob_open_business"]["status"] == "ready"      # state-based
        assert ob["ob_first_list"]["status"] == "ready"      # event-based
        assert ob["ob_first_sale"]["status"] == "active"
        assert ov["next"]["action"] == "claim"

        r = await quests.claim("u1", "ob_first_list", "ru")
        assert {k: r["granted"][k] for k in ("city", "xp", "capped")} == {"city": 15, "xp": 20, "capped": False}
        with pytest.raises(HTTPException) as e:
            await quests.claim("u1", "ob_first_list", "ru")
        assert e.value.status_code == 409
        with pytest.raises(HTTPException) as e:
            await quests.claim("u1", "ob_first_sale", "ru")
        assert e.value.status_code == 400

        u = await db.users.find_one({"id": "u1"})
        assert abs(u["bonus_balance"] - 0.015) < 1e-9   # bonus, not real balance
        assert u["balance_ton"] == 1.0
        assert u["xp"] == 20
        tx = await db.transactions.find_one({"user_id": "u1", "tx_type": "quest_reward"})
        assert tx and tx["reward_city"] == 15
    run(go())


def test_concurrent_claims_pay_once():
    async def go():
        db = await _fresh_db()
        await quests.quest_event("u1", "market_list", 1)
        await quests.build_overview("u1", "ru")
        res = await asyncio.gather(*[quests.claim("u1", "ob_first_list", "ru") for _ in range(5)],
                                   return_exceptions=True)
        assert sum(1 for x in res if isinstance(x, dict)) == 1
        u = await db.users.find_one({"id": "u1"})
        assert abs(u["bonus_balance"] - 0.015) < 1e-9
    run(go())


def test_unique_event_is_counted_once():
    async def go():
        await _fresh_db()
        for _ in range(3):
            await quests.quest_event("u1", "market_list", 1, unique="lot:42")
        ids = await quests.ensure_assignment("u1", "daily")
        if "d_list_lot" in ids:
            doc = await quests._DB.user_quests.find_one({"user_id": "u1", "quest_id": "d_list_lot"})
            assert doc["status"] == "ready"
        # the log keeps one row only
        assert await quests._DB.quest_event_log.count_documents({"user_id": "u1", "unique": "lot:42"}) == 1
    run(go())


def test_daily_goals_one_per_difficulty_and_arcade_ones_without_a_business():
    async def go():
        await _fresh_db(with_business=False, uid="nobiz")
        # no business: daily goals are still there — buy / sell / list (shift and repair need a business)
        nb = await quests.ensure_assignment("nobiz", "daily")
        assert len(nb) == 3 and not {"d_shift", "d_repair"} & set(nb), nb
        await _fresh_db(uid="biz")
        ids = await quests.ensure_assignment("biz", "daily")
        tpls = {t["id"]: t for t in await quests.get_templates()}
        assert sorted(tpls[i]["difficulty"] for i in ids) == ["easy", "good", "medium"]
        assert await quests.ensure_assignment("biz", "daily") == ids   # stable for the day
    run(go())


def test_daily_bonus_cap():
    async def go():
        db = await _fresh_db()
        await db.tasks_config.insert_one({"key": "quest_limits", "daily_bonus_cap_city": 25})
        await quests.build_overview("u1", "ru")
        r1 = await quests.claim("u1", "ob_open_business", "ru")      # 20
        await quests.quest_event("u1", "market_list", 1)
        r2 = await quests.claim("u1", "ob_first_list", "ru")      # 15 -> capped to 5
        assert r1["granted"]["city"] == 20
        assert r2["granted"]["city"] == 5 and r2["granted"]["capped"] is True
    run(go())


def test_sales_between_linked_accounts_do_not_count():
    async def go():
        db = await _fresh_db(uid="seller")
        await db.users.insert_one({"id": "twin", "email": "t@x.io"})
        await db.users.insert_one({"id": "stranger", "email": "s@x.io"})
        await db.fingerprints.insert_many([
            {"user_id": "seller", "visitor_id": "dev-1"},
            {"user_id": "twin", "visitor_id": "dev-1"},
            {"user_id": "stranger", "visitor_id": "dev-2"},
        ])
        await quests.sale_event("seller", "twin", 5)
        doc = await db.user_quests.find_one({"user_id": "seller", "quest_id": "ob_first_sale"})
        assert doc is None
        await quests.sale_event("seller", "stranger", 5)
        doc = await db.user_quests.find_one({"user_id": "seller", "quest_id": "ob_first_sale"})
        assert doc["status"] == "ready"
    run(go())


def test_onboarding_groups_and_final_reward(monkeypatch):
    async def go():
        db = await _fresh_db()
        monkeypatch.setenv("ONBOARDING_MODE", "quests")
        assert await quests.onboarding_group(db, await db.users.find_one({"id": "u1"})) == "quests"
        # an old player who already finished the tutorial stays "legacy"
        await db.users.insert_one({"id": "old", "tutorial_completed": True})
        assert await quests.onboarding_group(db, await db.users.find_one({"id": "old"})) == "legacy"
        # the group is sticky even if the mode changes
        monkeypatch.setenv("ONBOARDING_MODE", "tutorial")
        assert await quests.onboarding_group(db, await db.users.find_one({"id": "u1"})) == "quests"

        with pytest.raises(HTTPException):
            await quests.grant_onboarding_reward("u1", "neuro_core")    # chain not finished
        for ev in ("shift_start", "market_list", "market_buy", "repair", "upgrade"):
            await quests.quest_event("u1", ev, 1)
        await quests.sale_event("u1", None, 1)
        await db.tasks_config.insert_one({"key": "quest_limits", "daily_bonus_cap_city": 10000})
        ov = await quests.build_overview("u1", "ru")
        for x in ov["onboarding"]["items"]:
            await quests.claim("u1", x["id"], "ru")
        with pytest.raises(HTTPException):
            await quests.grant_onboarding_reward("u1", "not_a_resource")
        r = await quests.grant_onboarding_reward("u1", "gold_bill")
        assert r["reward"] == "gold_bill"
        with pytest.raises(HTTPException) as e:
            await quests.grant_onboarding_reward("u1", "gold_bill")
        assert e.value.status_code == 409
        u = await db.users.find_one({"id": "u1"})
        # the player owns a business → the bonus is switched on at once (the free unit is used for it)
        assert r["activated"] is True and u["tutorial_t3_reward_granted"] is True
        assert u["resources"]["gold_bill_tutorial"] == 0 and "tutorial_pending_t3_auto_activate" not in u
        assert [b["resource_id"] for b in u["active_resource_buffs"]] == ["gold_bill"]
    run(go())


def test_onboarding_reward_http_body_is_json():
    """POST /api/quests/onboarding/reward {"choice": …} — the body must be read as JSON (it used to be a 422)."""
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    async def prep():
        db = await _fresh_db(with_business=False)
        return db
    db = run(prep())
    app = FastAPI()
    app.include_router(quests.create_quests_router(db, lambda: SimpleNamespace(id="u1", language="ru"), lambda: None))
    c = TestClient(app)
    r = c.post("/api/quests/onboarding/reward", json={"choice": "neuro_core"})
    assert r.status_code == 400, r.text                    # «finish the path first» — not a validation error
    assert isinstance(r.json()["detail"], str)


def test_has_daily_done_unlocks_daily_reward():
    async def go():
        await _fresh_db()
        assert await quests.has_daily_done("u1") is False
        ids = await quests.ensure_assignment("u1", "daily")
        tpls = {t["id"]: t for t in await quests.get_templates()}
        easy = next(i for i in ids if tpls[i]["difficulty"] == "easy")
        await quests.quest_event("u1", tpls[easy]["event"], tpls[easy]["target"])
        assert await quests.has_daily_done("u1") is True
    run(go())


# ───────────────────────── translations (LibreTranslate) ─────────────────────────
def _fake_lt(monkeypatch, fail_langs=()):
    import translation_service
    calls = []

    async def fake(text, target, source="en"):
        calls.append((target, text))
        if target in fail_langs:
            raise ValueError("placeholder lost in translation")
        return f"[{target}] {text}"
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt.test")
    monkeypatch.setattr(translation_service, "translate_libre_protected", fake)
    return calls


def test_quest_texts_translated_and_saved(monkeypatch):
    async def go():
        db = await _fresh_db()
        calls = _fake_lt(monkeypatch)
        st = await quests.translate_templates(["id"])
        assert st["translated"] > 0 and st["failed"] == 0
        t = await db.quest_templates.find_one({"id": "ob_first_sale"})
        assert t["title"]["id"] == "[id] Sell a resource"
        assert t["i18n_auto"]["title"]["id"] is True
        assert t["title"]["ru"] == "Продайте ресурс"            # hand-written untouched
        n = len(calls)
        await quests.translate_templates(["id"])               # saved -> no new calls
        assert len(calls) == n
        ov = await quests.build_overview("u1", "id")
        assert ov["onboarding"]["items"][0]["title"].startswith("[id] ")
    run(go())


def test_failed_translation_is_not_saved(monkeypatch):
    async def go():
        db = await _fresh_db()
        _fake_lt(monkeypatch, fail_langs=("ja",))
        st = await quests.translate_templates(["ja"])
        assert st["translated"] == 0 and st["failed"] > 0
        t = await db.quest_templates.find_one({"id": "ob_first_sale"})
        assert "ja" not in t["title"]
        ov = await quests.build_overview("u1", "ja")          # falls back to English
        assert ov["onboarding"]["items"][0]["title"] == "Open your first business"
    run(go())


def test_manual_text_wins_and_en_change_retranslates(monkeypatch):
    async def go():
        db = await _fresh_db()
        _fake_lt(monkeypatch)
        await quests.translate_templates(["id", "es"])
        # admin writes Indonesian by hand -> machine never overwrites it
        await db.quest_templates.update_one({"id": "ob_first_sale"},
                                            {"$set": {"title.id": "Jual sumber daya"},
                                             "$unset": {"i18n_auto.title.id": ""}})
        await quests.translate_templates(["id"], force=True)
        t = await db.quest_templates.find_one({"id": "ob_first_sale"})
        assert t["title"]["id"] == "Jual sumber daya"
        # force re-makes machine translations only
        assert t["title"]["es"].startswith("[es] ")
    run(go())


def test_without_libretranslate_nothing_breaks(monkeypatch):
    async def go():
        await _fresh_db()
        monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
        st = await quests.translate_templates(["id"])
        assert st["translated"] == 0 and st["errors"]
        ov = await quests.build_overview("u1", "id")
        assert ov["onboarding"]["items"][0]["title"] == "Open your first business"
        assert await quests.msg("not_ready", "ru") == "Задание ещё не выполнено"
        assert await quests.msg("not_ready", "id") == "Quest is not completed yet"
    run(go())


def test_daily_reward_needs_no_trading_only_a_daily_goal(monkeypatch):
    """The old gate (buy 30 + sell 95) is gone: a finished daily goal unlocks it."""
    async def go():
        await _fresh_db()
        assert await quests.has_daily_done("u1") is False
        ids = await quests.ensure_assignment("u1", "daily")
        tpls = {t["id"]: t for t in await quests.get_templates()}
        easy = next(i for i in ids if tpls[i]["difficulty"] == "easy")
        await quests.quest_event("u1", tpls[easy]["event"], tpls[easy]["target"])
        assert await quests.has_daily_done("u1") is True     # no buy/sell needed
    run(go())


def test_collect_quests_retired_and_replaced():
    """Production is auto-collected, so 'collect' quests are switched off."""
    async def go():
        db = await _fresh_db()
        # an old database that still has the retired templates active
        await db.quest_templates.insert_one({"id": "ob_first_collect", "kind": "onboarding", "order": 3,
                                             "event": "collect", "target": 1, "active": True,
                                             "title": {"en": "Collect"}, "description": {"en": "x"}})
        await db.quest_templates.insert_one({"id": "d_collect", "kind": "daily", "difficulty": "easy",
                                             "event": "collect", "target": 1, "active": True, "requires_business": True,
                                             "title": {"en": "Collect"}, "description": {"en": "x"}})
        # today's assignment was made before the change and contains d_collect
        await db.quest_assignments.insert_one({"user_id": "u1", "kind": "daily",
                                               "period_key": quests.period_key("daily"),
                                               "quest_ids": ["d_collect", "d_sell20", "d_list_lot"]})
        ov = await quests.build_overview("u1", "ru")
        ob_ids = [x["id"] for x in ov["onboarding"]["items"]]
        assert "ob_first_collect" not in ob_ids and "ob_first_list" in ob_ids
        assert ob_ids.index("ob_first_buy") < ob_ids.index("ob_first_list") < ob_ids.index("ob_first_sale")
        daily_ids = [x["id"] for x in ov["daily"]["items"]]
        assert "d_collect" not in daily_ids and len(daily_ids) == 3          # swapped, still 3 goals
        tpls = {t["id"]: t for t in await quests.get_templates()}
        assert all(tpls[i]["event"] != "collect" for i in daily_ids)
    run(go())


def test_admin_marks_onboarding_completed():
    async def go():
        db = await _fresh_db(with_business=False)
        st = await quests.admin_onboarding_state("u1")
        assert st["completed"] is False and st["done"] == 0 and st["total"] >= 1
        st = await quests.admin_complete_onboarding("u1", reward_received=False)
        assert st["completed"] is True and st["done"] == st["total"] and st["reward_received"] is False
        # the player sees the path done and can pick the free tier-3 resource
        ov = await quests.build_overview("u1", "ru")
        assert ov["onboarding"]["completed"] is True and ov["onboarding"]["reward"]["available"] is True
        u = await db.users.find_one({"id": "u1"})
        assert not any(k.endswith("_tutorial") for k in (u.get("resources") or {}))      # nothing credited
        # «and the reward is already given»: no choice window
        st = await quests.admin_complete_onboarding("u1", reward_received=True)
        assert st["reward_received"] is True
        ov = await quests.build_overview("u1", "ru")
        assert ov["onboarding"]["reward"]["available"] is False
    run(go())


def test_overview_survives_a_failing_translation_and_sync(monkeypatch):
    """LibreTranslate down / a sync error must not hide «Путь новичка», «Сегодня» and «Неделя» together."""
    async def go():
        await _fresh_db(with_business=True)

        async def boom(*a, **k):
            raise RuntimeError("LibreTranslate 502")
        monkeypatch.setattr(quests, "ensure_lang", boom)
        monkeypatch.setattr(quests, "sync_state", boom)
        ov = await quests.build_overview("u1", "de")
        assert ov["onboarding"]["total"] >= 1 and len(ov["daily"]["items"]) >= 1
    run(go())


def test_business_found_under_any_identifier_and_daily_gate():
    async def go():
        db = await _fresh_db(with_business=False)
        assert await quests._has_business("u1") is False
        # no business → the market daily goals: the daily-login reward waits for one of them
        assert await quests.daily_gate_open("u1") is False
        # a business recorded under the player's Telegram id / an old `owner_id` still counts
        await db.users.update_one({"id": "u1"}, {"$set": {"telegram_id": "5550001"}})
        await db.businesses.insert_one({"id": "bt", "owner": "5550001", "business_type": "farm", "level": 1})
        assert await quests._has_business("u1") is True
        await db.businesses.delete_one({"id": "bt"})
        await db.businesses.insert_one({"id": "bo", "owner_id": "u1", "business_type": "farm", "level": 1})
        assert await quests._has_business("u1") is True
        # a tutorial business does not count
        await db.businesses.delete_one({"id": "bo"})
        await db.businesses.insert_one({"id": "btut", "owner": "u1", "tutorial": True})
        assert await quests._has_business("u1") is False
        # with a business there ARE daily goals → one has to be finished
        await db.businesses.insert_one({"id": "b2", "owner": "u1", "business_type": "farm", "level": 1})
        assert await quests.daily_gate_open("u1") is False
        ov = await quests.build_overview("u1", "ru")
        assert ov["has_business"] is True and len(ov["daily"]["items"]) >= 1
    run(go())


def test_daily_goals_always_there_even_without_a_business():
    async def go():
        db = await _fresh_db(with_business=False)
        ov = await quests.build_overview("u1", "ru")
        ids = [x["id"] for x in ov["daily"]["items"]]
        assert len(ids) == 3 and all(i in ("d_buy1", "d_sell20", "d_buy20", "d_list_lot", "d_sell50") for i in ids), ids
        assert ov["weekly"]["items"] == []                       # weekly goals still need a business
        # a day that was handed out the retired Arcade goals is repaired with real ones of the same difficulty
        await db.quest_assignments.update_one({"user_id": "u1", "kind": "daily"},
                                              {"$set": {"quest_ids": ["d_arcade1", "d_arcade3", "d_arcade5"]}})
        quests._tpl_cache["items"] = []
        ov = await quests.build_overview("u1", "ru")
        ids = [x["id"] for x in ov["daily"]["items"]]
        assert len(ids) == 3 and not any(i.startswith("d_arcade") for i in ids), ids
    run(go())


def test_admin_edits_daily_goals(monkeypatch):
    """Админка → Задания → Ежедневные цели: target / rewards / who gets it / new goals / how many per day."""
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    db = run(_fresh_db(with_business=False))
    monkeypatch.setattr(quests, "_lt_configured", lambda: False)
    app = FastAPI()
    app.include_router(quests.create_quests_router(db, lambda: SimpleNamespace(id="u1", language="ru"), lambda: True))
    c = TestClient(app)
    # sell 20 → sell 35: the number in every text follows
    r = c.put("/api/admin/quests/templates/d_sell20", json={"target": 35, "reward_city": 12})
    assert r.status_code == 200, r.text
    t = next(x for x in c.get("/api/admin/quests/templates").json()["templates"] if x["id"] == "d_sell20")
    assert t["target"] == 35 and t["reward_city"] == 12
    assert t["title"]["ru"] == "Продайте 35 единиц" and t["title"]["en"] == "Sell 35 units"
    # the admin decides who gets a goal — and a restart (re-seeding) keeps it
    c.put("/api/admin/quests/templates/d_repair", json={"requires_business": False})
    quests._seeded = False
    quests._tpl_cache["items"] = []
    t = next(x for x in c.get("/api/admin/quests/templates").json()["templates"] if x["id"] == "d_repair")
    assert t["requires_business"] is False
    # a new goal
    r = c.post("/api/admin/quests/templates", json={"kind": "daily", "difficulty": "easy", "event": "market_buy", "target": 5,
                                                    "reward_city": 7, "title": {"ru": "Купите 5 единиц", "en": "Buy 5 units"}})
    assert r.status_code == 200, r.text
    new_id = r.json()["template"]["id"]
    assert r.json()["template"]["requires_business"] is False and r.json()["template"]["deep_link"] == "/trading"
    # how many goals per day: 2 easy + 0 medium + 1 good
    assert c.put("/api/admin/quests/settings", json={"daily_per_difficulty": {"easy": 2, "medium": 0, "good": 1}}).status_code == 200
    ids = run(quests.ensure_assignment("u1", "daily"))
    tm = {x["id"]: x for x in run(quests.get_templates(force=True))}
    assert len(ids) == 3 and sorted(tm[i]["difficulty"] for i in ids) == ["easy", "easy", "good"]
    # built-in goals cannot be deleted, new ones can
    assert c.delete("/api/admin/quests/templates/d_buy1").status_code == 400
    assert c.delete(f"/api/admin/quests/templates/{new_id}").status_code == 200
    assert c.get("/api/admin/quests/meta").json()["daily_per_difficulty"] == {"easy": 2, "medium": 0, "good": 1}
