"""Willy GRAM's answers built from the game itself (so they always match the code).

Numbers that the game config defines are not written into the texts: a text holds a live token like
{cfg:prod:helios:3} that Willy fills at the moment of answering (willy/core.py, _cfg). So a change of the config, a
City Pass reward or a daily reward changes every answer at once, in every language.

What is built here:
  • every business × every level: production, raw materials, warehouse, the upgrade to that level, the whole way
    up to that level, what the level changes;
  • every business: price and keeping the level-0 one, finding it, buying, selling, renting, «not producing»,
    repair, who buys its goods, where to get its raw materials, its role in the chains;
  • every resource: tax, warehouse weight, minimum lot, the City, price, buying, selling, spoilage, tenders,
    contracts, «how much do I have»;
  • every tier-3 buff, booster, patron buff; every business level; every City Pass level, every XP source,
    every day of the daily reward; the player's own numbers; every article and every line of the Справочник;
    every message the game shows on an error (willy/answers_errors.py); the glossary; the languages.
"""
import re
from typing import Any, Dict, List

TIER_WORD = {1: "первого", 2: "второго", 3: "третьего"}


def _lv(n: int) -> List[str]:
    return [f"{n} уровень", f"уровень {n}", f"ур {n}", f"{n} лвл", f"{n} уровне", f"{n}-й уровень"]


def _names(code: str) -> List[str]:
    from business_config import BUSINESSES
    from wiki_content.effects import BIZ
    out = []
    for n in [(BIZ.get(code) or {}).get("ru"), ((BUSINESSES.get(code) or {}).get("name") or {}).get("ru"),
              (BIZ.get(code) or {}).get("en")]:
        if n and n not in out:
            out.append(n)
    return out


def _rn(r: str) -> str:
    from wiki_content.effects import RES
    from business_config import RESOURCE_TYPES
    return (RES.get(r) or {}).get("ru") or (RESOURCE_TYPES.get(r) or {}).get("name_ru") or r


def _a(out, key, topic, title, wiki, text, q, route=None, checks=None, agent_only=False):
    seen, ph = set(), []
    for x in q:
        x = re.sub(r"\s+", " ", x).strip()
        if x and x.lower() not in seen:
            seen.add(x.lower())
            ph.append(x)
    out.append({"key": key, "topic": topic, "title": title, "wiki": wiki, "text": text, "phrasings": ph,
                "checks": checks or [], "route": route, "handoff": False, "agent_only": agent_only, "prio": 0})


