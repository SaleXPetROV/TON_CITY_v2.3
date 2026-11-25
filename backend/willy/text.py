"""Russian text helpers for Willy GRAM: normalisation, stems, character trigrams.

The answer base is Russian only. A player's question is translated to Russian first, then
compared with the Russian phrasings by stems (word level) and by character trigrams (catches
typos and word forms the stemmer misses)."""
import re
from functools import lru_cache
from typing import List, Optional

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


# ───────────── the language a message is written in (owner, 20 Nov: Willy answers in it) ─────────────

_PROJECT = {"ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"}
# small, common words: enough to tell the languages apart in a short chat message. Languages that are NOT in the
# project are here too — a message in them must not be taken for one of ours (then the account's language is used).
_WORDS = {
    "en": "the a an how what where when why who which is are am was were do does did can could would should i my me "
          "you your it its to of in on at for and or not no yes please help money get earn withdraw deposit buy sell "
          "with from this that there have has hi hello thanks thank ok okay game business want need tell much many",
    "es": "el la los las un una cómo como qué que dónde donde cuándo cuando por para mi mis yo tú tu es son está estoy "
          "no sí con de del y o dinero ganar gano puedo quiero ayuda hola gracias juego negocio retirar cuánto",
    "fr": "le la les un une des comment quoi où quand pourquoi je mon ma mes est sont avec pour de du et ou ne pas "
          "oui argent gagner puis peux veux aide bonjour merci jeu retirer combien",
    "de": "der die das ein eine wie was wo wann warum ich mein meine ist sind mit für von und oder nicht ja geld "
          "verdienen kann will hilfe hallo danke spiel auszahlen wieviel viel",
    "id": "yang dan di ke dari ini itu bagaimana apa dimana kapan kenapa mengapa saya aku kamu anda tidak ya dengan "
          "untuk uang cara bisa mau tolong halo terima kasih mendapatkan menarik berapa",
    "pt": "o os um uma como onde quando porque eu meu minha é são com para de do da e ou não sim dinheiro ganhar "
          "posso quero ajuda olá obrigado jogo sacar quanto você",
    "it": "il lo gli un una come dove quando perché io mio mia è sono con per di del e o non sì soldi guadagnare "
          "posso voglio aiuto ciao grazie gioco prelevare quanto",
    "pl": "jak co gdzie kiedy dlaczego ja mój moja jest są z dla i lub nie tak pieniądze zarobić mogę chcę pomoc "
          "cześć dziękuję gra wypłacić ile",
    "tr": "nasıl ne nerede neden ben benim bir ve ile için değil evet para kazanmak yardım merhaba teşekkür oyun",
    "nl": "de het een hoe wat waar wanneer waarom ik mijn is zijn met voor van en of niet ja geld verdienen kan wil "
          "hulp hallo bedankt spel",
    "vi": "làm sao thế nào tôi của là và không có tiền kiếm giúp chào cảm ơn",
}
_WSET = {lg: set(ws.split()) for lg, ws in _WORDS.items()}
_MARKS = [("es", r"[¿¡ñ]"), ("de", r"[ßäöü]"), ("fr", r"[çœêàù]"), ("pt", r"[ãõ]"), ("pl", r"[ąęłśźżńć]"),
          ("tr", r"[ğşı]"), ("vi", r"[ơưđạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]")]


def message_lang(text: str) -> Optional[str]:
    """The project language a message is written in, or None: too short to tell, or a language the project does not
    have (Ukrainian, Portuguese, Arabic…) — then Willy uses the language of the player's account."""
    t = (text or "").strip()
    if len(re.findall(r"\w", t)) < 2:
        return None
    if re.search(r"[Ѐ-ӿ]", t):
        if re.search(r"[іїєґўәғқңөұүһІЇЄҐЎ]", t):      # Ukrainian, Belarusian, Kazakh…
            return None
        return "ru"
    if re.search(r"[가-힣]", t):
        return "ko"
    if re.search(r"[぀-ヿ]", t):
        return "ja"
    if re.search(r"[一-鿿]", t):
        return "zh"
    if re.search(r"[֐-ࣿऀ-෿฀-໿Ͱ-ϿႠ-ჿ԰-֏]", t):
        return None                                       # Hebrew, Arabic, Indic, Thai, Greek, Georgian, Armenian
    low = t.lower()
    toks = re.findall(r"[^\W\d_]+", low)
    score = {lg: sum(1 for w in toks if w in ws) for lg, ws in _WSET.items()}
    for lg, rx in _MARKS:
        if re.search(rx, low):
            score[lg] = score.get(lg, 0) + 2
    best = sorted(score.items(), key=lambda kv: -kv[1])
    if best and best[0][1] > 0 and (len(best) == 1 or best[0][1] > best[1][1]):
        return best[0][0] if best[0][0] in _PROJECT else None
    try:                                                   # no clear sign: langdetect, when it is sure
        from langdetect import detect_langs, DetectorFactory
        DetectorFactory.seed = 0
        top = detect_langs(t)[0]
        if len(toks) >= 3 and top.prob >= 0.9:
            return top.lang if top.lang in _PROJECT else None
    except Exception:
        pass
    return None
