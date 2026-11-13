"""Russian text helpers for Willy GRAM: normalisation, stems, character trigrams.

The answer base is Russian only. A player's question is translated to Russian first, then
compared with the Russian phrasings by stems (word level) and by character trigrams (catches
typos and word forms the stemmer misses)."""
import re
from functools import lru_cache
from typing import List

try:
    import snowballstemmer as _sb
    _STEM = _sb.stemmer("russian")
    _STEM_EN = _sb.stemmer("english")
except Exception:  # pragma: no cover — the package is in requirements.txt
    _STEM = _STEM_EN = None

_WORD = re.compile(r"[a-zа-я0-9$]+", re.I)

# Words that carry no meaning for the search («как», «почему»… are kept: they tell the kind of question,
# but they are so common that IDF makes them weightless anyway).
STOP = set("""
а и в во на но да же ли бы ни то это этот эта эти тот та те так там тут вот уже еще ещё
я мы ты вы он она оно они мне меня мой моя мое моё мои нам нас наш ваш вам вас его ее её их им
у к с со о об от до по за из про для при над под без через же ведь ну ой ах
был была было были будет быть есть
пожалуйста подскажите подскажи скажите скажи
ребят ребята можно ли
the a an is are to of in on and or my me i you it do does how what why
""".split())

# Same-meaning words the players use: every key is replaced by its value before stemming.
SYN = {
    "ресы": "ресурсы", "рес": "ресурс", "ресурсов": "ресурсы",
    "бизы": "бизнесы", "биз": "бизнес", "бизнеса": "бизнес", "предприятие": "бизнес", "здание": "бизнес",
    "завод": "бизнес", "фабрика": "бизнес",
    "баланс": "счет", "счёт": "счет", "кошель": "кошелек", "кошелёк": "кошелек", "вывод": "вывести",
    "вывода": "вывести", "выводить": "вывести", "вывожу": "вывести", "снять": "вывести",
    "пополнить": "пополнение", "пополняю": "пополнение", "закинуть": "пополнение", "задонатить": "пополнение",
    "депозит": "пополнение", "деп": "пополнение",
    "тон": "gram", "ton": "gram", "грам": "gram", "грамы": "gram",
    "сити": "city", "$city": "city", "монеты": "city", "монет": "city",
    "склад": "склад", "хранилище": "склад", "инвентарь": "склад",
    "сгнило": "испортилось", "сгнил": "испортился", "пропало": "исчезло", "пропал": "исчез",
    "пропали": "исчезли", "делось": "исчезло", "делся": "исчез", "делись": "исчезли",
    "апгрейд": "улучшение", "апнуть": "улучшить", "прокачать": "улучшить", "прокачка": "улучшение",
    "лвл": "уровень", "левел": "уровень", "уровня": "уровень", "ур": "уровень",
    "бафф": "баф", "баффы": "бафы", "буст": "баф", "бусты": "бафы", "бустануть": "баф",
    "рефка": "реферальная", "рефы": "рефералы", "реф": "реферал", "рефералка": "реферальная",
    "тендер": "тендер", "контракт": "контракт", "лот": "лот", "лоты": "лоты",
    "2фа": "2fa", "двухфакторка": "2fa", "двухфакторная": "2fa", "аутентификатор": "2fa", "гугл": "2fa",
    "смену": "смена", "смены": "смена", "запуск": "запустить",
    "прочка": "прочность", "износ": "прочность", "сломался": "прочность", "ремонтировать": "ремонт",
    "почини": "ремонт", "починить": "ремонт",
}


def norm(text: str) -> str:
    t = (text or "").lower().replace("ё", "е")
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=200000)
def _stem(w: str) -> str:
    if _STEM is None:
        return w[:6] if len(w) > 6 else w
    if re.match(r"^[a-z]+$", w):
        return _STEM_EN.stemWord(w)
    return _STEM.stemWord(w)


def words(text: str) -> List[str]:
    out = []
    for w in _WORD.findall(norm(text)):
        w = SYN.get(w, w)
        for part in w.split():
            if part in STOP or (len(part) < 2 and not part.isdigit()):
                continue
            out.append(part)
    return out


GREET = set("привет здравствуйте здравствуй добрый доброе день вечер утро алло спасибо благодарю помогите помоги "
             "большое огромное ок окей понял поняла понятно ясно отлично супер класс "
             "hello hi hey thanks thank ok".split())


def content(text: str) -> str:
    """Drop greetings and thanks when the message has a real question besides them."""
    ws = words(text)
    if any(w not in GREET for w in ws):
        ws = [w for w in ws if w not in GREET]
    return " ".join(ws)


def stems(text: str) -> List[str]:
    return [_stem(w) for w in words(text)]


def trigrams(text: str) -> List[str]:
    out = []
    for w in words(text):
        w = f" {w} "
        out.extend(w[i:i + 3] for i in range(len(w) - 2))
    return out


def is_russian(text: str) -> bool:
    letters = re.findall(r"[a-zа-яё]", (text or "").lower())
    if not letters:
        return True
    cyr = sum(1 for c in letters if "а" <= c <= "я" or c == "ё")
    return cyr / len(letters) >= 0.5
