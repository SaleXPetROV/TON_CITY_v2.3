"""Images uploaded for announcements: stored ONCE as a file, referenced by URL.

Before, an uploaded picture was kept as a `data:` URI (up to 2 MB of base64) inside the announcement and copied into
the in-app notification of EVERY player, and re-uploaded to Telegram for every recipient. Now:
  • the file lives in <UPLOADS_ROOT>/announcements/<sha>.<ext> and is served by GET /api/media/announcements/<name>;
  • the announcement and every notification store only that short URL;
  • Telegram receives the bytes once, then the bot re-sends the returned file_id (telegram_bot.send_photo).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

URL_PREFIX = "/api/media/announcements/"
_NAME_RE = re.compile(r"/api/media/announcements/([A-Za-z0-9_-]+\.(?:png|jpg|webp|gif))$")
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp", "image/gif": "gif"}
MIME = {v: k for k, v in _EXT.items() if k != "image/jpg"}


def media_dir() -> Path:
    root = Path(os.environ.get("UPLOADS_ROOT") or (Path(__file__).resolve().parents[1] / "uploads"))
    d = root / "announcements"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sniff_mime(data: bytes, declared: str = "") -> Optional[str]:
    head = data[:12]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def save_image(data: bytes, mime: str) -> str:
    """Store the bytes (same picture → same file) and return its URL."""
    ext = _EXT.get((mime or "").lower(), "png")
    name = f"{hashlib.sha256(data).hexdigest()[:32]}.{ext}"
    f = media_dir() / name
    if not f.is_file():
        tmp = f.with_suffix(f.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(f)
    return URL_PREFIX + name


def local_file(url: Optional[str]) -> Optional[Path]:
    """The file behind one of our media URLs (relative or absolute), else None."""
    if not url or not isinstance(url, str):
        return None
    m = _NAME_RE.search(url.split("?", 1)[0])
    if not m:
        return None
    f = media_dir() / m.group(1)
    return f if f.is_file() else None


def decode_data_uri(s: str) -> Optional[Tuple[bytes, str]]:
    try:
        head, b64 = s.split(",", 1)
        mime = head.split(";")[0].split(":", 1)[1] if ":" in head else "image/png"
        return base64.b64decode(b64), mime
    except Exception:
        return None


def to_media_url(image: Optional[str]) -> Optional[str]:
    """A `data:` URI becomes a stored file URL; anything else is returned as is."""
    if not image or not isinstance(image, str) or not image.startswith("data:"):
        return image
    dec = decode_data_uri(image)
    if not dec:
        return image
    data, mime = dec
    mime = sniff_mime(data) or mime
    try:
        return save_image(data, mime)
    except Exception as e:
        logger.warning(f"announcement image could not be stored as a file: {e}")
        return image


def announcement_to_media(ann: dict) -> bool:
    """Convert every data: picture of an announcement (top level + translations) in place. True if changed."""
    changed = False
    url = to_media_url(ann.get("image_url"))
    if url != ann.get("image_url"):
        ann["image_url"], changed = url, True
    for tr in (ann.get("translations") or {}).values():
        if isinstance(tr, dict):
            u = to_media_url(tr.get("image_url"))
            if u != tr.get("image_url"):
                tr["image_url"], changed = u, True
    return changed


async def migrate_old_announcements(db) -> dict:
    """One-off cleanup: announcements (and their per-player notifications) that still carry data: pictures."""
    n_ann = n_notif = 0
    async for ann in db.announcements.find({"$or": [{"image_url": {"$regex": "^data:"}},
                                                    {"translations": {"$exists": True, "$ne": None}}]}, {"_id": 0}):
        before = {"top": ann.get("image_url"),
                  **{k: (v or {}).get("image_url") for k, v in (ann.get("translations") or {}).items() if isinstance(v, dict)}}
        if not announcement_to_media(ann):
            continue
        await db.announcements.update_one({"id": ann["id"]}, {"$set": {"image_url": ann.get("image_url"),
                                                                       "translations": ann.get("translations")}})
        n_ann += 1
        after = {"top": ann.get("image_url"),
                 **{k: (v or {}).get("image_url") for k, v in (ann.get("translations") or {}).items() if isinstance(v, dict)}}
        for k, old in before.items():
            new = after.get(k)
            if isinstance(old, str) and old.startswith("data:") and new and new != old:
                r = await db.notifications.update_many({"type": "announcement", "image_url": old}, {"$set": {"image_url": new}})
                n_notif += r.modified_count
    if n_ann or n_notif:
        logger.warning(f"📣 announcement pictures moved to files: {n_ann} announcements, {n_notif} notifications")
    return {"announcements": n_ann, "notifications": n_notif}
