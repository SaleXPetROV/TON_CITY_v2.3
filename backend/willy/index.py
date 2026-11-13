"""Search over the Russian answer base.

Two engines, the stronger one wins:
• keyword engine — inside the backend, always on: TF-IDF cosine over word stems + character trigrams
  between the question and every phrasing of every answer. Builds in well under a second.
• meaning engine — the separate `willy` service (txtai + multilingual-e5-small, see /willy_service),
  used when WILLY_URL is set. If it is down or slow, the keyword engine answers alone.

Every worker keeps its own copy of the keyword index and rebuilds it when the base revision
(`willy_meta`, bumped by every edit in the admin) changes."""
import math
import os
import time
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .text import content, stems, trigrams

logger = logging.getLogger(__name__)

W_STEM, W_TRI = 0.7, 0.3
W_PHR, W_ANS = 0.65, 0.35   # the best single phrasing vs. the answer as a whole (all phrasings + its text)
_IDX: Dict[str, Any] = {"rev": None, "checked": 0.0, "built": None}


class _Vec:
    """Sparse TF-IDF vectors with an inverted index."""

    def __init__(self, docs: List[List[str]]):
        df: Dict[str, int] = defaultdict(int)
        for d in docs:
            for t in set(d):
                df[t] += 1
        n = max(1, len(docs))
        self.idf = {t: math.log(1 + n / c) for t, c in df.items()}
        self.post: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        self.norm: List[float] = []
        for i, d in enumerate(docs):
            tf: Dict[str, int] = defaultdict(int)
            for t in d:
                tf[t] += 1
            s = 0.0
            for t, c in tf.items():
                w = (1 + math.log(c)) * self.idf[t]
                self.post[t].append((i, w))
                s += w * w
            self.norm.append(math.sqrt(s) or 1.0)

    def scores(self, q: List[str]) -> Dict[int, float]:
        tf: Dict[str, int] = defaultdict(int)
        for t in q:
            if t in self.idf:
                tf[t] += 1
        # a bare number (a level, an amount) says little on its own: half weight, so «10 → 30 units» does not pull
        # «City Pass level 10/30»
        qv = {t: (1 + math.log(c)) * self.idf[t] * (0.5 if t.isdigit() else 1.0) for t, c in tf.items()}
        qn = math.sqrt(sum(w * w for w in qv.values())) or 1.0
        acc: Dict[int, float] = defaultdict(float)
        for t, qw in qv.items():
            for i, w in self.post.get(t, ()):
                acc[i] += qw * w
        return {i: s / (qn * self.norm[i]) for i, s in acc.items()}


class Index:
    def __init__(self, answers: List[Dict[str, Any]]):
        self.answers = {a["id"]: a for a in answers}
        self.agent_only = {a["id"] for a in answers if a.get("agent_only")}
        # hand-written / admin answers win a tie over the ones built from the config (prio 0)
        self.prio = {a["id"]: float(a.get("prio", 1) or 0) for a in answers}
        self.owner: List[str] = []
        st, tr = [], []
        for a in answers:
            for p in [a.get("title") or ""] + list(a.get("phrasings") or []):
                if not p.strip():
                    continue
                self.owner.append(a["id"])
                st.append(stems(p))
                tr.append(trigrams(p))
        self.stem = _Vec(st)
        self.tri = _Vec(tr)
        self.size = len(self.owner)
        # the answer as a whole: its topic words weigh in even when no single phrasing is close
        self.aids = [a["id"] for a in answers]
        self.whole = _Vec([stems(" ".join([a.get("title") or ""] * 2 + list(a.get("phrasings") or []) + [a.get("text") or ""]))
                           for a in answers])

    def search(self, q: str, k: int = 5, agent: bool = False) -> List[Tuple[str, float]]:
        q = content(q)
        s1 = self.stem.scores(stems(q))
        s2 = self.tri.scores(trigrams(q))
        best: Dict[str, float] = {}
        for i in set(s1) | set(s2):
            sc = W_STEM * s1.get(i, 0.0) + W_TRI * s2.get(i, 0.0)
            aid = self.owner[i]
            if sc > best.get(aid, 0.0):
                best[aid] = sc
        whole = {self.aids[i]: v for i, v in self.whole.scores(stems(q)).items()}
        out = {aid: W_PHR * best.get(aid, 0.0) + W_ANS * whole.get(aid, 0.0) + 0.03 * self.prio.get(aid, 1)
               for aid in set(best) | set(whole) if agent or aid not in self.agent_only}
        # a phrasing typed word for word stays a sure answer
        for aid, v in best.items():
            if v >= 0.97 and aid in out:
                out[aid] = max(out[aid], v + 0.03 * self.prio.get(aid, 1))
        top = sorted(out.items(), key=lambda kv: -kv[1])[:k]      # ranked with the hand-written bonus, then capped at 1
        return [(aid, min(1.0, v)) for aid, v in top]