def businesses(out: List[Dict[str, Any]]) -> None:
    from business_config import BUSINESSES, UPGRADE_COSTS_TABLE
    for code, b in BUSINESSES.items():
        names = _names(code)
        nm = names[0]
        icon = b.get("icon", "🏭")
        tier = int(b.get("tier") or 1)
        prod = _rn(b.get("produces"))
        raws = [_rn(r) for r in (b.get("consumes") or {})]
        up_res = (UPGRADE_COSTS_TABLE.get(code, {}).get(2) or {}).get("resource")
        for lvl in range(1, 11):
            lq = _lv(lvl)
            _a(out, f"prod:{code}:{lvl}", "business", f"{nm}, ур. {lvl}: сколько производит", "shift",
               f"{icon} {nm} на ур. {lvl} производит {{cfg:prod:{code}:{lvl}}} ед. «{prod}» в сутки (≈ {{cfg:prodh:{code}:{lvl}}} в час) — "
               f"когда идёт смена и хватает сырья. Ниже 50% прочности — 80% от этого.",
               [f"сколько производит {n} на {l}" for n in names for l in lq[:3]]
               + [f"производство {nm} {lvl} уровень", f"{nm} {lvl} уровень сколько {prod} в сутки", f"сколько {prod} дает {nm} ур {lvl}",
                  f"доход {nm} на {lvl} уровне", f"сколько в час производит {nm} {lvl} уровня"])
            if raws:
                _a(out, f"cons:{code}:{lvl}", "business", f"{nm}, ур. {lvl}: сколько сырья тратит", "raw-materials",
                   f"{icon} {nm} на ур. {lvl} тратит в сутки: {{cfg:cons:{code}:{lvl}}}. Сырьё тратится только во время смены. "
                   f"Купите его в Торговле → «Купить» или заключите тендер.",
                   [f"сколько сырья тратит {n} на {l}" for n in names for l in lq[:3]]
                   + [f"сколько {r} нужно {nm} {lvl} уровня" for r in raws]
                   + [f"потребление {nm} ур {lvl}", f"чем кормить {nm} на {lvl} уровне", f"расход {nm} {lvl} лвл"])
            _a(out, f"prodshift:{code}:{lvl}", "business", f"{nm}, ур. {lvl}: товар за смену", "shift",
               f"{icon} За одну смену ({{shift_hours}} ч) {nm} на ур. {lvl} даёт ≈ {{cfg:prodshift:{code}:{lvl}}} ед. «{prod}» — если хватает "
               f"сырья и прочность от 50%. Запускайте следующую смену сразу или включите «Автозапуск смен».",
               [f"сколько дает {n} за смену на {l}" for n in names for l in lq[:2]]
               + [f"{nm} {lvl} уровень за смену", f"сколько {prod} за 8 часов {nm} ур {lvl}", f"выработка за смену {nm} {lvl} лвл",
                  f"сколько получу за смену {nm} {lvl}"])
            if raws:
                _a(out, f"consshift:{code}:{lvl}", "business", f"{nm}, ур. {lvl}: сырьё на смену", "raw-materials",
                   f"{icon} На одну смену ({{shift_hours}} ч) {nm} ур. {lvl} тратит ≈ {{cfg:consshift:{code}:{lvl}}}. Держите столько на складе "
                   f"перед запуском — иначе бизнес даст меньше товара.",
                   [f"сколько сырья на смену {n} {l}" for n in names for l in lq[:2]]
                   + [f"сколько {r} на одну смену {nm} ур {lvl}" for r in raws]
                   + [f"сколько нужно сырья на 8 часов {nm} {lvl} уровень", f"запас сырья на смену {nm} {lvl} лвл"])
            _a(out, f"store:{code}:{lvl}", "warehouse", f"{nm}, ур. {lvl}: склад", "capacity",
               f"{icon} {nm} на ур. {lvl} добавляет {{cfg:store:{code}:{lvl}}} мест склада. Вместимость склада — сумма складов всех "
               f"ваших бизнесов. Ресурс эшелона 1 занимает 1 место, 2 — 5, 3 — 20.",
               [f"какой склад у {n} на {l}" for n in names for l in lq[:3]]
               + [f"вместимость {nm} {lvl} уровень", f"сколько влезет на склад {nm} ур {lvl}", f"склад {nm} {lvl} лвл",
                  f"сколько мест дает {nm} на {lvl} уровне"])
            if lvl >= 2 and (UPGRADE_COSTS_TABLE.get(code, {}).get(lvl)):
                res_l = _rn((UPGRADE_COSTS_TABLE[code][lvl] or {}).get("resource") or up_res or "")
                _a(out, f"upg:{code}:{lvl}", "business", f"{nm}: улучшение до ур. {lvl}", "upgrade",
                   f"{icon} {nm}: улучшение с ур. {lvl - 1} до ур. {lvl} стоит {{cfg:upg:{code}:{lvl}}}. Наградный ресурс тоже "
                   f"подходит. Сейчас у вас «{res_l}»: {{cfg:have:{(UPGRADE_COSTS_TABLE[code][lvl] or {}).get('resource')}}}.",
                   [f"сколько стоит улучшить {n} до {l}" for n in names for l in lq[:3]]
                   + [f"апгрейд {nm} на {lvl} уровень", f"цена улучшения {nm} {lvl}", f"сколько {res_l} нужно для {lvl} уровня {nm}",
                      f"что нужно для {lvl} уровня {nm}", f"прокачать {nm} с {lvl - 1} до {lvl}", f"сколько city на апгрейд {nm} {lvl} лвл"])
                _a(out, f"upgsum:{code}:{lvl}", "business", f"{nm}: всего до ур. {lvl}", "upgrade",
                   f"{icon} {nm}: путь с ур. 1 до ур. {lvl} стоит всего {{cfg:upgsum:{code}:{lvl}}} — без цены выкупа ур. 1. "
                   f"Улучшать можно по одному уровню.",
                   [f"сколько всего стоит прокачать {n} до {l}" for n in names for l in lq[:2]]
                   + [f"сколько нужно чтобы прокачать {nm} с 1 до {lvl}", f"общая стоимость {nm} до {lvl} уровня",
                      f"сколько {res_l} всего на {lvl} уровень {nm}", f"сумма улучшений {nm} до {lvl}"])
                _a(out, f"lvlgain:{code}:{lvl}", "business", f"{nm}: что даёт ур. {lvl}", "upgrade",
                   f"{icon} {nm} на ур. {lvl}: {{cfg:prod:{code}:{lvl}}} ед. в сутки вместо {{cfg:prod:{code}:{lvl - 1}}}, склад "
                   f"{{cfg:store:{code}:{lvl}}} вместо {{cfg:store:{code}:{lvl - 1}}}"
                   + (f", сырья {{cfg:cons:{code}:{lvl}}} в сутки" if raws else "") + ".",
                   [f"что даст {lvl} уровень {n}" for n in names]
                   + [f"зачем улучшать {nm} до {lvl}", f"стоит ли качать {nm} на {lvl} уровень", f"разница {nm} {lvl - 1} и {lvl} уровень",
                      f"что изменится на {lvl} уровне {nm}", f"выгода от {lvl} уровня {nm}"])
        # one per business
        _a(out, f"bizprice0:{code}", "land", f"{nm}: выкуп бизнеса 0 уровня", "zero-business",
           f"{icon} {nm}, ур. 0: бизнес останется у вас навсегда после улучшения до ур. 1. Цена — цена этого места на карте "
           f"(видна в карточке), только с основного счёта. У вас на основном: {{balance_main}} $CITY. До конца аренды: {{zero_left}}.",
           [f"сколько стоит выкупить {n}" for n in names] + [f"{nm} 0 уровня выкуп", f"сделать {nm} своим", f"улучшить {nm} до 1 уровня",
                                                            f"сколько стоит 1 уровень {nm}"], checks=["main_balance"])
        if up_res:
            _a(out, f"bizupres:{code}", "business", f"{nm}: каким ресурсом улучшать", "upgrade",
               f"{icon} {nm}: для улучшения до ур. 2 и выше нужен ресурс эшелона 3 «{_rn(up_res)}» (наградный тоже подходит). У вас сейчас: "
               f"{{cfg:have:{up_res}}}. Сколько штук на каждый уровень — на кнопке «Апгрейд».",
               [f"какой ресурс нужен для улучшения {n}" for n in names] + [f"чем улучшать {nm}", f"{nm} апгрейд ресурс", f"{_rn(up_res)} для {nm}",
                                                                          f"что нужно для апгрейда {nm}"])
        _a(out, f"bizraw:{code}", "business", f"{nm}: где взять сырьё", "raw-materials",
           (f"{icon} {nm} тратит: {', '.join(raws)}. " if raws else f"{icon} {nm} сырья не тратит. ")
           + (" ".join(f"{r} производит: {', '.join(_names(c)[0] for c, x in BUSINESSES.items() if _rn(x.get('produces')) == r) or '—'}."
                       for r in raws))
           + (" Купите на рынке или заключите тендер — сырьё будет приходить каждый день." if raws else ""),
           [f"где взять сырье для {n}" for n in names] + [f"что нужно {nm} для работы", f"чем кормить {nm}", f"откуда брать сырье {nm}",
                                                          f"{nm} не хватает сырья", f"какое сырье нужно {nm}"])
        buyers = [_names(c)[0] for c, x in BUSINESSES.items() if b.get("produces") in (x.get("consumes") or {})]
        _a(out, f"bizsell:{code}", "trade", f"{nm}: кому продавать товар", "sell",
           f"{icon} {nm} производит «{prod}». "
           + (f"Это сырьё для: {', '.join(buyers)} — их владельцы и покупают. " if buyers else "")
           + ("Ресурсы эшелона 1 покупает и Город (по цене не выше своей). " if tier == 1 else "Город этот товар не покупает — только игроки. ")
           + f"Налог с продажи — {{tax_t{tier}}}%.",
           [f"кому продавать {prod}", f"кому продать товар {nm}", f"кто покупает {prod}", f"куда девать {prod}", f"{nm} куда продавать",
            f"кому нужен {prod}"])
        _a(out, f"bizfix:{code}", "business", f"{nm} не производит", "shift",
           f"{icon} {nm} производит только во время смены (сейчас у вас: {{shift_state}}). Нужны сырьё ({', '.join(raws) or 'не нужно'}) "
           f"и прочность выше 0% (самая низкая у вас — {{worst_dur}}%). Запустите смену, купите сырьё или почините.",
           [f"{n} не производит" for n in names] + [f"почему {nm} не работает", f"{nm} стоит", f"{nm} ничего не дает", f"{nm} простаивает",
                                                    f"не идет производство {nm}"], checks=["shift_running", "durability_ok"])
        _a(out, f"bizrep:{code}", "business", f"{nm}: ремонт", "durability",
           f"{icon} {nm} — эшелон {tier}: ремонт стоит {{repair_t{tier}}} $CITY за каждый недостающий процент, проценты ниже 50% — вдвое. "
           f"Ниже 50% бизнес даёт 80% товара, при 0% — стоит.",
           [f"сколько стоит ремонт {n}" for n in names] + [f"как починить {nm}", f"прочность {nm}", f"{nm} сломался", f"ремонт {nm} цена",
                                                           f"износ {nm}"], checks=["durability_ok"])
        _a(out, f"bizbuy:{code}", "land", f"{nm}: как купить", "buy-business",
           f"{icon} {nm} — бизнес эшелона {tier}. "
           + ("Все бизнесы эшелона 3 уже стоят в зоне «Ядро» — купить можно у владельцев на Маркетплейсе. " if tier == 3 else
              "Найдите его на карте фильтром по типу и купите свободное место или купите у игрока на Маркетплейсе. ")
           + "Купленный бизнес — сразу ур. 1 и ваш навсегда.",
           [f"как купить {n}" for n in names] + [f"где купить {nm}", f"хочу {nm}", f"сколько стоит {nm}", f"цена {nm}", f"где найти {nm} на карте",
                                                 f"как найти {nm}"], route="/marketplace")
        _a(out, f"bizrent:{code}", "business", f"{nm}: аренда и продажа", "rental",
           f"{icon} {nm} 1 уровня и выше можно сдать в аренду (до {{rent_max_days}} дней, комиссия {{rent_fee}}%) или продать на "
           f"Маркетплейсе (налог {{tax_t{tier}}}%). Бизнес 0 уровня не сдаётся и не продаётся.",
           [f"как продать {n}" for n in names] + [f"сдать {nm} в аренду", f"арендовать {nm}", f"продажа {nm}", f"аренда {nm}"],
           checks=["biz_level1"])
        role = {1: "Эшелон 1 делает базовый ресурс: его покупают игроки как сырьё и Город.",
                2: "Эшелон 2 перерабатывает ресурсы эшелона 1 в товар для игроков.",
                3: "Эшелон 3 делает редкий ресурс: из него включают бафы и улучшают бизнесы; сам бизнес может быть покровителем."}[tier]
        _a(out, f"bizrole:{code}", "business", f"{nm}: место в цепочке", "chains",
           f"{icon} {nm}: {', '.join(raws) or 'без сырья'} → {prod}. {role}"
           + (f" Для улучшения до ур. 2+ нужен ресурс «{_rn(up_res)}»." if up_res else ""),
           [f"зачем нужен {n}" for n in names] + [f"{nm} цепочка", f"выгоден ли {nm}", f"стоит ли брать {nm}", f"{nm} какой эшелон",
                                                  f"что за бизнес {nm}"])
        if tier == 3:
            _a(out, f"bizpatron:{code}", "business", f"{nm}: стать покровителем", "patron-buffs",
               f"{icon} {nm} как бизнес эшелона 3 может быть покровителем: вы выбираете баф для подопечных и получаете 1% их дохода. "
               f"Опубликуйте предложение в разделе контрактов. До 25 подопечных.",
               [f"как сделать {nm} покровителем", f"{nm} патрон", f"покровитель {nm}", f"подопечные {nm}", f"бафы от {nm}"])


