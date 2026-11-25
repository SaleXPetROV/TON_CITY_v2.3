"""GitBook ⇄ «Справочник» and GitBook AI in the support — no network: the GitBook API is faked."""
import asyncio
import os
import re

import mongomock_motor
import pytest

import routes.wiki as W
import wiki_gitbook as G

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "documentation")
FIX = os.path.join(HERE, "fixtures", "gitbook")


def run(c):
    return asyncio.run(c)


@pytest.fixture(autouse=True)
def _no_translator(monkeypatch):
    monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
    W._GB_SECTIONS.clear()
    W._SECTION_ORDER.clear()
    W._CACHE["at"] = 0
    yield
    W._GB_SECTIONS.clear()
    W._SECTION_ORDER.clear()


_FILES = None


def files():
    global _FILES
    if _FILES is None:
        _FILES = G.render_docs(G.seed_docs(), run(G.default_vars()))
    return _FILES


def test_render_is_exactly_the_documentation_folder():
    """The sync takes «unchanged» from git blob ids — the files must be byte for byte what is in documentation/."""
    f = files()
    on_disk = {os.path.relpath(os.path.join(r, n), DOC) for r, _, ns in os.walk(DOC) for n in ns if n.endswith(".md")}
    assert set(f) == on_disk
    for rel, text in f.items():
        with open(os.path.join(DOC, rel), encoding="utf-8") as fh:
            assert fh.read() == text, rel


def test_gitbook_markdown_means_the_same_as_ours():
    """GitBook gives the page back in its own markdown (* bullets, padded tables, *** rules, /pages/ links)."""
    links = {d["slug"]: d["slug"] for d in G.seed_docs()}
    links.update({"jo9jvZORklMjadlqLBwO": "first-days", "Anwd9HNPlQgfarVAliSi": "upgrade"})
    for name, path in (("glossary", "rules/glossary.md"), ("quick-start", "start/quick-start.md"),
                       ("t3-buffs", "warehouse/t3-buffs.md")):
        with open(os.path.join(FIX, name + ".md"), encoding="utf-8") as fh:
            gb = G.to_markup(fh.read(), links)
        assert G.same(gb, G.to_markup(files()[path], links)), name
    t3 = G.to_markup(open(os.path.join(FIX, "t3-buffs.md"), encoding="utf-8").read(), links)
    assert t3["t"] == "Бафы ресурсов эшелона 3" and t3["s"].startswith("Что даёт")
    assert "[[first-days|план на 3 дня]]" in t3["b"] and "| Ресурс | Что даёт | Срок |" in t3["b"]
    assert "Цифры в статье" not in t3["b"]


def test_markup_of_gitbook_blocks():
    md = ("---\ndescription: Короткое описание\n---\n\n# Заголовок\n\n## Раздел\n\nТекст с *курсивом* и "
          "[ссылкой](https://ton.org) и `кодом`.\n\n{% hint style=\"warning\" %}\nОсторожно!\n{% endhint %}\n\n"
          "<figure><img src=\"https://files.gitbook.com/a.png\" alt=\"Карта\"><figcaption></figcaption></figure>\n\n"
          "1. Раз\n2. Два\n")
    m = G.to_markup(md)
    assert m["t"] == "Заголовок" and m["s"] == "Короткое описание"
    assert m["b"].split("\n") == ["# Раздел", "", "Текст с курсивом и [ссылкой](https://ton.org) и кодом.", "",
                                  "> Осторожно!", "", "![Карта](https://files.gitbook.com/a.png)", "", "1. Раз", "1. Два"]


def test_emoji_codes():
    assert G.emoji("1f680") == "🚀"
    assert G.emoji("2696") == "⚖️"
    assert G.emoji("📦") == "📦"
    assert G.emoji(None) == ""


# ───────────────────────── the sync, against a fake GitBook ─────────────────────────

def _tree(edited=None, drop=(), extra=None, rename=None):
    """The page tree GitBook would give for documentation/ (+ changes)."""
    f = files()
    secs = []
    for line in f["SUMMARY.md"].split("\n"):
        m = re.match(r"^\* \[(.+?)\]\((\w+)/README\.md\)$", line)
        if m:
            icon, title = m.group(1).split(" ", 1)
            secs.append({"id": f"p-{m.group(2)}", "title": (rename or {}).get(m.group(2), title),
                         "emoji": "%x" % ord(icon[0]), "slug": m.group(2), "type": "document",
                         "git": {"oid": G.git_oid(f[f"{m.group(2)}/README.md"]), "path": f"documentation/{m.group(2)}/README.md"},
                         "pages": []})
            continue
        m = re.match(r"^  \* \[(.+?)\]\((\w+)/([\w-]+)\.md\)$", line)
        if m and m.group(3) not in drop:
            rel = f"{m.group(2)}/{m.group(3)}.md"
            oid = G.git_oid(f[rel]) if m.group(3) not in (edited or {}) else "edited-oid"
            secs[-1]["pages"].append({"id": f"p-{m.group(3)}", "title": m.group(1).split(" ", 1)[1], "slug": m.group(3),
                                      "type": "document", "git": {"oid": oid, "path": f"documentation/{rel}"},
                                      "updatedAt": "t1", "pages": []})
    if extra:
        secs[-1]["pages"].append(extra)
    intro = {"id": "p-intro", "title": "Справочник игрока", "slug": "spravochnik-igroka", "type": "document",
             "git": {"oid": G.git_oid(f["README.md"]), "path": "documentation/README.md"}, "pages": []}
    return [intro] + secs


