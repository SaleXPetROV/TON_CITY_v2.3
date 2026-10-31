"""Announcements in the player's language: before a broadcast the announcement is translated with LibreTranslate
into every language of the project that the admin did not fill himself.

The translations are kept only while they are needed: `announcement_translations`
{announcement_id, lang, data {title, message, image_url, buttons}, expires_at} — a broadcast that is retried or
continued uses them instead of asking LibreTranslate again, and they are deleted one day later (TTL index +
cleanup). Every player gets the variant of his language: in Telegram and in the in-app notification.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

LANGS = ("en", "ru", "es", "zh", "fr", "de", "ja", "ko", "id")
KEEP = timedelta(days=1)


async def ensure_indexes(db) -> None:
    try:
        await db.announcement_translations.create_index([("announcement_id", 1), ("lang", 1)], unique=True)
        await db.announcement_translations.create_index("expires_at", expireAfterSeconds=0)
    except Exception as e:                                # FerretDB may lack TTL — cleanup() covers it
        logger.debug(f"announcement_translations indexes: {e}")


async def cleanup(db) -> int:
    """Translations older than one day are removed (also done by the TTL index where the database supports it)."""
    try:
        r = await db.announcement_translations.delete_many({"expires_at": {"$lt": datetime.now(timezone.utc)}})
        return int(r.deleted_count or 0)
    except Exception as e:
        logger.debug(f"announcement translations cleanup: {e}")
        return 0


async def _tr(text: str, target: str, source: str) -> str:
    """One text: placeholders / links / $CITY / emoji protected; HTML kept.
    Emoji are kept in place: first as protected placeholders; if the engine loses one, the text is translated piece
    by piece BETWEEN the emoji (the emoji themselves are never sent), so a «🚀 Играть» button stays «🚀 Play»."""
    import translation_service as ts
    if not text or not text.strip() or target == source:
        return text
    try:
        return await ts.translate_libre_protected(text, target, source, protect_emoji=True)
    except Exception:
        pass
    if not ts.EMOJI_RE.search(text):
        try:
            return await ts.translate_libre_protected(text, target, source)
        except Exception:
            return await ts._translate_libre(text, target, source)
    emojis = ts.EMOJI_RE.findall(text)
    out = []
    for i, part in enumerate(ts.EMOJI_RE.split(text)):   # split() drops the emoji: put each back after its piece
        out.append(await _tr_plain(part, target, source))
        if i < len(emojis):
            out.append(emojis[i])
    return "".join(out)


async def _tr_plain(part: str, target: str, source: str) -> str:
    """A piece of text without emoji; its surrounding spaces / punctuation-only pieces are kept as they are."""
    import re
    import translation_service as ts
    m = re.match(r"^(\s*)(.*?)(\s*)$", part, re.DOTALL)
    lead, core, trail = (m.group(1), m.group(2), m.group(3)) if m else ("", part, "")
    if not re.search(r"\w", core):
        return part
    try:
        tr = await ts.translate_libre_protected(core, target, source)
    except Exception:
        tr = await ts._translate_libre(core, target, source)
    return f"{lead}{tr or core}{trail}"


def _source(ann: Dict[str, Any], existing: Dict[str, Any]):
    """The text everything is translated from: the admin's Russian / English variant, or the main text."""
    import translation_service as ts
    for lang in ("ru", "en"):
        if lang in existing:
            return lang, existing[lang]
    if existing:
        lang = next(iter(existing))
        return lang, existing[lang]
    src = {"title": ann.get("title") or "", "message": ann.get("message") or "",
           "image_url": ann.get("image_url"), "buttons": ann.get("buttons") or []}
    lang = (ann.get("lang") or "").lower()
    if lang not in LANGS:
        import re
        plain = re.sub(r"<[^>]+>", " ", f"{src['title']} {src['message']}")
        lang = ts.detect_language(plain) or "ru"
    return lang, src


async def auto_translate(db, ann: Dict[str, Any], normalize=lambda c: c, progress=None) -> Optional[Dict[str, Any]]:
    """{lang: {title, message, image_url, buttons}} for EVERY language of the project (the admin's own variants are
    kept as they are). Returns the admin's translations unchanged when LibreTranslate is not configured.

    `progress(lang, state)` (async, optional) is told about every language as it goes — state: "source" (the text
    everything is translated from), "manual" (written by the admin), "cached" (translated earlier, kept a day),
    "running", "done", "failed" — the admin's broadcast window shows it live."""
    import translation_service as ts

    async def _tell(lang, state):
        if progress:
            try:
                await progress(lang, state)
            except Exception as e:                        # the progress display never breaks the broadcast
                logger.debug(f"translation progress: {e}")

    existing = {normalize(k): v for k, v in (ann.get("translations") or {}).items() if v}
    if not ts.libretranslate_configured():
        return ann.get("translations")
    await cleanup(db)
    ann_id = ann.get("id") or ""
    src_lang, src = _source(ann, existing)
    out: Dict[str, Any] = dict(existing)
    out.setdefault(src_lang, src)
    for lang in out:
        await _tell(lang, "source" if lang == src_lang else "manual")
    made = []
    for lang in LANGS:
        if lang in out:
            continue
        cached = await db.announcement_translations.find_one({"announcement_id": ann_id, "lang": lang}, {"_id": 0, "data": 1})
        if cached and cached.get("data"):
            out[lang] = cached["data"]
            await _tell(lang, "cached")
            continue
        await _tell(lang, "running")
        try:
            data = {"title": await _tr(src.get("title") or "", lang, src_lang),
                    "message": await _tr(src.get("message") or "", lang, src_lang),
                    "image_url": src.get("image_url"),
                    "buttons": [{"text": (await _tr(b.get("text") or "", lang, src_lang))[:60] or b.get("text"), "url": b.get("url")}
                                for b in (src.get("buttons") or []) if b.get("url")]}
        except Exception as e:                            # this language gets the main text (as before)
            logger.warning(f"announcement {ann_id}: translation to {lang} failed: {e}")
            await _tell(lang, "failed")
            continue
        if not data["message"]:
            await _tell(lang, "failed")
            continue
        out[lang] = data
        made.append(lang)
        await _tell(lang, "done")
        try:
            await db.announcement_translations.update_one(
                {"announcement_id": ann_id, "lang": lang},
                {"$set": {"announcement_id": ann_id, "lang": lang, "data": data, "source_lang": src_lang,
                          "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + KEEP}},
                upsert=True)
        except Exception as e:
            logger.debug(f"announcement translation save: {e}")
    if made:
        logger.info(f"announcement {ann_id}: auto-translated from {src_lang} to {', '.join(made)}")
    return out


def source_lang(ann: Dict[str, Any], normalize=lambda c: c) -> str:
    """The language the admin wrote the announcement in (the default language of the channel post)."""
    existing = {normalize(k): v for k, v in (ann.get("translations") or {}).items() if v}
    try:
        return _source(ann, existing)[0]
    except Exception:
        return "ru"


async def cached_translations(db, ann_id: str) -> Dict[str, Any]:
    """The auto-translations kept for a day (shown in the admin's broadcast window)."""
    out: Dict[str, Any] = {}
    try:
        async for d in db.announcement_translations.find({"announcement_id": ann_id}, {"_id": 0, "lang": 1, "data": 1}):
            if d.get("data"):
                out[d["lang"]] = d["data"]
    except Exception as e:
        logger.debug(f"cached translations: {e}")
    return out