def resources(out: List[Dict[str, Any]]) -> None:
    from business_config import BUSINESSES, RESOURCE_TYPES
    for r, info in RESOURCE_TYPES.items():
        nm = _rn(r)
        tier = int(info.get("tier") or 1)
        w = {1: 1, 2: 5, 3: 20}.get(tier, 1)
        def add(kind, title, wiki, text, q, route=None, checks=None):
            _a(out, f"{kind}:{r}", "trade" if wiki in ("sell", "buy", "taxes", "tenders", "contracts", "analytics", "city-market") else "warehouse",
               f"{nm}: {title}", wiki, text, q, route, checks)
        add("rtax", "налог с продажи", "taxes", f"«{nm}» — ресурс эшелона {tier}: с продажи берётся {{tax_t{tier}}}% налога. Сумму «чистыми» видно до выставления лота.",
            [f"налог на {nm}", f"какой налог при продаже {nm}", f"комиссия {nm}", f"сколько заберут с продажи {nm}", f"{nm} налог процент"])
        add("rweight", "место на складе", "capacity", f"1 шт. «{nm}» занимает {w} мест{'о' if w == 1 else ''} склада (эшелон {tier}). Свободно у вас: {{wh_free}}.",
            [f"сколько места занимает {nm}", f"вес {nm}", f"{nm} сколько мест на складе", f"почему {nm} занимает много места"])
        add("rlot", "минимальный лот", "sell",
            (f"«{nm}» можно выставлять поштучно, от 1 шт.; цена за 1 шт. до сотых $CITY." if tier == 1 else f"«{nm}» можно выставлять поштучно, цена за 1 шт."),
            [f"минимальный лот {nm}", f"сколько минимум продать {nm}", f"можно ли продать 1 {nm}", f"поштучно {nm}"])
        add("rcity", "покупает ли Город", "city-market",
            (f"Да: «{nm}» — эшелон 1, Город покупает этот ресурс, но только по цене не выше своей и дешевле игроков." if tier == 1
             else f"Нет: Город покупает только ресурсы эшелона 1. «{nm}» покупают игроки."),
            [f"покупает ли город {nm}", f"продать {nm} городу", f"город берет {nm}", f"почему город не купил {nm}"])
        add("rprice", "цена", "analytics",
            f"Цена «{nm}» меняется: смотрите лоты в Торговле → «Купить» и графики в Аналитике (кнопка на экране «Бизнесы»).",
            [f"сколько стоит {nm}", f"цена {nm}", f"почем {nm}", f"курс {nm}", f"по какой цене продавать {nm}", f"график цены {nm}"])
        add("rsell", "как продать", "sell",
            f"Торговля → «Мои» → «Продать ресурс» → «{nm}», количество и цена → «Выставить». У вас сейчас: {{cfg:have:{r}}}."
            + (" Наградный ресурс продать нельзя." if tier == 3 else ""),
            [f"как продать {nm}", f"выставить {nm} на продажу", f"продажа {nm}", f"хочу продать {nm}", f"где продать {nm}"],
            route="/trading?tab=my")
        add("rbuy", "как купить", "buy",
            f"Торговля → «Купить» → фильтр «{nm}» → лот → количество. Оплата: сначала бонусный, потом основной счёт. Свободно на складе: {{wh_free}}.",
            [f"как купить {nm}", f"где купить {nm}", f"купить {nm}", f"нужен {nm} где взять", f"{nm} купить на рынке"], route="/trading")
        add("rspoil", "порча", "spoilage",
            f"Да, «{nm}» портится, как и всё на складе: в {{spoil_time}} МСК — {{spoil_in}}% (сверх вместимости — {{spoil_over}}%). Лоты на рынке не портятся.",
            [f"портится ли {nm}", f"{nm} пропадает", f"почему уменьшился {nm}", f"порча {nm}", f"куда делся {nm}"])
        add("rtender", "тендер", "tenders",
            f"Нужно «{nm}» каждый день — создайте тендер: Торговля → «Контракты» → «Закупки» → «Новый тендер». Есть «{nm}» на продажу — ищите заказы в «Бирже».",
            [f"тендер на {nm}", f"поставка {nm} каждый день", f"заказать {nm}", f"контракт на {nm}"], route="/trading")
        add("rhave", "сколько у меня", "resources", f"У вас на складе: {{cfg:have:{r}}} — «{nm}».",
            [f"сколько у меня {nm}", f"мой {nm}", f"сколько {nm} на складе", f"остаток {nm}"], route="/resources")
        add("rcityprice", "цены Города", "city-market",
            f"Городской рынок по «{nm}»: {{cfg:city:{r}}}. Город покупает дешевле и продаёт дороже игроков — с игроками выгоднее.",
            [f"по чем город покупает {nm}", f"цена города на {nm}", f"сколько город платит за {nm}", f"город продает {nm} цена"])
        add("rsys", "системная цена", "zero-business",
            f"Системная цена «{nm}» для лотов бизнеса 0 уровня — {{cfg:sys:{r}}} $CITY за 1 шт. Её нельзя менять, деньги идут на бонусный счёт.",
            [f"системная цена {nm}", f"почему цена {nm} не меняется", f"цена {nm} у бизнеса 0 уровня", f"фиксированная цена {nm}"])
        ups = [_names(c)[0] for c, lv in __import__('business_config').UPGRADE_COSTS_TABLE.items() if (lv.get(2) or {}).get("resource") == r]
        if ups:
            add("rupg", "для каких улучшений", "upgrade", f"«{nm}» нужен для улучшения до ур. 2 и выше: {', '.join(ups)}.",
                [f"для чего {nm} в улучшении", f"какие бизнесы улучшаются {nm}", f"куда потратить {nm}", f"{nm} для апгрейда"])
        makers = [_names(c)[0] for c, x in BUSINESSES.items() if x.get("produces") == r]
        users = [_names(c)[0] for c, x in BUSINESSES.items() if r in (x.get("consumes") or {})]
        add("rwho", "кто производит и кому нужен", "chains",
            f"«{nm}» производит: {', '.join(makers) or '—'}. " + (f"Это сырьё для: {', '.join(users)}." if users else "Как сырьё не используется."),
            [f"кто производит {nm}", f"какой бизнес делает {nm}", f"кому нужен {nm}", f"где используется {nm}", f"откуда {nm}"])