async def _rev(db) -> int:
    m = await db.willy_meta.find_one({"_id": "rev"}, {"rev": 1})
    return int((m or {}).get("rev") or 0)


async def bump(db) -> int:
    """An answer was added/changed: every worker rebuilds on its next question; the night job rebuilds the meaning
    index (only when something changed)."""
    r = await db.willy_meta.find_one_and_update({"_id": "rev"}, {"$inc": {"rev": 1}, "$set": {"dirty": True}},
                                                upsert=True, return_document=True)
    _IDX["checked"] = 0.0
    return int((r or {}).get("rev") or 0)


async def get(db, force: bool = False) -> Index:
    now = time.time()
    if not force and _IDX["built"] is not None and now - _IDX["checked"] < 15:
        return _IDX["built"]
    rev = await _rev(db)
    _IDX["checked"] = now
    if force or _IDX["built"] is None or rev != _IDX["rev"]:
        rows = await db.willy_answers.find({"enabled": True}, {"_id": 0, "id": 1, "title": 1, "phrasings": 1, "text": 1, "agent_only": 1, "prio": 1}).to_list(20000)
        import asyncio
        _IDX["built"] = await asyncio.to_thread(Index, rows)   # ~1–2 s for 3 000 answers: off the event loop
        _IDX["rev"] = rev
    return _IDX["built"]


# ───────────────────────── meaning engine (optional service) ─────────────────────────

def service_url() -> str:
    return (os.environ.get("WILLY_URL") or "").rstrip("/")


async def semantic(queries: List[str], k: int = 5) -> Optional[List[Tuple[str, float]]]:
    """[(answer_id, score 0..1)] from the willy service, or None when it is not set up / not answering."""
    url = service_url()
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=float(os.environ.get("WILLY_TIMEOUT", "1.5"))) as c:
            r = await c.post(f"{url}/search", json={"q": [q for q in queries if q], "k": k})
            r.raise_for_status()
            return [(h["id"], float(h["score"])) for h in (r.json().get("hits") or [])]
    except Exception as e:  # noqa: BLE001
        logger.info(f"willy service unavailable: {e}")
        return None


async def service_upsert(rows: List[Dict[str, Any]]) -> bool:
    url = service_url()
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{url}/upsert", json={"rows": rows})
            return r.status_code < 300
    except Exception:  # noqa: BLE001
        return False


async def service_rebuild(db) -> bool:
    url = service_url()
    if not url:
        return False
    rows = await db.willy_answers.find({"enabled": True}, {"_id": 0, "id": 1, "title": 1, "phrasings": 1}).to_list(20000)
    try:
        async with httpx.AsyncClient(timeout=3600) as c:
            r = await c.post(f"{url}/rebuild", json={"rows": rows})
            return r.status_code < 300
    except Exception as e:  # noqa: BLE001
        logger.warning(f"willy service rebuild failed: {e}")
        return False


async def health() -> Dict[str, Any]:
    url = service_url()
    if not url:
        return {"configured": False, "ok": False}
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{url}/health")
            return {"configured": True, "ok": r.status_code == 200, **(r.json() if r.status_code == 200 else {})}
    except Exception as e:  # noqa: BLE001
        return {"configured": True, "ok": False, "error": str(e)[:200]}