def _fake(rev, tree, mds):
    calls = []

    async def fetch(path, params=None):
        calls.append(path)
        if path == "/orgs":
            return {"items": [{"id": "org"}]}
        if path.endswith("/sites"):
            return {"items": [{"id": "site"}]}
        if path.endswith("/site-spaces"):
            return {"items": [{"default": True, "space": {"id": "space"}}]}
        if path == "/spaces/space":
            return {"id": "space", "revision": rev}
        if path == "/spaces/space/content":
            return {"pages": tree}
        m = re.match(r"^/spaces/space/content/page/p-([\w-]+)$", path)
        if m:
            return {"markdown": mds[m.group(1)]}
        raise AssertionError(path)
    fetch.calls = calls
    return fetch


EDITED = """# Город на рынке

Что и когда выкупает Город.

Городской рынок сразу покупает лоты по своей цене или дешевле.

* Ограничивают его только «Выкуп в сутки» и запас Города.
* Подробнее — [Налоги](/pages/p-taxes).

***

_Цифры в статье — значения по умолчанию; в игре всегда показываются текущие._
"""

NEW = """# Как пройти ивент

Новая статья, написанная в GitBook.

| Шаг | Награда |
| --- | ------- |
| 1   | 100     |
"""


def test_sync_takes_gitbook_and_keeps_the_code_where_nothing_changed():
    db = mongomock_motor.AsyncMongoMockClient()["gb"]
    run(W.seed(db))
    tree = _tree(edited={"city-market"}, drop=("blackout",), rename={"rules": "Правила"},
                 extra={"id": "p-event-howto", "title": "Как пройти ивент", "slug": "event-howto", "emoji": "1f3c6",
                        "type": "document", "git": {"oid": "x", "path": "documentation/rules/event-howto.md"},
                        "updatedAt": "t1", "pages": []})
    fetch = _fake("rev1", tree, {"city-market": EDITED, "event-howto": NEW})
    res = run(G.sync(db, fetch=fetch))
    assert res["ok"] and res["from_gitbook"] == 2 and res["new"] == 1 and res["hidden"] == 1, res
    # only the changed pages were downloaded
    assert sorted(p for p in fetch.calls if "/content/page/" in p) == ["/spaces/space/content/page/p-city-market",
                                                                      "/spaces/space/content/page/p-event-howto"]
    cm = run(db.wiki_articles.find_one({"slug": "city-market"}, {"_id": 0}))
    assert cm["origin"] == "gitbook" and cm["published"] is True
    assert cm["i18n"]["ru"]["b"].startswith("Городской рынок сразу покупает")
    assert "[[taxes|Налоги]]" in cm["i18n"]["ru"]["b"]
    assert cm["i18n"]["en"]["t"]                       # the old translation stays until LibreTranslate makes a new one
    taxes = run(db.wiki_articles.find_one({"slug": "taxes"}, {"_id": 0}))
    assert taxes["origin"] == "seed" and re.search(r"\{\{|\[\[table:", taxes["i18n"]["ru"]["b"])  # live numbers kept
    assert taxes["gitbook_page"] == "p-taxes"
    ev = run(db.wiki_articles.find_one({"slug": "event-howto"}, {"_id": 0}))
    assert ev["section"] == "rules" and ev["icon"] == "🏆" and "| 1 | 100 |" in ev["i18n"]["ru"]["b"]
    assert run(db.wiki_articles.find_one({"slug": "blackout"}))["published"] is False
    # the wiki shows GitBook's sections: «Правила» renamed, «События» (now empty) left out of the index
    secs = W._sections()
    assert next(s for s in secs if s["id"] == "rules")["t"]["ru"] == "Правила"
    docs = run(W._all(db))
    assert "blackout" not in {d["slug"] for d in docs} and "event-howto" in {d["slug"] for d in docs}
    # the same revision again → nothing is read
    fetch2 = _fake("rev1", tree, {})
    assert run(G.sync(db, fetch=fetch2))["skipped"] == "same revision"
    # the page is put back as it was in the code → the code's article again (live numbers, translations)
    fetch3 = _fake("rev2", _tree(), {})
    res3 = run(G.sync(db, fetch=fetch3))
    assert res3["ok"] and res3["from_gitbook"] == 0 and res3["shown"] == 1, res3
    cm = run(db.wiki_articles.find_one({"slug": "city-market"}, {"_id": 0}))
    assert cm["origin"] == "seed" and cm["i18n"]["ru"]["b"] == next(
        d for d in G.seed_docs() if d["slug"] == "city-market")["i18n"]["ru"]["b"]
    assert run(db.wiki_articles.find_one({"slug": "blackout"}))["published"] is True
    assert run(db.wiki_versions.count_documents({"slug": "city-market"})) == 2