def buffs(out: List[Dict[str, Any]]) -> None:
    from wiki_content.effects import T3, BOOST, PATRON, RES
    try:
        from routes.buffs import RESOURCE_BUFFS
    except Exception:
        RESOURCE_BUFFS = {}
    for r, d in T3.items():
        nm = _rn(r)
        days = (RESOURCE_BUFFS.get(r) or {}).get("duration_days", 7)
        _a(out, f"t3days:{r}", "warehouse", f"{nm}: сколько действует баф", "t3-buffs",
           f"Баф «{nm}» ({d['ru']}) действует {days} дн. Сколько осталось — Склад → Усилители → «Сейчас действуют».",
           [f"сколько действует {nm}", f"на сколько дней {nm}", f"срок бафа {nm}", f"когда кончится {nm}"], route="/resources")
        _a(out, f"t3twice:{r}", "warehouse", f"{nm}: включить два раза", "t3-buffs",
           f"Один и тот же баф дважды не включается: дождитесь конца «{nm}». Одновременно — не больше двух бафов и усилителей.",
           [f"можно ли включить {nm} два раза", f"второй {nm}", f"продлить {nm}", f"два {nm} сразу"])
        _a(out, f"t3reward:{r}", "warehouse", f"{nm} из награды", "t3-buffs",
           f"«{nm}» из награды лежит на складе отдельно: продать нельзя, можно включить баф или потратить на улучшение. Сейчас у вас: {{t3_reward}}.",
           [f"{nm} из награды", f"наградный {nm}", f"не могу продать {nm}", f"где мой {nm} из награды"], route="/resources")
        _a(out, f"t3where:{r}", "warehouse", f"{nm}: где взять", "t3-buffs",
           f"«{nm}» производят бизнесы эшелона 3, его продают игроки (Торговля → «Купить»), он бывает наградой City Pass.",
           [f"где взять {nm} для бафа", f"как получить {nm}", f"{nm} бесплатно", f"{nm} в city pass"])
    icons = {"auto_shift": "🔁", "warehouse_guard": "🛡", "repair_all": "🔧", "xp_x2": "✨", "streak_shield": "🔰"}
    for k, x in BOOST.items():
        nm = x["n"]["ru"]
        _a(out, f"boostwhere:{k}", "warehouse", f"{nm}: где взять", "boosters",
           f"{icons.get(k, '⚡')} «{nm}» — награда City Pass (на бесплатной и премиум-дорожке). Продать и купить нельзя.",
           [f"где взять {nm}", f"как получить {nm}", f"купить {nm}", f"{nm} откуда"])
        _a(out, f"boostuse:{k}", "warehouse", f"{nm}: как включить", "boosters",
           f"{icons.get(k, '⚡')} Склад → Усилители → «{nm}» → «Активировать». Одновременно — не больше двух усилителей и бафов.",
           [f"как включить {nm}", f"как активировать {nm}", f"где {nm} на складе", f"не включается {nm}"], route="/resources")
    for k, x in PATRON.items():
        nm = x["n"]["ru"]
        _a(out, f"patronpick:{k}", "business", f"Баф «{nm}»: как получить", "patron-buffs",
           f"«{nm}» ({x['d']['ru']}) ваш бизнес получает от покровителя: выберите покровителя эшелона 3, который даёт этот баф, "
           f"и примите его предложение. Покровитель берёт 1% дохода.",
           [f"как получить баф {nm}", f"где взять {nm}", f"кто дает {nm}", f"{nm} покровитель"])


