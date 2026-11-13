"""Willy GRAM meaning search: the Russian phrasings of the answer base → vectors (multilingual-e5-small, ONNX int8)
→ a faiss index with 1-byte numbers. The backend sends a question (its Russian translation and the original),
gets back the closest answers. Nothing leaves the server; no tick: idle = no CPU.

  GET  /health
  POST /search   {q: [texts], k}            → {hits: [{id, score}]}       score — cosine 0..1, best phrasing per answer
  POST /upsert   {rows: [{id, title, phrasings}]}   one answer changed in the admin: its phrasings are replaced at once
  POST /rebuild  {rows: [...]}              the whole base (night job at 04:00 МСК, only after edits)
"""
import json
import os
import re
import threading
from typing import Dict, List

from fastapi import FastAPI
from pydantic import BaseModel
from txtai import Embeddings

DATA = os.environ.get("WILLY_DATA", "/var/lib/willy")
MODELS = os.environ.get("WILLY_MODELS", "/opt/willy/models")
IDX = os.path.join(DATA, "index")
MAP = os.path.join(DATA, "ids.json")
CONFIG = {
    "path": os.path.join(MODELS, "e5.onnx"),
    "tokenizer": os.path.join(MODELS, "tok"),
    "instructions": {"query": "query: ", "data": "passage: "},   # e5 wants these prefixes
    "backend": "faiss",
    "faiss": {"quantize": 8},                                     # 1 byte per number instead of 4
    "content": False,
}
app = FastAPI(title="Willy GRAM search")
_lock = threading.Lock()
emb: Embeddings = None
ids: Dict[str, List[str]] = {}     # answer id → its phrasing uids


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower().replace("ё", "е")).strip(" ?!.,")


def _rows(rows) -> List[tuple]:
    out, seen = [], set()
    for r in rows:
        k = 0
        for t in [r.get("title") or ""] + list(r.get("phrasings") or []):
            n = _norm(t)
            if not n or (r["id"], n) in seen:          # near-identical phrasings are stored once
                continue
            seen.add((r["id"], n))
            out.append((f"{r['id']}#{k}", n, None))
            k += 1
    return out


def _save():
    os.makedirs(DATA, exist_ok=True)
    emb.save(IDX)
    with open(MAP, "w") as f:
        json.dump(ids, f)


def _load():
    global emb, ids
    emb = Embeddings(CONFIG)
    if os.path.exists(IDX) and os.path.exists(MAP):
        emb.load(IDX)
        with open(MAP) as f:
            ids = json.load(f)


_load()


class SearchIn(BaseModel):
    q: List[str]
    k: int = 5


class RowsIn(BaseModel):
    rows: List[dict]


@app.get("/health")
def health():
    return {"ok": True, "phrasings": emb.count() if emb and emb.ann else 0, "answers": len(ids)}


@app.post("/search")
def search(data: SearchIn):
    if not emb or not emb.ann:
        return {"hits": []}
    best: Dict[str, float] = {}
    for q in [x for x in data.q if x and x.strip()][:2]:
        for uid, score in emb.search(_norm(q), max(10, data.k * 6)):
            aid = str(uid).split("#", 1)[0]
            if score > best.get(aid, 0.0):
                best[aid] = float(score)
    hits = sorted(best.items(), key=lambda kv: -kv[1])[: data.k]
    return {"hits": [{"id": a, "score": round(s, 4)} for a, s in hits]}


@app.post("/upsert")
def upsert(data: RowsIn):
    global emb
    with _lock:
        if not emb.ann:
            return rebuild(data)
        old = [u for r in data.rows for u in ids.get(r["id"], [])]
        if old:
            emb.delete(old)
        rows = _rows(data.rows)
        if rows:
            emb.upsert(rows)
        for r in data.rows:
            ids[r["id"]] = [u for u, _, _ in rows if u.split("#", 1)[0] == r["id"]]
        _save()
    return {"ok": True, "phrasings": len(rows)}


@app.post("/rebuild")
def rebuild(data: RowsIn):
    global emb, ids
    rows = _rows(data.rows)
    fresh = Embeddings(CONFIG)
    fresh.index(rows)
    m: Dict[str, List[str]] = {}
    for u, _, _ in rows:
        m.setdefault(u.split("#", 1)[0], []).append(u)
    with _lock:
        emb, ids = fresh, m
        _save()
    return {"ok": True, "phrasings": len(rows), "answers": len(m)}
