"""When Willy GRAM must not answer by himself and calls a human at once.

The rules look at the Russian translation of the question AND at the original text (a few words in the
other languages are listed too, so a bad translation cannot hide «I need a human» or «withdrawal missing»).
Every rule can be switched off in the admin (Поддержка → Willy GRAM → Правила); extra words per rule can be
added there too."""
import re
from typing import Any, Dict, List, Optional

from .text import norm

REASONS = {
    "money": "Деньги",
    "human": "Просит человека",
    "complaint": "Жалоба",
    "bug": "Ошибка в игре",
    "seizure": "Изъятие бизнеса",
    "hack": "Взлом / доступ",
    "dispute": "Спор с игроком",
    "no_answer": "Нет в базе",
    "by_answer": "Ответ требует человека",
    "not_helped": "«Не помогло» 2 раза",
    "offline": "Willy GRAM недоступен",
}

_MONEY_TOPIC = (r"(пополн|депозит|вывод|вывест|вывел|выв[её]л|снят|списа|заморо|заблокир|кредит|платеж|платёж|оплат|"
                r"транзакц|перевод|деньг|баланс|счет|gram|ton|city|"
                r"deposit|withdraw|payment|transaction|balance|retiro|depósito|retrait|dépôt|auszahlung|einzahlung|"
                r"提现|充值|出金|入金|출금|입금|penarikan|setoran)")
_MONEY_PROBLEM = (r"(не пришл|не пришел|не пришёл|не дошл|не зачисл|не поступ|не отображ|не вижу|не появ|пропал|исчез|"
                  r"завис|где мои|где деньги|верните|вернуть деньги|ошибочно|по ошибке|лишн|дважды|два раза|"
                  r"не могу вывести|не получается вывести|не выводит|отклон|отменил|списали|сняли|заморозили|"
                  r"заблокировали|не вернул|"
                  r"not (arrived|received|credited|showing)|missing|stuck|lost|never (came|arrived)|refund|"
                  r"no (llegó|llego)|pas reçu|nicht angekommen|没到|未到账|届かない|着金しない|안 들어|입금 안|belum masuk|tidak masuk)")
DEFAULT_PATTERNS: Dict[str, List[str]] = {
    "human": [r"позов\w* (человек|оператор|агент|админ|модератор|специалист|сотрудник)", r"живо\w* (человек|оператор)",
              r"нуж\w* (человек|оператор|агент|специалист)", r"свяжите|соедините", r"хочу (с |со )?(человек|оператор|агент)",
              r"\bоператор\w*\b", r"\bагент\w*\b", r"^\W*(человек|людей|люди|живой)\W*$",
              r"\b(human|operator|real person|live agent|talk to (a )?(person|human|someone))\b", r"\bhumano\b|persona real",
              r"\bopérateur\b|\bhumain\b", r"\bmensch\b|mitarbeiter", r"人工|客服|真人", r"オペレーター|担当者|人間",
              r"상담원|상담사|사람이랑|사람과", r"\bmanusia\b|\bcs\b|customer service"],
    "complaint": [r"жалоб", r"пожаловаться", r"претензи", r"недовол", r"обманул|обманыва|кинули|развод|мошенни", r"\bcomplain",
                  r"\bscam", r"\bqueja|\breclamación|\bplainte|\bbeschwerde|投诉|苦情|불만|keluhan|penipu"],
    "bug": [r"\bбаг\w*", r"глюк", r"вылета", r"завис(ает|ла|ло|ли)", r"белый экран|черный экран|чёрный экран", r"не грузит|не загружа",
            r"не открыва", r"ошибк\w* \d{3}", r"\bbug\b|\bglitch|\bcrash|\berror\b|\bfreez", r"错误|故障|バグ|버그"],
    "seizure": [r"изъял|изъят\w* (мой|мои|у меня)", r"(забрали|отобрали|отняли) (мой |мои |у меня )?(бизнес|здани|завод)",
                r"\bseiz", r"\bconfisc", r"没收|没収|압류|disita"],
    "hack": [r"взлом", r"украл|угнал", r"не я (вывел|выводил|заходил|входил|покупал|продал)", r"чуж\w* (вход|кошел|устройств)",
             r"потерял\w* доступ|нет доступа к (аккаунт|почт|телеграм)", r"смени(ли|л) (почт|пароль|кошел)", r"\bhack",
             r"\bstolen\b|\bcompromis", r"被盗|盗まれ|乗っ取|해킹|diretas"],
    "dispute": [r"спор с игрок", r"игрок\w* (обманул|не прислал|не отдал|не вернул|не заплатил)", r"не прислал ресурс",
                r"арбитраж", r"\bdispute\b"],
}

# 12/15/18/21/24 lowercase latin words in a row — looks like a wallet seed phrase.
_SEED = re.compile(r"(?:\b[a-z]{3,8}\b[\s,]+){11,23}\b[a-z]{3,8}\b")


def looks_like_seed(text: str) -> bool:
    t = (text or "").strip().lower()
    m = _SEED.search(t)
    if not m:
        return False
    n = len(re.findall(r"[a-z]{3,8}", m.group(0)))
    return n in (12, 15, 18, 21, 24) or n >= 12


def check(texts: List[str], settings: Dict[str, Any]) -> Optional[str]:
    """The reason to hand over to a human, or None. `texts` — the original question and its Russian translation."""
    rules = (settings or {}).get("rules") or {}
    joined = " \n ".join(norm(t) for t in texts if t)
    if not joined.strip():
        return None
    order = ["hack", "money", "seizure", "dispute", "complaint", "bug", "human"]
    for r in order:
        cfg = rules.get(r) or {}
        if cfg.get("enabled") is False:
            continue
        extra = [re.escape(norm(w)) for w in (cfg.get("words") or []) if str(w).strip()]
        if r == "money":
            strict = bool(cfg.get("strict"))
            if re.search(_MONEY_TOPIC, joined) and (strict or re.search(_MONEY_PROBLEM, joined)):
                return r
            if any(re.search(p, joined) for p in extra):
                return r
            continue
        for p in DEFAULT_PATTERNS.get(r, []) + extra:
            if re.search(p, joined, re.M):
                return r
    return None