def levels(out: List[Dict[str, Any]]) -> None:
    for lvl in range(0, 11):
        if lvl == 0:
            t = "Ур. 0 — бесплатная аренда от Города на {lease_days} дня: цена товара системная, деньги на бонусный счёт. Улучшите до ур. 1 — и бизнес ваш навсегда."
        elif lvl == 1:
            t = "Ур. 1 — бизнес ваш навсегда, выручка идёт на основной счёт, можно продать, сдать в аренду и взять кредит. Ур. 0 → 1 стоит цену бизнеса на карте."
        else:
            t = (f"Ур. {lvl}: больше товара за смену и больше склад, но и больше сырья. Улучшение до ур. {lvl} стоит $CITY и ресурс эшелона 3 "
                 f"своего типа — точную цену видно на кнопке «Апгрейд».")
        _a(out, f"level:{lvl}", "business", f"Что даёт ур. {lvl}", "upgrade", t,
           [f"что дает {lvl} уровень", f"зачем {lvl} уровень", f"уровень {lvl} бизнеса", f"{lvl} лвл что дает", f"бизнес {lvl} уровня"])


def pass_and_rewards(out: List[Dict[str, Any]]) -> None:
    for n in range(1, 31):
        _a(out, f"pass:{n}", "rewards", f"City Pass, ур. {n}", "city-pass",
           f"City Pass, ур. {n}: {{cfg:pass:{n}}}. Нужно опыта: {{cfg:passxp:{n}}}. Ваш уровень: {{pass_level}}.",
           [f"что дают на {n} уровне city pass", f"награда {n} уровня пасса", f"city pass {n} уровень", f"сколько опыта до {n} уровня пасса",
            f"пасс {n} лвл награда"], route="/city-pass")
    xp = {"daily_goal": "цель дня", "weekly_goal": "цель недели", "shift_start": "запуск смены", "repair": "ремонт",
          "sale": "продажа игрокам", "streak_day": "день серии входов", "league_top": "место в лиге"}
    for k, l in xp.items():
        _a(out, f"xp:{k}", "rewards", f"Опыт City Pass: {l}", "city-pass",
           f"За «{l}» City Pass даёт {{cfg:xp:{k}}}. Опыт копится в течение сезона; уровни забирайте кнопкой «Забрать».",
           [f"сколько опыта за {l}", f"опыт за {l}", f"xp за {l}", f"как получить опыт {l}"], route="/city-pass")
    for d in range(1, 8):
        _a(out, f"daily:{d}", "rewards", f"Ежедневный вход, день {d}", "daily-login",
           f"На {d}-й день серии входов награда — {{cfg:daily:{d}}} $CITY на бонусный счёт. Забрать — после одной цели дня.",
           [f"награда за {d} день входа", f"{d} день серии", f"сколько дают на {d} день", f"ежедневная награда день {d}"], route="/tasks")
    for i, (d, nm) in enumerate([("bronze", "Бронза"), ("silver", "Серебро"), ("gold", "Золото"), ("platinum", "Платина"), ("diamond", "Алмаз")]):
        _a(out, f"league:{d}", "community", f"Лига «{nm}»", "leagues",
           f"«{nm}» — {i + 1}-я из 5 лиг. Каждую неделю лучшие поднимаются выше, худшие опускаются. Очки — за цели, смены, ремонты, "
           f"продажи игрокам и серию входов.",
           [f"как попасть в {nm}", f"лига {nm}", f"что дает {nm} лига", f"{nm} награды"], route="/community")