def test_sync_is_off_by_switch_and_safe_on_an_empty_space():
    db = mongomock_motor.AsyncMongoMockClient()["gb2"]
    run(W.seed(db))
    run(G.save_settings(db, {"wiki_sync": False}))
    assert run(G.sync(db, fetch=_fake("r", [], {})))["skipped"] == "off"
    run(G.save_settings(db, {"wiki_sync": True}))
    res = run(G.sync(db, fetch=_fake("r", [], {})))
    assert res["ok"] and res["hidden"] == 0          # an empty space never hides the whole wiki
    assert run(db.wiki_articles.count_documents({"published": False})) == 0


# ───────────────────────── GitBook AI in the support ─────────────────────────

def test_ask_reads_the_stream_and_spots_no_answer():
    db = mongomock_motor.AsyncMongoMockClient()["gb3"]

    async def post_ok(path, body):
        assert path.endswith("/ask") and body["question"] == "Как вывести GRAM?" and body["scope"] == {"mode": "default"}
        part = {"type": "answer", "answer": {"answer": {"markdown": "Вывод"}, "sources": [], "followupQuestions": []}}
        full = {"type": "answer", "answer": {"answer": {"markdown": "**Вывод**: Деньги → «Вывести».\n\n* от 1 GRAM"},
                                             "sources": [{"type": "page", "page": "p-withdraw", "title": "Вывод"}],
                                             "followupQuestions": ["А комиссия?"]}}
        return [part, full]

    r = run(G.ask(db, "Как вывести GRAM?", "ru", post=post_ok))
    assert r["ok"] and r["sources"] == [{"page": "p-withdraw", "title": "Вывод"}]
    assert G.plain(r["answer"]) == "Вывод: Деньги → «Вывести».\n\n• от 1 GRAM"

    async def post_none(path, body):
        return [{"type": "answer", "answer": {"answer": {"markdown": "Я не нашёл ответа в документации."}, "sources": [],
                                              "followupQuestions": []}}]
    assert run(G.ask(db, "Погода?", "ru", post=post_none)) == {"ok": False, "none": True,
                                                                "answer": "Я не нашёл ответа в документации."}

    async def post_empty(path, body):
        return []
    assert run(G.ask(db, "?", "ru", post=post_empty))["none"] is True


def _support_db():
    from willy import core as C
    db = mongomock_motor.AsyncMongoMockClient()["gb4"]
    C.init(db)
    chat = {"id": "c1", "user_id": "u1", "status": "bot", "user_username": "neo"}
    run(db.support_chats.insert_one(dict(chat)))
    run(db.wiki_articles.insert_one({"slug": "withdraw", "icon": "⬆️", "gitbook_page": "p-withdraw", "published": True,
                                     "i18n": {"ru": {"t": "Вывод"}, "en": {"t": "Withdraw"}}}))
    return C, db, chat


def test_support_answer_from_gitbook():
    C, db, chat = _support_db()

    async def ask(db_, q, lang):
        return {"ok": True, "answer": "**Вывод** — от 1 GRAM.", "sources": [{"page": "p-withdraw", "title": "Вывод"}]}
    assert run(C.gitbook_answer(db, chat, {"language": "ru"}, "как вывести", "как вывести", "ru", ask=ask)) is True
    m = run(db.support_messages.find_one({"chat_id": "c1", "sender_type": "bot"}, {"_id": 0}))
    assert m["content"] == "Вывод — от 1 GRAM."
    assert m["willy"]["kind"] == "answer" and m["willy"]["engine"] == "gitbook"
    assert m["willy"]["buttons"] == [{"kind": "wiki", "slug": "withdraw", "icon": "⬆️", "title": "Вывод"}]
    assert run(db.support_chats.find_one({"id": "c1"}))["status"] == "bot"


