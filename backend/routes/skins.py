"""
Business Skins system.
======================
A "skin" re-textures a business on the map. Skins are grouped: the GROUP is what
the player sees (e.g. "Bio Farm", "Crazy Bio Farm") and is identified by a unique
`group_key`. Within a group each (business_type, level) can have its own image so
a business looks different at every level; if a level has no image the level 0
("any") image (or the standard skin) is used as a fallback.

Documents (db.business_skins):
  { id, group_key, group_name, business_type, level (0 = any level),
    image (public /sprites path OR data:image/webp;base64 URL),
    is_standard (bool), created_at }
Unique key: (group_key, business_type, level).

Ownership: everyone owns the "standard" group. A player owns other groups when the
group_key is present in `user.available_skins` (granted by partner quests). A skin
is applied PER BUSINESS via `business.skin_group`.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

STANDARD_GROUP = "standard"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_webp(image: str) -> bool:
    if not image:
        return False
    s = image.strip().lower()
    return s.endswith(".webp") or s.startswith("data:image/webp")


async def ensure_skin_indexes(db):
    try:
        await db.business_skins.create_index(
            [("group_key", 1), ("business_type", 1), ("level", 1)], unique=True, name="uniq_skin")
    except Exception as e:
        logger.debug(f"skin index ensure failed: {e}")


DEFAULT_SKINS = [
    {
        "group_key": STANDARD_GROUP, "group_name": "Standard",
        "business_type": "bio_farm", "level": 0,
        "image": "/sprites/bio_farm/bio_farm.webp", "is_standard": True,
    },
    {
        "group_key": "crazy_bio_farm", "group_name": "Crazy",
        "business_type": "bio_farm", "level": 0,
        "image": "/sprites/crazy_bio_farm/crazy_bio_farm.webp", "is_standard": False,
    },
]


async def seed_default_skins(db):
    await ensure_skin_indexes(db)
    for s in DEFAULT_SKINS:
        try:
            existing = await db.business_skins.find_one(
                {"group_key": s["group_key"], "business_type": s["business_type"], "level": s["level"]})
            if existing:
                await db.business_skins.update_one(
                    {"id": existing["id"]},
                    {"$set": {"image": s["image"], "group_name": s["group_name"], "is_standard": s["is_standard"]}})
            else:
                doc = {"id": str(uuid.uuid4()), "created_at": _now_iso(), **s}
                await db.business_skins.insert_one(doc)
        except Exception as e:
            logger.debug(f"seed skin failed: {e}")


def _clean(s: dict) -> dict:
    s.pop("_id", None)
    return s


class SkinCreate(BaseModel):
    group_key: str
    group_name: str
    business_type: str
    level: int = Field(0, ge=0, le=10)
    image: str  # /sprites path or data:image/webp;base64,...
    is_standard: bool = False


class ApplySkin(BaseModel):
    business_id: str
    group_key: str


class SkinSizeUpdate(BaseModel):
    # Display size on the map as a PERCENTAGE of the skin's natural size.
    # 100 = original. Bounded to sane values so a bad input can't break the map.
    height_pct: float = Field(100, ge=10, le=400)
    width_pct: float = Field(100, ge=10, le=400)


def create_skins_admin_router(db, admin_dependency):
    router = APIRouter(prefix="/api/admin/skins", tags=["skins-admin"])

    @router.get("")
    async def list_skins(group_key: Optional[str] = None, business_type: Optional[str] = None,
                         level: Optional[int] = None, admin=Depends(admin_dependency)):
        q = {}
        if group_key:
            q["group_key"] = group_key
        if business_type:
            q["business_type"] = business_type
        if level is not None:
            q["level"] = level
        skins = await db.business_skins.find(q, {"_id": 0}).sort("group_key", 1).to_list(2000)
        return {"skins": skins, "count": len(skins)}

    @router.get("/groups")
    async def list_groups(admin=Depends(admin_dependency)):
        skins = await db.business_skins.find({}, {"_id": 0}).to_list(2000)
        groups = {}
        for s in skins:
            g = groups.setdefault(s["group_key"], {
                "group_key": s["group_key"], "group_name": s.get("group_name"),
                "is_standard": s.get("is_standard", False), "count": 0,
                "image": None,
                "business_types": set()})
            g["count"] += 1
            g["business_types"].add(s.get("business_type"))
            # Representative preview image: prefer the level-0 ("any") image,
            # otherwise keep the first non-empty image we encounter.
            img = s.get("image")
            if img and (g["image"] is None or int(s.get("level", 0) or 0) == 0):
                g["image"] = img
        out = []
        for g in groups.values():
            g["business_types"] = sorted(list(g["business_types"]))
            out.append(g)
        return {"groups": sorted(out, key=lambda x: (not x["is_standard"], x["group_key"]))}

    @router.get("/exists")
    async def skin_exists(group_key: str, business_type: str, level: int = 0, admin=Depends(admin_dependency)):
        s = await db.business_skins.find_one(
            {"group_key": group_key, "business_type": business_type, "level": level}, {"_id": 0})
        return {"exists": bool(s), "skin": s}

    @router.post("")
    async def create_skin(data: SkinCreate, admin=Depends(admin_dependency)):
        if not _is_webp(data.image):
            raise HTTPException(status_code=400, detail="Изображение должно быть в формате WEBP")
        existing = await db.business_skins.find_one(
            {"group_key": data.group_key, "business_type": data.business_type, "level": data.level}, {"_id": 0})
        if existing:
            raise HTTPException(status_code=409, detail={
                "message": "Скин для этой группы, бизнеса и уровня уже существует",
                "existing": existing,
            })
        doc = {
            "id": str(uuid.uuid4()),
            "group_key": data.group_key.strip(),
            "group_name": data.group_name.strip() or data.group_key.strip(),
            "business_type": data.business_type,
            "level": int(data.level),
            "image": data.image,
            "is_standard": bool(data.is_standard),
            "created_at": _now_iso(),
        }
        await db.business_skins.insert_one(doc.copy())
        return {"status": "created", "skin": _clean(doc)}

    @router.delete("/{skin_id}")
    async def delete_skin(skin_id: str, admin=Depends(admin_dependency)):
        res = await db.business_skins.delete_one({"id": skin_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Скин не найден")
        return {"status": "deleted"}

    @router.patch("/{skin_id}/size")
    async def update_skin_size(skin_id: str, data: SkinSizeUpdate, admin=Depends(admin_dependency)):
        """Persist per-skin display size (height/width as % of the original)."""
        res = await db.business_skins.update_one(
            {"id": skin_id},
            {"$set": {
                "height_pct": float(data.height_pct),
                "width_pct": float(data.width_pct),
                "size_updated_at": _now_iso(),
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Скин не найден")
        skin = await db.business_skins.find_one({"id": skin_id}, {"_id": 0})
        return {"status": "updated", "skin": skin}

    return router


def create_skins_user_router(db, get_current_user):
    router = APIRouter(prefix="/api/skins", tags=["skins"])

    async def _full_user(current_user):
        uid = getattr(current_user, "id", None) or (current_user.get("id") if isinstance(current_user, dict) else None)
        doc = await db.users.find_one({"id": uid}, {"_id": 0})
        return doc or {}

    @router.get("/index")
    async def skins_index():
        """Nested index for the map renderer: {group_key: {business_type: {level: image}}}
        plus a parallel `sizes` map {group_key: {business_type: {level: {h, w}}}} with
        the admin-configured display size (percent of original, 100 = original)."""
        skins = await db.business_skins.find({}, {"_id": 0}).to_list(5000)
        idx = {}
        sizes = {}
        for s in skins:
            lvl = str(s["level"])
            idx.setdefault(s["group_key"], {}).setdefault(s["business_type"], {})[lvl] = s["image"]
            sizes.setdefault(s["group_key"], {}).setdefault(s["business_type"], {})[lvl] = {
                "h": float(s.get("height_pct", 100) or 100),
                "w": float(s.get("width_pct", 100) or 100),
            }
        return {"index": idx, "sizes": sizes}

    @router.get("/my")
    async def my_skins(business_type: Optional[str] = None, current_user=Depends(get_current_user)):
        """Groups the player owns (standard + available_skins) that have a skin for
        the given business_type. Returns a representative image + name per group."""
        user_doc = await _full_user(current_user)
        owned = set(user_doc.get("available_skins") or [])
        owned.add(STANDARD_GROUP)
        q = {"group_key": {"$in": list(owned)}}
        if business_type:
            q["business_type"] = business_type
        skins = await db.business_skins.find(q, {"_id": 0}).to_list(2000)
        groups = {}
        for s in skins:
            g = groups.setdefault(s["group_key"], {
                "group_key": s["group_key"], "group_name": s.get("group_name"),
                "is_standard": s.get("is_standard", False), "image": None, "by_level": {}})
            g["by_level"][str(s["level"])] = s["image"]
            # representative: prefer level 0 (any), else the lowest level
            if g["image"] is None or s["level"] == 0:
                g["image"] = s["image"]
        out = sorted(groups.values(), key=lambda x: (not x["is_standard"], x["group_key"]))
        return {"skins": out}

    @router.post("/apply")
    async def apply_skin(data: ApplySkin, current_user=Depends(get_current_user)):
        user_doc = await _full_user(current_user)
        uid = user_doc.get("id")
        owned = set(user_doc.get("available_skins") or [])
        owned.add(STANDARD_GROUP)
        if data.group_key not in owned:
            raise HTTPException(status_code=403, detail="У вас нет этого скина")
        # Verify a skin exists for this group + business type
        biz = await db.businesses.find_one({"id": data.business_id}, {"_id": 0})
        if not biz:
            raise HTTPException(status_code=404, detail="Бизнес не найден")
        owner_keys = {biz.get("owner"), biz.get("owner_wallet"), biz.get("owner_id")}
        if uid not in owner_keys and user_doc.get("wallet_address") not in owner_keys and user_doc.get("email") not in owner_keys:
            raise HTTPException(status_code=403, detail="Это не ваш бизнес")
        if data.group_key != STANDARD_GROUP:
            has = await db.business_skins.find_one(
                {"group_key": data.group_key, "business_type": biz.get("business_type")})
            if not has:
                raise HTTPException(status_code=400, detail="Для этого бизнеса нет такого скина")
        await db.businesses.update_one({"id": data.business_id}, {"$set": {"skin_group": data.group_key}})
        return {"status": "applied", "business_id": data.business_id, "skin_group": data.group_key}

    return router