def player(out: List[Dict[str, Any]]) -> None:
    from .player import PLAYER_VARS
    q = {
        "balance_main": ["какой у меня основной баланс", "сколько на основном счете", "сколько я могу вывести"],
        "balance_bonus": ["сколько у меня бонусов", "бонусный баланс", "сколько на бонусном счете"],
        "balance_gram": ["сколько у меня gram", "баланс в gram", "сколько тон на балансе"],
        "frozen": ["сколько у меня заморожено", "замороженные деньги сколько", "сколько в эскроу"],
        "biz_count": ["сколько у меня бизнесов", "мои бизнесы количество"],
        "biz_name": ["какой у меня бизнес", "мой бизнес что это"],
        "biz_level": ["какой уровень у моего бизнеса", "мой уровень бизнеса"],
        "zero_left": ["сколько осталось аренды", "когда кончится аренда бизнеса", "сколько времени до конца аренды"],
        "zero_until": ["до какого числа аренда", "когда заберут бесплатный бизнес"],
        "shift_state": ["идет ли смена", "работает ли мой бизнес сейчас", "запущена ли смена"],
        "worst_dur": ["какая прочность у моего бизнеса", "сколько прочности", "нужен ли ремонт"],
        "wh_used": ["сколько занято на складе", "заполненность склада"],
        "wh_cap": ["какая вместимость моего склада", "какой у меня склад"],
        "wh_free": ["сколько свободно на складе", "сколько еще влезет на склад"],
        "top_res": ["чего у меня больше всего", "что у меня на складе"],
        "spoil_tonight": ["сколько испортится сегодня", "сколько сгниет сегодня", "сколько потеряю на порче"],
        "spoil_last": ["сколько испортилось вчера", "сколько сгнило в прошлый раз", "сколько я потерял на порче"],
        "lots": ["сколько у меня лотов", "мои лоты сколько"],
        "lot_slots": ["сколько лотов я могу выставить", "сколько слотов лотов"],
        "bought_10d": ["сколько я купил за 10 дней", "моя активность покупки"],
        "sold_10d": ["сколько я продал за 10 дней", "моя активность продажи"],
        "overdue": ["есть ли у меня просрочка", "просрочен ли кредит"],
        "pass_level": ["какой у меня уровень пасса", "мой уровень city pass"],
        "buffs_active": ["какие бафы у меня включены", "что сейчас действует", "активные бафы"],
        "t3_reward": ["есть ли у меня наградный ресурс", "мой ресурс из награды"],
        "ref_count": ["сколько у меня рефералов", "сколько друзей я пригласил"],
        "ref_link": ["дай мою реферальную ссылку", "скинь мою ссылку для приглашения"],
        "twofa": ["включена ли у меня 2fa", "есть ли у меня двухфакторка"],
        "wallet": ["подключен ли мой кошелек", "привязан ли кошелек"],
        "telegram": ["привязан ли телеграм", "подключен ли бот"],
        "user_id": ["какой у меня id", "мой id игрока", "где мой айди"],
        "name": ["какой у меня ник", "как меня зовут в игре"],
    }
    for k, lbl in PLAYER_VARS.items():
        if k not in q:
            continue
        _a(out, f"me:{k}", "start", f"Мои данные: {lbl.lower()}", None, f"{lbl}: {{{k}}}.", q[k] + [f"мой {lbl.lower()}", lbl.lower(), f"покажи {lbl.lower()}", f"узнать {lbl.lower()}"])


