"""Screen texts in every language of the project, translated by the server's LibreTranslate.

The Russian source of each namespace is `data/ui_i18n_ru.json` (copied from frontend/src/i18n/<ns>.json by
scripts/sync_ui_i18n.py). GET /api/i18n/{ns}?lang=xx returns the namespace in that language: every string is
translated once (ru → xx, placeholders like {n} and $CITY protected), kept in `ui_i18n` and translated again only
when its Russian text changes. At start the server translates whatever is missing in the background.
Without LibreTranslate nothing is stored and the app shows its own Russian / English."""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

LANGS = ("en", "es", "zh", "fr", "de", "ja", "ko", "id")
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ui_i18n_ru.json")


@lru_cache(maxsize=1)
def sources() -> Dict[str, Dict[str, str]]:
    try:
        return json.load(open(_SRC, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ui_i18n sources: {e}")
        return {}


async def bundle(db, ns: str, lang: str, budget: int = 40) -> Dict[str, Any]:
    src = sources().get(ns)
    if src is None:
        raise HTTPException(status_code=404, detail="unknown_namespace")
    lang = (lang or "ru").lower()
    if lang == "ru" or lang not in LANGS:
        return {"ns": ns, "lang": "ru" if lang == "ru" else lang, "texts": {} if lang != "ru" else src, "complete": lang == "ru"}
    have: Dict[str, Dict[str, Any]] = {}
    async for d in db.ui_i18n.find({"ns": ns, "lang": lang}, {"_id": 0, "key": 1, "text": 1, "src": 1}):
        have[d["key"]] = d
    try:
        from translation_service import libretranslate_configured, translate_libre_protected
        can = libretranslate_configured()
    except Exception:  # noqa: BLE001
        can = False
    out: Dict[str, str] = {}
    missing = 0
    for k, ru in src.items():
        d = have.get(k)
        if d and d.get("src") == ru and d.get("text"):
            out[k] = d["text"]
            continue
        if not can or budget <= 0:
            missing += 1
            continue
        budget -= 1
        try:
            tr = (await translate_libre_protected(ru, lang, "ru")).strip()
        except ValueError:                       # a placeholder got lost: keep the app's own text for this one
            missing += 1
            continue
        except Exception as e:  # noqa: BLE001
            logger.warning(f"ui_i18n {ns}.{k} → {lang}: {e}")
            can = False
            missing += 1
            continue
        if tr:
            out[k] = tr
            await db.ui_i18n.update_one({"_id": f"{ns}:{lang}:{k}"}, {"$set": {"ns": ns, "lang": lang, "key": k, "text": tr, "src": ru,
                                                                            "by": "libretranslate"}}, upsert=True)
    return {"ns": ns, "lang": lang, "texts": out, "complete": missing == 0}


async def warm(db) -> int:
    n = 0
    for ns in sources():
        for lang in LANGS:
            r = await bundle(db, ns, lang, budget=10 ** 6)
            n += len(r["texts"])
    return n


def create_router(db) -> APIRouter:
    r = APIRouter(prefix="/i18n", tags=["i18n"])

    @r.get("/{ns}")
    async def get_bundle(ns: str, lang: str = "en"):
        return await bundle(db, ns, lang)

    return r
