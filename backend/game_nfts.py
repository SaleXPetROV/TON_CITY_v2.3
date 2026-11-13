"""NFT of every game: a game has its own list of NFTs; each NFT is a 3×3 picture (an `mg_puzzles` puzzle + its
`mg_nfts` NFT). Its 9 pieces are collected from that game's chests:

  • the chest of a good game is given only when the player has watched EVERY ad of that game's reward
    (arcade.py: the XP chain 2/4 → 3/4 → 4/4; the chest comes with the last ad — games_hub.chest_after_ads);
  • with NFT on for the game, every such chest holds one piece for sure (100 %).

Which NFT the piece belongs to is drawn among the game's NFTs that can still be collected (a started picture always
finishes; a new one starts only while the NFT's quantity lasts — the supply guarantee of minigame_rewards). 9/9 →
«Собрать» (minigame_rewards.assemble_puzzle) → the NFT goes to the player's wallet (or waits for the stock).

An NFT is a picture, a GIF / animated WebP or a video (mp4 / webm): `media_url` + `media_type` (image | gif | video);
`image_url` is always a still picture (the poster of a video, the first frame of a GIF) — it is cut into the 9 pieces.

Per game (admin_settings {type: "game_nfts", games: {<game>: {...}}}):
    enabled            NFT in this game on / off (off by default: the games run for points only)
    puzzles            the game's NFTs (ids of mg_puzzles)
Player: users.mg_total_by_game.<game> (total points of the game, for statistics).
"""
from __future__ import annotations

import io
import logging
import random
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import minigame_rewards as mr

logger = logging.getLogger(__name__)

CFG_TYPE = "game_nfts"
MEDIA_TYPES = ("image", "gif", "video")
_rng = random.SystemRandom()


# ───────────────────────────── settings ─────────────────────────────
async def get_config(db) -> Dict[str, Any]:
    d = await db.admin_settings.find_one({"type": CFG_TYPE}, {"_id": 0}) or {}
    return {"games": dict(d.get("games") or {})}


def game_cfg(cfg: Dict[str, Any], game: str) -> Dict[str, Any]:
    g = dict((cfg.get("games") or {}).get(game) or {})
    return {"enabled": bool(g.get("enabled", False)), "puzzles": [p for p in (g.get("puzzles") or []) if p]}


async def _good_game_score(db, game: str) -> int:
    import arcade
    import games_hub
    import minigames as mg
    cfg = await mg.get_config(db)
    if game == "sorter":
        sp = cfg.get("star_points") or [300, 1000, 2000]
        return int(sp[min(len(sp) - 1, 1)] or 1000)
    return int(games_hub.chest_score(cfg, await arcade.get_config(db), game) or 1000)


# ───────────────────────────── pieces ─────────────────────────────
async def _candidates(db, uid: str, puzzle_ids: List[str]) -> List[Dict[str, Any]]:
    out = []
    for pid in puzzle_ids:
        puzzle = await mr._find(db, "mg_puzzles", {"id": pid})
        ok, cur = await mr._puzzle_open_for(db, uid, puzzle)
        if ok:
            out.append({"puzzle": puzzle, "cur": cur})
    return out