def wiki(out: List[Dict[str, Any]]) -> None:
    """Every article and every line of the Russian Справочник becomes an answer (numbers stay live: {{var}} → {var})."""
    from wiki_content.ru import A
    for slug, art in A.items():
        title = re.sub(r"\{\{(\w+)\}\}", r"{\1}", art["t"])
        summ = re.sub(r"\{\{(\w+)\}\}", r"{\1}", art.get("s") or "")
        _a(out, f"wiki:{slug}", "rules", f"Справочник: {title}", slug, f"{summ} Подробно — в статье «{title}».",
           [title, f"статья {title}", f"расскажи про {title}", f"что такое {title}", f"{title} как работает", summ])
        heading = title
        for i, raw in enumerate((art.get("b") or "").split("\n")):
            line = raw.strip()
            if not line or line.startswith("[[table:"):
                continue
            if line.startswith("# "):
                heading = line[2:].strip()
                continue
            kind = "note" if line.startswith(">") else "item"
            text = re.sub(r"^(>|-|\d+\.)\s*", "", line)
            if line.startswith("="):
                term, _, mean = text[1:].partition("|")
                term, mean = term.strip(), mean.strip()
                text = f"{term} — {mean}"
                q = [f"что такое {term}", f"что значит {term}", term, f"{term} это"]
                ttl = f"Словарик: {term}"
            else:
                short = " ".join(text.split()[:7])
                q = [text, f"{heading} {text}", f"{title}: {short}", f"{short}?", f"расскажи {short}"]
                ttl = f"{title}: {text[:60]}"
            text = re.sub(r"\[\[[\w-]+\|([^\]]+)\]\]", r"«\1»", text).replace("**", "")
            text = re.sub(r"\{\{(\w+)\}\}", r"{\1}", text)
            qq = [re.sub(r"\{\{?(\w+)\}?\}", "", re.sub(r"\[\[[\w-]+\|([^\]]+)\]\]", r"\1", x)).replace("**", "") for x in q]
            if len(text) < 12:
                continue
            _a(out, f"wl:{slug}:{i}", "rules", ttl, slug, text + ("" if kind == "note" else f" Подробно — «{title}»."), qq)


def errors(out: List[Dict[str, Any]]) -> None:
    from .answers_errors import E
    for i, (msg, why, wiki_slug) in enumerate(E):
        clean = msg.replace("…", "").strip()
        _a(out, f"err:{i}", "rules", f"Ошибка: {msg[:70]}", wiki_slug, f"«{msg}» — {why}",
           [clean, f"пишет {clean}", f"ошибка {clean}", f"что значит {clean}", f"выдает {clean}"])


def misc(out: List[Dict[str, Any]]) -> None:
    langs = {"ru": "русский", "en": "английский", "es": "испанский", "zh": "китайский", "fr": "французский", "de": "немецкий",
             "ja": "японский", "ko": "корейский", "id": "индонезийский"}
    for code, l in langs.items():
        _a(out, f"lang:{code}", "start", f"Игра на языке: {l}", "notifications",
           f"Да, игра есть на языке «{l}». Настройки → «Язык». В Telegram-боте — команда /language. Поддержка тоже отвечает на нём.",
           [f"есть ли {l} язык", f"как поставить {l}", f"игра на {l}", f"{l} язык", f"поддержка на {l}"], route="/settings")
    for t in (1, 2, 3):
        _a(out, f"tier:{t}", "business", f"Эшелон {t}", "tiers",
           f"Эшелон {t}: налог с продажи {{tax_t{t}}}%, ремонт {{repair_t{t}}} $CITY за %, 1 шт. занимает {({1: 1, 2: 5, 3: 20})[t]} мест склада."
           + (" Его ресурсы покупает и Город." if t == 1 else " Его товар покупают только игроки."),
           [f"эшелон {t}", f"бизнесы {TIER_WORD[t]} эшелона", f"ресурсы {TIER_WORD[t]} эшелона", f"t{t}", f"тир {t}", f"налог эшелон {t}"])
    from wiki_content.ui import CHECKS
    for cid, x in CHECKS.items():
        t = re.sub(r"\{(\w+)\}", "…", (x.get("ru") or {}).get("t") or cid)
        fail = (x.get("ru") or {}).get("fail") or ""
        fail = re.sub(r"\{(\w+)\}", "…", fail)
        _a(out, f"check:{cid}", "rules", f"Проверка «{t}» не пройдена", None,
           f"❌ «{t}»{': ' + fail if fail else ''}. Ниже — ваша проверка прямо сейчас и статья, как это исправить.",
           [f"почему крестик {t}", f"не выполнено {t}", f"{t} красный", f"как выполнить {t}"], checks=[cid])