def test_support_cant_answer_offers_a_person():
    C, db, chat = _support_db()

    async def ask(db_, q, lang):
        return {"ok": False, "none": True}
    assert run(C.gitbook_answer(db, chat, {"language": "ru"}, "как создать свою игру", "как создать свою игру", "ru", ask=ask))
    c = run(db.support_chats.find_one({"id": "c1"}))
    assert c["status"] == "bot" and c["willy_offer"] is True
    m = run(db.support_messages.find_one({"chat_id": "c1", "sender_type": "bot"}, {"_id": 0}))
    assert m["willy"]["kind"] == "offer" and m["content"].startswith("На этот вопрос я ответить не могу")
    # the player takes the offer → a person
    run(C.call_human(db, chat, {"language": "ru"}))
    c = run(db.support_chats.find_one({"id": "c1"}))
    assert c["status"] == "new" and c["handoff_reason"] == "no_answer"
    assert run(db.support_messages.find_one({"id": m["id"]}))["willy"]["taken"] is True


def test_no_person_without_an_offer():
    C, db, chat = _support_db()
    assert run(C.call_human(db, chat, {"language": "ru"})) == []
    assert run(db.support_chats.find_one({"id": "c1"}))["status"] == "bot"


def test_hedged_ai_answer_counts_as_no_answer():
    db = mongomock_motor.AsyncMongoMockClient()["gb7"]
    for md in ("Если вы имеете в виду бизнес в GRAM City: откройте Карту. Документация не описывает создание отдельной игры.",
               "Доступная документация описывает только GRAM City, поэтому информации о вашей игре в ней нет.",
               "NO_ANSWER"):
        async def post(path, body, md=md):
            assert "NO_ANSWER" in body["context"]["goal"]
            return [{"type": "answer", "answer": {"answer": {"markdown": md},
                                                  "sources": [{"type": "page", "page": "p", "title": "t"}]}}]
        assert run(G.ask(db, "как создать свою игру", "ru", post=post))["none"] is True, md


def test_support_not_helped_twice_calls_a_person():
    C, db, chat = _support_db()

    async def ask(db_, q, lang):
        return {"ok": True, "answer": "Ответ", "sources": [{"page": "p-withdraw", "title": "Вывод"}]}
    for i in (1, 2):
        run(C.gitbook_answer(db, chat, {"language": "ru"}, f"вопрос {i}", f"вопрос {i}", "ru", ask=ask))
        m = run(db.support_messages.find({"chat_id": "c1", "sender_type": "bot", "willy.kind": "answer"}, {"_id": 0})
                .sort("created_at", -1).to_list(1))[0]
        run(C.feedback(db, chat, {"language": "ru"}, m["id"], False))
        c = run(db.support_chats.find_one({"id": "c1"}))
        assert c["status"] == ("bot" if i == 1 else "new"), i


def test_rules_no_longer_hand_over_at_once():
    from willy import core as C
    db = mongomock_motor.AsyncMongoMockClient()["gb5"]
    C.init(db)
    assert run(C.settings(db))["rules_handoff"] is False


def test_support_gitbook_down_leaves_it_to_willy():
    C, db, chat = _support_db()

    async def ask(db_, q, lang):
        raise G.GitBookError("GitBook 503")
    assert run(C.gitbook_answer(db, chat, {"language": "ru"}, "вопрос", "вопрос", "ru", ask=ask)) is False
    assert run(db.support_chats.find_one({"id": "c1"}))["status"] == "bot"
    assert run(db.support_messages.count_documents({"chat_id": "c1"})) == 0


def test_willy_answers_in_the_language_of_the_message():
    from willy import core as C
    assert C.reply_lang({"language": "ru"}, "How to earn money?") == "en"            # the message's language wins
    assert C.reply_lang({"language": "en"}, "Где мой вывод?") == "ru"
    assert C.reply_lang({"language": "de"}, "¿Cómo gano dinero?") == "es"
    assert C.reply_lang({"language": "fr"}, "Як заробити гроші?") == "fr"           # not a project language → account
    assert C.reply_lang({"language": "ko"}, "Como ganhar dinheiro?") == "ko"
    assert C.reply_lang({"language": "ja"}, "GRAM") == "ja"                          # can't tell → account
    assert C.reply_lang({}, "GRAM") == "en"


def test_ai_answer_in_another_language_is_translated(monkeypatch):
    from willy import core as C
    db = mongomock_motor.AsyncMongoMockClient()["gb6"]
    seen = {}

    async def fake_tr(db_, text, target, source="ru", ttl_min=0):
        seen.update(target=target, source=source)
        return "Withdrawals start at 1 GRAM."
    monkeypatch.setattr(C, "tr", fake_tr)
    assert run(C.in_lang(db, "Вывод — от 1 GRAM, в разделе Деньги.", "en")) == "Withdrawals start at 1 GRAM."
    assert seen == {"target": "en", "source": "ru"}
    assert run(C.in_lang(db, "Withdrawals start at 1 GRAM in the Money section.", "en")) == "Withdrawals start at 1 GRAM in the Money section."
    assert run(C.in_lang(db, "Withdrawals start at 1 GRAM.", "en")) == "Withdrawals start at 1 GRAM."