async def give_piece(db, uid: str, game: str, gc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A piece of one of the game's NFTs (drawn among those that can still be collected), or None."""
    cands = await _candidates(db, uid, gc["puzzles"])
    if not cands:
        return None
    c = _rng.choice(cands)
    got = await mr._add_piece(db, uid, c["puzzle"], c["cur"])
    if not got:
        return None
    p = c["puzzle"]
    got.update(name=p.get("name"), name_i18n=p.get("name_i18n"), game=game,
               image_url=f"/api/minigames/img/puzzle_{p['id']}_{got['piece']}.webp" if p.get("has_pieces") else None)
    return got


async def after_game(db, uid: str, game: str, score: int) -> Dict[str, Any]:
    """Every counted game: the total points of the game grow (statistics). Returns {total_points, enabled}."""
    if score > 0:
        await db.users.update_one({"id": uid}, {"$inc": {f"mg_total_by_game.{game}": int(score)}})
    u = await db.users.find_one({"id": uid}, {"_id": 0, "mg_total_by_game": 1}) or {}
    gc = game_cfg(await get_config(db), game)
    return {"total_points": int((u.get("mg_total_by_game") or {}).get(game) or 0),
            "enabled": gc["enabled"] and bool(gc["puzzles"])}


async def chest_piece(db, uid: str, game: str, chest: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A game chest that was given → one piece of one of the game's NFTs inside it, for sure (once per chest).
    None when NFT are off for the game, it has no NFT, or every NFT is already taken."""
    if not chest or not chest.get("given") or not chest.get("user_container_id"):
        return None
    gc = game_cfg(await get_config(db), game)
    if not gc["enabled"] or not gc["puzzles"]:
        return None
    ucid = chest["user_container_id"]
    first = await db.mg_user_containers.update_one({"id": ucid, "nft_rolled": {"$ne": True}}, {"$set": {"nft_rolled": True}})
    if not first.modified_count:
        return None
    got = await give_piece(db, uid, game, gc)
    if not got:
        return None
    await db.mg_user_containers.update_one({"id": ucid}, {"$push": {"results": got}})
    if isinstance(chest.get("chest"), dict):
        chest["chest"]["results"] = list(chest["chest"].get("results") or []) + [got]
    chest["nft_piece"] = got
    try:
        from core.notify import notify_user_background
        notify_user_background(db, uid, title="🧩 Часть NFT!", message="Откройте «Игры» → игра → «Награды».",
                               type_key="minigame_prize", telegram=False)
    except Exception:
        pass
    return got


# ───────────────────────────── the player's track ─────────────────────────────
def ghost_url(puzzle: Dict[str, Any]) -> Optional[str]:
    """A dark, blurred picture of the NFT — the teaser shown behind the pieces not collected yet."""
    try:
        from minigame_rewards_routes import img_dir
        pid = puzzle["id"]
        dst = img_dir() / f"puzzle_{pid}_ghost.webp"
        if not dst.exists():
            name = (puzzle.get("image_url") or "").rsplit("/", 1)[-1]
            src = img_dir() / name
            if not name or not src.exists():
                return None
            from PIL import Image, ImageEnhance, ImageFilter
            im = Image.open(src).convert("RGB")
            side = min(im.size)
            im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width - side) // 2 + side, (im.height - side) // 2 + side))
            im = im.resize((360, 360)).filter(ImageFilter.GaussianBlur(16))
            im = ImageEnhance.Brightness(im).enhance(0.42)
            im.save(dst, "WEBP", quality=80)
        return f"/api/minigames/img/puzzle_{pid}_ghost.webp"
    except Exception as e:
        logger.debug(f"ghost image: {e}")
        return None


async def nft_rows(db, uid: Optional[str], puzzle_ids: List[str], admin: bool = False) -> List[Dict[str, Any]]:
    rows = []
    for pid in puzzle_ids:
        p = await mr._find(db, "mg_puzzles", {"id": pid})
        if not p:
            continue
        nft = await mr._find(db, "mg_nfts", {"id": p.get("nft_id")}) or {}
        up = None
        grant = None
        if uid:
            mine = await db.mg_user_puzzles.find({"user_id": uid, "puzzle_id": pid}, {"_id": 0}).sort("round", -1).to_list(1)
            up = mine[0] if mine else None
            if up and up.get("grant_id"):
                grant = mr.public_grant(await mr._find(db, "mg_nft_grants", {"id": up["grant_id"]}))
        pieces = sorted(set((up or {}).get("pieces") or []))
        started = await db.mg_user_puzzles.count_documents({"puzzle_id": pid, "status": {"$in": ["collecting", "complete"]}})
        supply = int(nft.get("supply_total") or 0)
        granted = int(nft.get("granted") or 0)
        rows.append({
            "puzzle_id": pid, "nft_id": p.get("nft_id"), "name": p.get("name") or nft.get("name"),
            "name_i18n": p.get("name_i18n") or {}, "kind": nft.get("kind"), "is_active": bool(p.get("is_active")),
            "pieces": pieces, "have": len(pieces), "status": (up or {}).get("status") or "none",
            "piece_urls": {str(n): f"/api/minigames/img/puzzle_{pid}_{n}.webp" for n in pieces} if p.get("has_pieces") else {},
            "ghost_url": ghost_url(p) if p.get("has_pieces") else None,
            "image_url": p.get("image_url") or nft.get("image_url"),
            "media_url": p.get("media_url") or nft.get("media_url") or p.get("image_url") or nft.get("image_url"),
            "media_type": p.get("media_type") or nft.get("media_type") or "image",
            "supply_total": supply, "granted": granted, "collecting": started,
            "left": max(0, supply - granted - started),
            "assembled": await db.mg_user_puzzles.count_documents({"puzzle_id": pid, "status": "assembled"}),
            "grant": grant,
        })
    return rows


async def track(db, uid: str, game: str) -> Dict[str, Any]:
    import games_hub
    import minigames as mg
    if game not in games_hub.all_games():
        raise HTTPException(status_code=404, detail="unknown_game")
    import arcade
    gc = game_cfg(await get_config(db), game)
    u = await db.users.find_one({"id": uid}, {"_id": 0, "mg_total_by_game": 1, "wallet_address": 1}) or {}
    total = int((u.get("mg_total_by_game") or {}).get(game) or 0)
    acfg = await arcade.get_config(db)
    cfg = await mg.get_config(db)
    board = games_hub.board_id(game)
    lb = await mr.leaderboard(db, board, limit=5, prizes=games_hub.prizes_for(cfg, game))
    me = await games_hub.my_board(db, uid, board)
    return {
        "game": game, "user_id": uid, "nft_network": (await mr.nft_settings(db))["network"],
        "enabled": gc["enabled"] and bool(gc["puzzles"]), "nft_on": gc["enabled"],
        "total_points": total,
        "nfts": await nft_rows(db, uid, gc["puzzles"]) if gc["puzzles"] else [],
        "has_wallet": bool(u.get("wallet_address")),
        "week": {"id": games_hub.week_id(), "ends_at": games_hub.week_ends_at(), "points": me.get("points", 0),
                 "place": me.get("place"), "leaders": lb.get("rows", [])[:5],
                 "prizes": await mr.describe_prizes(db, [p for p in games_hub.prizes_for(cfg, game) if int(p.get("from", 0)) <= 5])},
        "chests": {"today": await mr.chests_today(db, uid), "per_day": int(cfg.get("chests_per_day") or 0),
                   "min_score": await _good_game_score(db, game),
                   # the chest comes only after every ad of the game's reward (sorter: no ads → by its stars)
                   "after_ads": game != "sorter", "ads_per_reward": int(acfg.get("ads_per_reward") or 3)},
    }


async def hub_summary(db, uid: str) -> Dict[str, Dict[str, int]]:
    """{game: {have, total}} — the pieces collected per game (the badge on the game cards)."""
    cfg = await get_config(db)
    out: Dict[str, Dict[str, int]] = {}
    for game, raw in (cfg.get("games") or {}).items():
        gc = game_cfg(cfg, game)
        if not gc["enabled"] or not gc["puzzles"]:
            continue
        have = 0
        for up in await db.mg_user_puzzles.find({"user_id": uid, "puzzle_id": {"$in": gc["puzzles"]}},
                                                {"_id": 0, "pieces": 1, "status": 1}).to_list(200):
            have += 9 if up.get("status") == "assembled" else len(set(up.get("pieces") or []))
        out[game] = {"have": have, "total": 9 * len(gc["puzzles"])}
    return out


async def backfill_totals(db) -> int:
    """Once: the total points of every game from the points of all past weeks (the players keep their history)."""
    if await db.admin_settings.find_one({"type": "game_nfts_backfill", "done": True}):
        return 0
    sums: Dict[tuple, int] = {}
    async for p in db.minigame_points.find({}, {"_id": 0, "campaign_id": 1, "user_id": 1, "points": 1}):
        cid, uid = str(p.get("campaign_id") or ""), p.get("user_id")
        if not uid or not cid:
            continue
        game = cid.split(":", 1)[1] if ":" in cid else "sorter"
        sums[(uid, game)] = sums.get((uid, game), 0) + int(p.get("points") or 0)
    for (uid, game), pts in sums.items():
        if pts > 0:
            await db.users.update_one({"id": uid}, {"$inc": {f"mg_total_by_game.{game}": pts}})
    await db.admin_settings.update_one({"type": "game_nfts_backfill"}, {"$set": {"type": "game_nfts_backfill", "done": True,
                                                                                "users": len(sums), "at": mr._iso()}}, upsert=True)
    return len(sums)


# ───────────────────────────── media (picture / GIF / video) ─────────────────────────────
MAX_MEDIA = 30 * 1024 * 1024


def _poster_from(im, name: str) -> str:
    """A still picture (≤ 1024 px, webp) from a PIL image — the poster that is cut into the pieces."""
    from minigame_rewards_routes import img_dir
    im = im.convert("RGBA")
    im.thumbnail((1024, 1024))
    im.save(img_dir() / name, "WEBP", quality=90)
    return f"/api/minigames/img/{name}"


def _video_kind(raw: bytes) -> Optional[str]:
    if len(raw) > 12 and raw[4:8] == b"ftyp":
        brand = raw[8:12]
        return "mov" if brand == b"qt  " else "mp4"
    if raw[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def _ffmpeg_poster(video: Path, dst: Path) -> bool:
    ff = shutil.which("ffmpeg")
    if not ff:
        return False
    for ss in ("0.5", "0"):
        try:
            subprocess.run([ff, "-y", "-loglevel", "error", "-ss", ss, "-i", str(video), "-frames:v", "1",
                            "-vf", "scale='min(1024,iw)':-2", str(dst)], timeout=60, check=True)
            if dst.exists() and dst.stat().st_size > 0:
                return True
        except Exception as e:
            logger.debug(f"ffmpeg poster: {e}")
    return False


async def save_media(file: UploadFile, poster: Optional[UploadFile] = None) -> Dict[str, Any]:
    """The admin's NFT file → {media_url, media_type, image_url (the still picture for the pieces)}.
    picture (png / jpg / webp) → webp; GIF / animated WebP → kept animated + the first frame;
    video (mp4 / webm; mov → mp4 with ffmpeg) → kept + a poster (sent by the admin panel, or a frame by ffmpeg)."""
    from minigame_rewards_routes import img_dir
    from PIL import Image
    raw = await file.read()
    if len(raw) > MAX_MEDIA:
        raise HTTPException(status_code=400, detail="Файл больше 30 МБ")
    if not raw:
        raise HTTPException(status_code=400, detail="Пустой файл")
    key = uuid.uuid4().hex[:10]
    vk = _video_kind(raw)
    if vk:
        ext = "webm" if vk == "webm" else "mp4"
        dst = img_dir() / f"nftv_{key}.{ext}"
        if vk == "mov":                                   # QuickTime → mp4 (the same streams; browsers play mp4)
            ff = shutil.which("ffmpeg")
            if not ff:
                raise HTTPException(status_code=400, detail="Видео .mov не поддерживается — загрузите mp4 или webm")
            with tempfile.TemporaryDirectory() as td:
                src = Path(td) / "in.mov"
                src.write_bytes(raw)
                try:
                    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(dst)],
                                   timeout=120, check=True)
                except Exception:
                    raise HTTPException(status_code=400, detail="Не удалось преобразовать .mov — загрузите mp4 или webm")
        else:
            dst.write_bytes(raw)
        poster_url = None
        if poster is not None:
            praw = await poster.read()
            if praw:
                try:
                    pim = Image.open(io.BytesIO(praw)); pim.load()
                    poster_url = _poster_from(pim, f"nftp_{key}.webp")
                except Exception:
                    poster_url = None
        if not poster_url:
            pd = img_dir() / f"nftp_{key}.webp"
            tmp = img_dir() / f"nftp_{key}.png"
            if _ffmpeg_poster(dst, tmp):
                try:
                    poster_url = _poster_from(Image.open(tmp), pd.name)
                finally:
                    tmp.unlink(missing_ok=True)
        if not poster_url:
            dst.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Не удалось взять кадр из видео — попробуйте другой файл")
        return {"media_url": f"/api/minigames/img/{dst.name}", "media_type": "video", "image_url": poster_url}
    try:
        im = Image.open(io.BytesIO(raw)); im.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Это не картинка, не GIF и не видео (mp4 / webm)")
    animated = bool(getattr(im, "is_animated", False)) and int(getattr(im, "n_frames", 1) or 1) > 1
    if animated and (im.format or "").upper() in ("GIF", "WEBP"):
        ext = "gif" if (im.format or "").upper() == "GIF" else "webp"
        name = f"nfta_{key}.{ext}"
        (img_dir() / name).write_bytes(raw)              # kept as it is: the animation plays in the app and wallets
        im.seek(0)
        return {"media_url": f"/api/minigames/img/{name}", "media_type": "gif",
                "image_url": _poster_from(im.copy(), f"nftp_{key}.webp")}
    url = _poster_from(im, f"nfti_{key}.webp")
    return {"media_url": url, "media_type": "image", "image_url": url}


# ───────────────────────────── admin ─────────────────────────────
async def cut_puzzle(pid: str, image_url: str) -> bool:
    from minigame_rewards_routes import img_dir
    from PIL import Image
    name = (image_url or "").rsplit("/", 1)[-1]
    src = img_dir() / name
    if not name or not src.exists():
        return False
    im = Image.open(src).convert("RGBA")
    side = min(im.size)
    im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width - side) // 2 + side, (im.height - side) // 2 + side))
    im = im.resize((600, 600))
    for n in range(1, 10):
        row, col = (n - 1) // 3, (n - 1) % 3
        im.crop((col * 200, row * 200, col * 200 + 200, row * 200 + 200)).save(img_dir() / f"puzzle_{pid}_{n}.webp", "WEBP", quality=88)
    ghost = img_dir() / f"puzzle_{pid}_ghost.webp"
    if ghost.exists():
        ghost.unlink()
    return True


async def _translate_name(name: str) -> Dict[str, str]:
    out = {}
    try:
        import translation_service as ts
        if not ts.libretranslate_configured():
            return {}
        src = ts.detect_language(name) or "ru"
        for lang in mr.LANGS:
            if lang == src:
                out[lang] = name
                continue
            try:
                out[lang] = (await ts.translate_libre_protected(name, lang, src, protect_emoji=True))[:80]
            except Exception:
                pass
    except Exception:
        return {}
    return out


async def _save_game(db, game: str, gc: Dict[str, Any]) -> None:
    await db.admin_settings.update_one({"type": CFG_TYPE}, {"$set": {"type": CFG_TYPE, f"games.{game}": gc}}, upsert=True)


async def admin_view(db) -> Dict[str, Any]:
    import games_hub
    cfg = await get_config(db)
    games = []
    attached = set()
    for g in games_hub.all_games():
        gc = game_cfg(cfg, g)
        attached |= set(gc["puzzles"])
        nfts = await nft_rows(db, None, gc["puzzles"], admin=True)
        games.append({"game": g, **gc, "good_game_score": await _good_game_score(db, g), "nfts": nfts,
                      "players_with_pieces": await db.mg_user_puzzles.count_documents({"puzzle_id": {"$in": gc["puzzles"]}}) if gc["puzzles"] else 0})
    free = [{"puzzle_id": p["id"], "name": p.get("name"), "nft_id": p.get("nft_id")}
            for p in await mr._all(db, "mg_puzzles", {}) if p["id"] not in attached]
    return {"games": games, "free_puzzles": free}


def create_game_nfts_router(db, get_current_user, get_current_admin) -> APIRouter:
    r = APIRouter()

    @r.get("/api/games/{game}/nft-track")
    async def player_track(game: str, current_user=Depends(get_current_user)):
        return await track(db, current_user.id, game)

    @r.post("/api/admin/game-nfts/upload")
    async def a_upload(file: UploadFile = File(...), poster: Optional[UploadFile] = File(None), _=Depends(get_current_admin)):
        """The NFT file: a picture, a GIF / animated WebP or a video (+ its poster frame from the admin panel)."""
        return await save_media(file, poster)

    @r.get("/api/admin/game-nfts")
    async def a_view(_=Depends(get_current_admin)):
        return await admin_view(db)

    async def _game(game: str) -> Dict[str, Any]:
        import games_hub
        if game not in games_hub.all_games():
            raise HTTPException(status_code=404, detail="Неизвестная игра")
        return game_cfg(await get_config(db), game)

    @r.put("/api/admin/game-nfts/{game}")
    async def a_put(game: str, body: Dict[str, Any], _=Depends(get_current_admin)):
        gc = await _game(game)
        if "enabled" in body:
            gc["enabled"] = bool(body["enabled"])
        await _save_game(db, game, gc)
        return await admin_view(db)

    @r.post("/api/admin/game-nfts/{game}/nfts")
    async def a_new_nft(game: str, body: Dict[str, Any], _=Depends(get_current_admin)):
        """A new NFT of the game in one step: the NFT (quantity that can be collected) + its 3×3 picture."""
        gc = await _game(game)
        name = (body.get("name") or "").strip()[:80]
        if not name:
            raise HTTPException(status_code=400, detail="Нужно название NFT")
        image = (body.get("image_url") or "").strip()
        if not image:
            raise HTTPException(status_code=400, detail="Загрузите файл NFT (картинка, GIF или видео) — его кадр режется на 9 частей")
        media_type = body.get("media_type") if body.get("media_type") in MEDIA_TYPES else "image"
        media = (body.get("media_url") or "").strip() or image
        if not media.startswith("/api/minigames/img/") or not image.startswith("/api/minigames/img/"):
            raise HTTPException(status_code=400, detail="Файл NFT загружается через «Загрузить»")
        supply = int(float(body.get("supply_total") or 0))
        if supply < 1:
            raise HTTPException(status_code=400, detail="Сколько можно получить — не меньше 1")
        kind = body.get("kind") if body.get("kind") in mr.NFT_KINDS else "tradable"
        i18n = await _translate_name(name)
        nid, pid = f"n_{uuid.uuid4().hex[:10]}", f"p_{uuid.uuid4().hex[:10]}"
        now = mr._iso()
        await db.mg_nfts.insert_one({"id": nid, "name": name, "kind": kind, "supply_total": supply, "granted": 0, "next_index": 0,
                                     "description": (body.get("description") or "")[:500], "image_url": image,
                                     "media_url": media, "media_type": media_type,
                                     "collection_address": "", "content_template": "{nft_id}/{index}.json", "attributes": [],
                                     "low_stock_alert": max(1, supply // 10), "is_active": True, "game": game, "created_at": now})
        has = await cut_puzzle(pid, image)
        await db.mg_puzzles.insert_one({"id": pid, "name": name, "name_i18n": i18n, "nft_id": nid, "image_url": image,
                                        "media_url": media, "media_type": media_type, "repeatable": False, "is_active": True, "has_pieces": has, "game": game, "created_at": now})
        gc["puzzles"] = [*gc["puzzles"], pid]
        await _save_game(db, game, gc)
        return await admin_view(db)

    @r.post("/api/admin/game-nfts/{game}/attach")
    async def a_attach(game: str, body: Dict[str, Any], _=Depends(get_current_admin)):
        gc = await _game(game)
        pid = body.get("puzzle_id")
        if not await mr._find(db, "mg_puzzles", {"id": pid}):
            raise HTTPException(status_code=400, detail="Пазл не найден")
        if pid not in gc["puzzles"]:
            gc["puzzles"] = [*gc["puzzles"], pid]
            await _save_game(db, game, gc)
        return await admin_view(db)

    @r.delete("/api/admin/game-nfts/{game}/nfts/{pid}")
    async def a_detach(game: str, pid: str, _=Depends(get_current_admin)):
        """Takes the NFT out of the game (pieces already collected stay with the players and can still be assembled)."""
        gc = await _game(game)
        gc["puzzles"] = [p for p in gc["puzzles"] if p != pid]
        await _save_game(db, game, gc)
        return await admin_view(db)

    @r.put("/api/admin/game-nfts/supply/{nid}")
    async def a_supply(nid: str, body: Dict[str, Any], _=Depends(get_current_admin)):
        """How many of this NFT can be collected (+ / −). Never below what is given + what players already collect."""
        nft = await mr._find(db, "mg_nfts", {"id": nid})
        if not nft:
            raise HTTPException(status_code=404)
        supply = int(float(body.get("supply_total") or 0))
        pids = [p["id"] for p in await mr._all(db, "mg_puzzles", {"nft_id": nid})]
        started = await db.mg_user_puzzles.count_documents({"puzzle_id": {"$in": pids}, "status": {"$in": ["collecting", "complete"]}}) if pids else 0
        loaded = await db.mg_nft_items.count_documents({"nft_id": nid, "kind": {"$ne": "sbt"}})
        floor_ = max(1, int(nft.get("granted") or 0) + started, loaded if nft.get("kind") != "sbt" else 0)
        if supply < floor_:
            raise HTTPException(status_code=400, detail=f"Нельзя меньше {floor_}: столько уже выдано или собирается игроками")
        await db.mg_nfts.update_one({"id": nid}, {"$set": {"supply_total": supply}})
        await mr.assign_waiting(db)
        return await admin_view(db)

    return r
