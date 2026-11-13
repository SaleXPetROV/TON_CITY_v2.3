"""Willy GRAM: search, rules, seed, rendering — no network, no database server (in-memory fakes)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from willy.index import Index  # noqa: E402
from willy.rules import check, looks_like_seed  # noqa: E402
from willy.seed import all_seed  # noqa: E402
from willy.text import content, is_russian, stems  # noqa: E402
from willy.phrases import P  # noqa: E402

LANGS = ["ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"]


def _idx():
    rows = []
    for i, a in enumerate(all_seed()):
        rows.append({"id": a["key"], "title": a["title"], "phrasings": a["phrasings"], "text": a["text"],
                     "agent_only": a.get("agent_only"), "prio": a.get("prio", 1)})
    return Index(rows)


def test_seed_is_sane():
    rows = all_seed()
    keys = [a["key"] for a in rows]
    assert len(keys) == len(set(keys)), "duplicate answer keys"
    assert len(rows) >= 3000
    for a in rows:
        assert a["title"] and a["text"] and len(a["phrasings"]) >= 4, a["key"]
        assert len(a["text"]) <= 420, a["key"]


def test_seed_vars_are_known():
    import re
    from willy.player import PLAYER_VARS
    game = {"tax_t1", "tax_t2", "tax_t3", "plot_resale", "ref_pct", "spoil_in", "spoil_over", "spoil_time", "spoil_on",
            "act_days", "act_buy", "act_sell", "lease_days", "t1_lot", "lot_hours", "shift_hours", "zero_mult",
            "repair_t1", "repair_t2", "repair_t3", "credit_rate", "credit_back", "credit_max", "credit_days",
            "bank_rate_max", "credit_deduct", "withdraw_fee", "withdraw_min", "instant_fee_max", "rent_fee",
            "rent_max_days", "alliance_level", "alliance_cost", "pass_levels", "daily_first", "daily_last",
            "daily_days", "guide_steps", "city_per_gram"}
    for a in all_seed():
        for v in re.findall(r"\{(\w+)\}", a["text"]):
            assert v in PLAYER_VARS or v in game, (a["key"], v)


def test_search_finds_the_right_answer():
    idx = _idx()
    cases = {
        "куда пропали мои ресурсы со склада?": "spoil",
        "как вывести деньги на тонкипер": "withdraw",
        "что даёт нейро-ядро": "t3:neuro_core",
        "где взять кварц": "res:quartz",
        "выбрал нейро ядро а его нет на складе": "t3_reward",
        "сколько можно выставить лотов": "lot_slots",
        "как запустить смену": "shift_how",
        "где моя реф ссылка": "refs",
        "спасибо большое": "thanks",
        "можно ли передать ресурсы другу": "transfer",
        "сколько стоит улучшить солнечную станцию до 5 уровня": "upg:helios:5",
        "сколько производит казино на 3 уровне": "prod:casino:3",
        "что значит ошибка этот баф уже активен": "err:" ,
        "что дают на 10 уровне city pass": "pass:10",
        "по чем город покупает энергию": "rcityprice:energy",
    }
    for q, key in cases.items():
        top = idx.search(q, 3)
        assert top and (top[0][0] == key or (key.endswith(":") and top[0][0].startswith(key))), (q, top[:2])


def test_operator_answers_hidden_from_players():
    idx = _idx()
    q = "вывод не пришел"
    assert all(not k.startswith("op_") for k, _ in idx.search(q, 6))
    assert any(k.startswith("op_") for k, _ in idx.search(q, 6, agent=True))


def test_rules():
    s = {}
    assert check(["позовите человека"], s) == "human"
    assert check(["не пришло пополнение 5 TON"], s) == "money"
    assert check(["My withdrawal is stuck"], s) == "money"
    assert check(["как пополнить баланс"], s) is None            # a how-to question is answered by Willy
    assert check(["как пополнить баланс"], {"rules": {"money": {"strict": True}}}) == "money"
    assert check(["мой бизнес изъяли"], s) == "seizure"
    assert check(["что такое изъятие"], s) is None
    assert check(["у меня взломали аккаунт"], s) == "hack"
    assert check(["сколько человек в альянсе"], s) is None
    assert check(["позовите человека"], {"rules": {"human": {"enabled": False}}}) is None
    assert check(["хочу вернуть бабки"], {"rules": {"money": {"words": ["бабки"]}}}) == "money"


def test_seed_phrase_detection():
    assert looks_like_seed("abandon ability able about above absent absorb abstract absurd abuse access accident")
    assert not looks_like_seed("how do i sell biomass on the market please help me now")


def test_text_helpers():
    assert content("привет, как продать товар") == "как продать товар"
    assert content("привет") == "привет"
    assert is_russian("как дела") and not is_russian("how are you")
    assert stems("бизнесы") == stems("бизнес")


def test_phrases_have_all_languages():
    for k, d in P.items():
        for lg in LANGS:
            assert d.get(lg), (k, lg)


def test_player_words_have_all_languages():
    from willy.player import WORDS
    for k, d in WORDS.items():
        for lg in LANGS:
            assert d.get(lg), (k, lg)


def test_eta_from_agent_hours(monkeypatch):
    from datetime import datetime, timezone
    import willy.core as W

    class Cur:
        def __init__(self, rows): self.rows = rows
        async def to_list(self, n): return self.rows

    class Col:
        def __init__(self, rows): self.rows = rows
        def find(self, *a, **k): return Cur(self.rows)

    class DB:
        support_agents = Col([{"hours": {"days": [0, 1, 2, 3, 4, 5, 6], "from": "10:00", "to": "11:00", "tz": "Europe/Moscow"}}])

    W._hooks.pop("ws_manager", None)
    monkeypatch.setattr(W, "_now", lambda: datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc))   # 23:00 МСК
    out = asyncio.run(W._eta(DB(), "ru"))
    assert "завтра" in out and "10:00" in out
    monkeypatch.setattr(W, "_now", lambda: datetime(2026, 11, 13, 4, 0, tzinfo=timezone.utc))    # 07:00 МСК
    assert "сегодня" in asyncio.run(W._eta(DB(), "ru"))