NOTIF = [
    ("market_sold", "Ваш лот купили", "Ваш лот на рынке купили: деньги (минус налог) уже на счёте — основной или бонусный, если продавал бизнес 0 уровня.", "sell"),
    ("market_lot_returned", "Лот вернулся на склад", "Лот не продался за {lot_hours} ч и вернулся на склад. Выставьте снова, ближе к рыночной цене.", "sell"),
    ("market_tail_returned", "Остаток лота вернулся", "Часть лота продана, а остаток меньше минимального лота вернулся на склад.", "sell"),
    ("warehouse_spoilage", "Порча склада", "В {spoil_time} МСК часть товара испортилась: {spoil_in}% (сверх вместимости — {spoil_over}%). В прошлый раз у вас — {spoil_last} ед.", "spoilage"),
    ("deposit", "Пополнение", "Пополнение зачислено на основной счёт: 1 GRAM = {city_per_gram} $CITY.", "deposit"),
    ("withdrawal_pending", "Вывод на проверке", "Заявка на вывод принята и проходит проверку. Статус — в Истории операций.", "withdraw"),
    ("withdrawal_approved", "Вывод одобрен", "Вывод одобрен и отправлен на ваш кошелёк. Перевод в сети TON обычно идёт несколько минут.", "withdraw"),
    ("withdrawal_rejected", "Вывод отклонён", "Вывод отклонён, деньги вернулись на основной счёт. Причина — в уведомлении; если неясно — напишите «человек».", "withdraw"),
    ("zero_lease_expiring", "Аренда бизнеса заканчивается", "Скоро кончится бесплатная аренда (осталось {zero_left}). Улучшите бизнес до ур. 1, чтобы оставить его.", "zero-business"),
    ("zero_lease_expired", "Аренда закончилась", "{lease_days} дня аренды прошли без улучшения — бизнес вернулся Городу. Если у вас не было бизнеса 1 уровня, займите новый.", "zero-business"),
    ("zero_business_bought", "Ваш бизнес 0 уровня купили", "Другой игрок купил ваш бизнес 0 уровня по цене карты ×{zero_mult}. Можно занять новый бесплатный.", "zero-business"),
    ("business_seized", "Бизнес изъят", "Город изъял бизнес: за неактивность или долг по кредиту. Из суммы продажи сначала гасится долг, остаток — вам.", "seizure"),
    ("credit_overdue", "Просрочка по кредиту", "Нет выплат по кредиту {credit_days} дней — ставка удвоена. Любой платёж снимает просрочку; ещё {credit_days} дней — изъятие.", "credit"),
    ("business_build", "Бизнес построен", "Бизнес стоит на вашем месте. Запустите первую смену.", "shift"),
    ("land_purchase", "Покупка места", "Место на карте теперь ваше.", "plots"),
    ("city_pass_level", "Новый уровень City Pass", "Вы получили уровень City Pass — заберите награду кнопкой «Забрать».", "city-pass"),
    ("league_result", "Итоги лиги", "Неделя лиги закончилась: ваше место и награда — в «Общение» → «Лиги».", "leagues"),
    ("task", "Задание", "Цель выполнена — заберите награду в Заданиях.", "quests"),
    ("announcement", "Объявление", "Новость от GRAM CITY — полный текст в колокольчике 🔔.", "notifications"),
    ("alliance", "Альянс", "Событие вашего альянса: заявка, приглашение, казна или уровень.", "alliances"),
    ("patron_buff_update", "Баф покровителя изменён", "Покровитель вашего бизнеса выбрал другой баф — новый эффект уже действует.", "patron-buffs"),
    ("counter_offer", "Встречное предложение", "Игрок прислал встречное предложение по контракту — примите или отклоните его.", "contracts"),
    ("counter_offer_accepted", "Встречное предложение принято", "Ваше встречное предложение приняли — контракт начался.", "contracts"),
    ("counter_offer_rejected", "Встречное предложение отклонено", "Ваше встречное предложение отклонили. Можно предложить другие условия.", "contracts"),
    ("tender_proposal_new", "Новое предложение по тендеру", "Поставщик предложил поставку по вашему тендеру — примите или отклоните во вкладке «Закупки». Без ответа оно закроется через 72 ч.", "tenders"),
    ("tender_contract_accepted", "Договор по тендеру принят", "Покупатель принял ваше предложение — ресурс будет уходить каждый день сам.", "tenders"),
    ("tender_contract_rejected", "Предложение по тендеру отклонено", "Покупатель отклонил ваше предложение. Посмотрите другие заказы на «Бирже».", "tenders"),
    ("tender_pending_funds", "Не хватает денег по тендеру", "На поставку по тендеру не хватает денег. У вас 24 часа, чтобы пополнить счёт, — потом договор рвётся со штрафом.", "tenders"),
    ("tender_pending_resources", "Не хватает ресурса по тендеру", "На поставку не хватает ресурса на складе. У вас 24 часа, чтобы пополнить склад, — потом договор рвётся со штрафом.", "tenders"),
    ("tender_amendment_new", "Запрос на изменение договора", "Вторая сторона предлагает изменить количество или цену — примите или отклоните.", "tenders"),
    ("tender_amendment_accepted", "Изменение договора принято", "Новые условия договора действуют с этого момента.", "tenders"),
    ("tender_amendment_rejected", "Изменение договора отклонено", "Вторая сторона отклонила изменение — договор идёт на старых условиях.", "tenders"),
    ("tender_break_request", "Запрос на разрыв договора", "Вторая сторона просит разорвать договор по согласию — примите или отклоните.", "tenders"),
    ("tender_break_request_rejected", "Разрыв договора отклонён", "Вторая сторона не согласилась разорвать договор — он продолжается.", "tenders"),
    ("tender_break_mutual", "Договор разорван по согласию", "Договор закрыт по согласию сторон, без штрафа.", "tenders"),
    ("tender_break_received", "Договор разорван", "Вторая сторона разорвала договор в одностороннем порядке — штраф взят с неё.", "tenders"),
    ("tender_break_unilateral", "Договор разорван автоматически", "Договор разорван: за 24 часа не нашлось денег или ресурса. Взят штраф.", "tenders"),
    ("minigame_prize", "Приз игры", "Вы выиграли приз в мини-игре — он уже на счёте или на складе.", "faq"),
    ("system", "Системное сообщение", "Служебное сообщение GRAM CITY — текст в колокольчике 🔔.", "notifications"),
]
BOT = [
    ("/start", "Открывает бота: кнопка входа в игру, язык и меню."),
    ("/status", "Показывает ваш баланс и главное по аккаунту. То же — /balance."),
    ("/businesses", "Список ваших бизнесов: уровень, прочность, смена. То же — /biz."),
    ("/help", "Список команд бота и кнопка поддержки."),
    ("/link", "Привязать аккаунт игры к этому Telegram: так приходят уведомления и ответы поддержки."),
    ("/language", "Сменить язык бота."),
]


def notifications(out: List[Dict[str, Any]]) -> None:
    for k, t, x, w in NOTIF:
        _a(out, f"notif:{k}", "start", f"Уведомление: {t}", w, f"🔔 «{t}»: {x}",
           [f"пришло уведомление {t}", f"что значит уведомление {t}", f"уведомление {t.lower()}", f"пришло {t.lower()}",
            f"оповещение {t.lower()}"])
    for cmd, x in BOT:
        _a(out, f"bot:{cmd[1:]}", "start", f"Команда бота {cmd}", "notifications", f"{cmd} — {x}",
           [f"команда {cmd}", f"что делает {cmd}", f"{cmd} в боте", f"бот {cmd[1:]}"])


def all_generated() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in (businesses, resources, buffs, levels, pass_and_rewards, player, wiki, errors, misc, notifications):
        f(out)
    return out
