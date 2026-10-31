"""Presale set up district by district: selecting plots in one district keeps the other districts' plots and plans;
a plan made before the plots were sold no longer blocks the selection (cut to what is free, with a warning);
sold presale plots are reported apart and not counted («Выставлю» = what is really on sale); a plot of an older layout
of the map (its cell is another business now) is dropped."""
import os
import sys

import pytest

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def test_select_by_district_and_sold_plans():
    import httpx
    import jwt
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from pymongo import MongoClient
    from security_middleware import get_or_generate_jwt_secret
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    B = "http://127.0.0.1:8001/api/admin"
    try:
        httpx.get("http://127.0.0.1:8001/api/health", timeout=3)
    except Exception:
        pytest.skip("server not running")
    tok = jwt.encode({"sub": "sanyanazarov212@gmail.com", "exp": 9999999999}, get_or_generate_jwt_secret(), algorithm="HS256")
    h = {"Authorization": f"Bearer {tok}"}
    orig = db.admin_settings.find_one({"type": "presale"}, {"_id": 0})
    inv = httpx.get(f"{B}/presale/inventory", headers=h, timeout=30).json()
    bd = inv["by_district"]
    ds = [d for d in sorted(bd, key=int) if any(v["free"] >= 2 for v in bd[d].values())]
    if len(ds) < 2:
        pytest.skip("need two districts with free plots")
    d1, d2 = int(ds[0]), int(ds[1])
    t1 = next(t for t, v in bd[ds[0]].items() if v["free"] >= 2)
    t2 = next(t for t, v in bd[ds[1]].items() if v["free"] >= 2)
    tag_plot = None
    try:
        r = httpx.post(f"{B}/presale/select-plots", headers=h, json={"businesses": [
            {"district": d1, "type": t1, "count": 2}, {"district": d2, "type": t2, "count": 1}]}).json()
        first = {(p["x"], p["y"]) for p in r["selected_plots"] if p["district"] == d1}
        assert len(first) == 2
        # one plot of district 1 is sold; its plan now asks more than is free
        x, y = sorted(first)[0]
        tag_plot = {"id": f"presale-test-{x}-{y}", "island_id": "ton_island", "x": x, "y": y, "owner": "presale-test"}
        db.plots.insert_one(dict(tag_plot))
        free1 = bd[ds[0]][t1]["free"] - 1
        # re-select ONLY district 2 with a bigger plan there; district 1 has an impossible plan (sold out) — no 400
        r = httpx.post(f"{B}/presale/select-plots", headers=h, json={"only_district": d2, "businesses": [
            {"district": d1, "type": t1, "count": free1 + 5}, {"district": d2, "type": t2, "count": 2}]})
        assert r.status_code == 200, r.text
        r = r.json()
        now1 = {(p["x"], p["y"]) for p in r["selected_plots"] if p["district"] == d1}
        assert now1 == first - {(x, y)}                       # district 1 untouched; the sold plot is reported apart
        assert r["sold_count"] == 1
        assert next(b for b in r["businesses"] if b["district"] == d1)["count"] == 1     # on sale now, not the old plan
        assert sum(1 for p in r["selected_plots"] if p["district"] == d2) == 2
        # the full re-selection cuts the over-plan to what is free instead of refusing; the unsold plot already in
        # the presale is kept (no reshuffle), the sold one stays in the list
        unsold_before = first - {(x, y)}
        r = httpx.post(f"{B}/presale/select-plots", headers=h, json={"businesses": [
            {"district": d1, "type": t1, "count": free1 + 5}]})
        assert r.status_code == 200 and r.json()["warnings"]
        assert next(b for b in r.json()["businesses"] if b["district"] == d1)["count"] == free1
        sel1 = {(p["x"], p["y"]) for p in r.json()["selected_plots"] if p["district"] == d1}
        assert unsold_before <= sel1 and (x, y) not in sel1 and r.json()["sold_count"] == 1
        # the admin view: only what is on sale; the sold one is counted apart; the plan = what is on sale
        v = httpx.get(f"{B}/presale", headers=h).json()
        assert (x, y) not in {(p["x"], p["y"]) for p in v["selected_plots"]} and v["sold_count"] == 1
        assert next(b for b in v["businesses"] if b["district"] == d1)["count"] == free1
        # a plot of an older layout (the cell holds another business now): not shown, not counted, dropped on select
        cells = db.islands.find_one({"id": "ton_island"}, {"_id": 0, "cells": 1})["cells"]
        other = next(c for c in cells if c.get("pre_business") and c["pre_business"] != t1 and not c.get("is_empty"))
        db.admin_settings.update_one({"type": "presale"}, {"$push": {"selected_plots": {
            "x": other["x"], "y": other["y"], "business_type": t1, "district": d1}}})
        v = httpx.get(f"{B}/presale", headers=h).json()
        assert (other["x"], other["y"]) not in {(p["x"], p["y"]) for p in v["selected_plots"]}
        assert next(b for b in v["businesses"] if b["district"] == d1)["count"] == free1
        r = httpx.post(f"{B}/presale/select-plots", headers=h, json={"businesses": v["businesses"]}).json()
        assert not r["warnings"]
        doc = db.admin_settings.find_one({"type": "presale"}, {"_id": 0, "selected_plots": 1})
        assert (other["x"], other["y"]) not in {(p["x"], p["y"]) for p in doc["selected_plots"]}
        assert (x, y) in {(p["x"], p["y"]) for p in doc["selected_plots"]}         # the sold one is kept (lease may end)
        # the level-0 lease ended: the plot record is removed → the plot is on sale again (in the presale, not sold)
        db.plots.delete_one({"id": tag_plot["id"]})
        tag_plot = None
        sel = httpx.get(f"{B}/presale", headers=h).json()["selected_plots"]
        assert [p["sold"] for p in sel if (p["x"], p["y"]) == (x, y)] == [False]
        import presale_gate  # noqa: F401  (the buy gate reads the same list)
        doc = db.admin_settings.find_one({"type": "presale"}, {"_id": 0, "selected_plots": 1})
        assert any((p["x"], p["y"]) == (x, y) for p in doc["selected_plots"])
    finally:
        if tag_plot:
            db.plots.delete_one({"id": tag_plot["id"]})
        db.admin_settings.delete_one({"type": "presale"})
        if orig:
            db.admin_settings.insert_one({**orig, "type": "presale"})
