"""Unified translation service.

Provider selection:
  • If LIBRETRANSLATE_URL is configured → use the self-hosted LibreTranslate
    server (free, no per-request cost).
  • Otherwise (or if LibreTranslate is unreachable) → fall back to the Emergent
    universal LLM key so translation never hard-fails.

All 8 project languages share ISO-639-1 codes that LibreTranslate understands
directly: ru, en, es, zh, fr, de, ja, ko.
"""
import os
import re
import uuid
import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Supported project languages -> English names (used by the LLM fallback prompt).
CHAT_LANGS = {
    "ru": "Russian", "en": "English", "es": "Spanish", "zh": "Chinese (Simplified)",
    "fr": "French", "de": "German", "ja": "Japanese", "ko": "Korean", "id": "Indonesian",
}


async def _translate_libre(text: str, target_lang: str, source_lang: str) -> str:
    """Translate via a self-hosted LibreTranslate server."""
    url = (os.environ.get("LIBRETRANSLATE_URL") or "").rstrip("/")
    payload = {
        "q": text,
        "source": source_lang or "auto",
        "target": target_lang,
        "format": "text",
    }
    api_key = os.environ.get("LIBRETRANSLATE_API_KEY")
    if api_key:
        payload["api_key"] = api_key
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{url}/translate", json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("translatedText") or "").strip()


async def _translate_emergent(text: str, target_lang: str) -> str:
    """Fallback translation via the Emergent universal LLM key."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Translation is not configured")
    target_name = CHAT_LANGS.get(target_lang, target_lang)
    chat = LlmChat(
        api_key=key,
        session_id=f"translate-{uuid.uuid4()}",
        system_message=(
            f"You are a translation engine. Translate the user's message into {target_name}. "
            "Output ONLY the translated text — no quotes, no explanations, no notes, "
            "no language labels. Preserve emojis and line breaks."
        ),
    ).with_model("openai", "gpt-5.4-mini")
    result = await chat.send_message(UserMessage(text=text))
    return (result or "").strip()


async def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Translate `text` into `target_lang`. Returns ONLY the translated string.

    Uses LibreTranslate when LIBRETRANSLATE_URL is set; on any error it falls
    back to the Emergent LLM so a temporarily-down LibreTranslate never breaks
    chat/support translation.
    """
    if not text or not text.strip():
        return ""
    if os.environ.get("LIBRETRANSLATE_URL"):
        try:
            out = await _translate_libre(text, target_lang, source_lang)
            if out:
                return out
        except Exception as e:  # noqa: BLE001 — fall back gracefully
            logger.warning(f"LibreTranslate failed ({e}); falling back to Emergent LLM")
    return await _translate_emergent(text, target_lang)


def script_language(text: str) -> str | None:
    """Return the language implied by the text's script when it is unambiguous
    for our 8-language set (Cyrillic→ru, Hangul→ko, Kana→ja, Han-only→zh).
    Returns None for Latin/empty text (needs statistical detection)."""
    if not text or not text.strip():
        return None
    t = text
    if re.search(r'[\u0400-\u04FF]', t):
        return "ru"
    if re.search(r'[\uAC00-\uD7A3]', t):
        return "ko"
    if re.search(r'[\u3040-\u30FF]', t):
        return "ja"
    if re.search(r'[\u4E00-\u9FFF]', t):
        return "zh"
    return None


def detect_language(text: str) -> str | None:
    """Best-effort detection of a message's language, mapped to the project's
    8 supported languages. Offline & fast (no external service needed):

    • Script shortcuts are 100% reliable for our language set (Cyrillic→ru,
      Hangul→ko, Kana→ja, Han-only→zh).
    • Latin text is disambiguated among en/es/fr/de via `langdetect`.
    Returns a 2-letter code from CHAT_LANGS, or None if the text is empty.
    """
    if not text or not text.strip():
        return None
    scripted = script_language(text)
    if scripted:
        return scripted
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        code = detect(text.strip())
        if code in CHAT_LANGS:
            return code
        if code in ("ca", "gl"):                # Catalan/Galician ~ Spanish
            return "es"
    except Exception:
        pass
    return "en"  # default for Latin-script text we can't pin down

