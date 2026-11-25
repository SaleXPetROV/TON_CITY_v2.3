"""The city map draws lots and parks sorted by the CENTRE of the lot (CityMapEngine: 2q+w+2r+h, then q).
Every lot / park standing behind another one (fully before it along x or y, overlapping on the other axis) must be
drawn first — otherwise a 2×2 park or a 3×3 building is painted over the 1×1 lot in front of it."""
import json
import os

LAYOUT = os.path.join(os.path.dirname(__file__), os.pardir, "data", "city_layout_v1.json")


def _items():
    lay = json.load(open(LAYOUT))
    items = [dict(q=s["x"], r=s["y"], w=s["w"], h=s["h"]) for s in lay["slots"]]
    parks = {(x, y) for x, y in lay["parks"]}
    used = set()
    for x, y in sorted(parks, key=lambda p: (p[1], p[0])):          # the same 2×2 grouping as the engine
        if (x, y) in used:
            continue
        sq = all((a, b) in parks and (a, b) not in used for a, b in [(x + 1, y), (x, y + 1), (x + 1, y + 1)])
        n = 2 if sq else 1
        used |= {(x + i, y + j) for i in range(n) for j in range(n)}
        items.append(dict(q=x, r=y, w=n, h=n))
    return items


def _behind(a, b):
    yo = a["r"] < b["r"] + b["h"] and b["r"] < a["r"] + a["h"]
    xo = a["q"] < b["q"] + b["w"] and b["q"] < a["q"] + a["w"]
    return (a["q"] + a["w"] <= b["q"] and yo) or (a["r"] + a["h"] <= b["r"] and xo)


def test_centre_depth_orders_every_neighbour_pair():
    key = lambda i: (2 * i["q"] + i["w"] + 2 * i["r"] + i["h"], i["q"])
    items = _items()
    bad = [(a, b) for a in items for b in items
           if a is not b and abs(a["q"] - b["q"]) <= 4 and abs(a["r"] - b["r"]) <= 4 and _behind(a, b) and key(a) >= key(b)]
    assert not bad, bad[:5]
