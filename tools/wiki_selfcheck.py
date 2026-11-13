#!/usr/bin/env python3
"""Autotest of «Справочник» before a release: every «Показать на деле» button and every «?» is really on its screen.

The articles point at real buttons of the game (data-testid). If a button is renamed or removed, this test fails here,
not in front of a player. It opens each article's screen with a real test account and looks for each framed button;
for a step that waits for a press («Действие») it presses the button, as a player would, and goes on.

    python3 tools/wiki_selfcheck.py --base http://localhost:3000 --token <JWT of a test player with a business>
    (or WIKI_CHECK_TOKEN=... ; --lang ru ; --phone / --desktop)

Exit code 0 — all found; 1 — something is missing (the list is printed).
Steps with {bid}/{prod} need the test player to own a business; without one they are reported as «skipped».
"""
import argparse
import json
import os
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

SCREENS = {"map": "/ton-island", "maps": "/maps", "resources": "/resources", "trading": "/trading", "community": "/community",
           "chat": "/chat", "tasks": "/tasks", "city-pass": "/city-pass", "credit": "/credit", "history": "/history",
           "settings": "/settings", "security": "/security", "marketplace": "/marketplace", "leaderboard": "/leaderboard",
           "analytics": "/analytics"}


def get(url, token=None):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fill(s, v):
    for k, val in v.items():
        s = s.replace("{" + k + "}", str(val or ""))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3000")
    ap.add_argument("--api", default=None, help="backend base (default: same as --base)")
    ap.add_argument("--token", default=os.environ.get("WIKI_CHECK_TOKEN", ""))
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--desktop", action="store_true", help="1280×800 instead of a phone")
    a = ap.parse_args()
    api = (a.api or a.base).rstrip("/") + "/api/wiki"
    if not a.token:
        sys.exit("a test player's token is needed: --token or WIKI_CHECK_TOKEN")
    idx = get(f"{api}/index?lang={a.lang}")
    slugs = [x["slug"] for s in idx["sections"] for x in s["articles"]]
    fails, skipped, ok = [], [], 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        vp = {"width": 1280, "height": 800} if a.desktop else {"width": 390, "height": 844}
        c = b.new_context(viewport=vp)
        c.add_init_script(f"try{{localStorage.setItem('token','{a.token}');localStorage.setItem('ton_city_lang','{a.lang}');"
                          "localStorage.setItem('ton_city_lang_explicit','1');localStorage.setItem('gc_intro_voice','off')}catch(e){}")
        pg = c.new_page()
        # the app sends a fresh start of /maps and /ton-island to «Бизнесы»: open it once, then move inside the app
        pg.goto(a.base.rstrip("/") + "/my-businesses")
        time.sleep(6)

        def go(route):
            pg.evaluate("r => { window.history.pushState({}, '', r); window.dispatchEvent(new PopStateEvent('popstate')); }", route)

        def find(sels, timeout=8.0):
            end = time.time() + timeout
            while time.time() < end:
                for s in sels:
                    try:
                        for el in pg.query_selector_all(s):
                            if el.is_visible():
                                return el
                    except Exception:
                        pass
                time.sleep(0.25)
            return None

        for slug in slugs:
            art = get(f"{api}/article/{slug}?lang={a.lang}")
            show = art.get("show")
            if not show or not show.get("steps"):
                continue
            vars_ = get(f"{api}/check/{slug}?lang={a.lang}", a.token).get("vars", {}) if art.get("needs") else {}
            if any("{bid}" in s or "{prod}" in s for st in show["steps"] for s in st["sel"]) and not vars_.get("bid"):
                vars_ = get(f"{api}/check/shift?lang={a.lang}", a.token).get("vars", {})
            for _ in range(2):                         # close what the previous article opened (a dialog, a sheet)
                pg.keyboard.press("Escape")
                time.sleep(0.3)
            go(fill(show["route"], vars_))
            time.sleep(2.5)
            for i, st in enumerate(show["steps"], 1):
                sels = [fill(s, vars_) for s in st["sel"]]
                if all("{" in s for s in sels):
                    skipped.append(f"{slug} step {i}: needs a business")
                    continue
                el = find([s for s in sels if "{" not in s])
                if not el:
                    fails.append(f"{slug} step {i}: none of {sels} on {show['route']}")
                    continue
                ok += 1
                if st.get("tap"):
                    try:
                        el.click(timeout=3000)
                        time.sleep(1.2)
                    except Exception as e:
                        fails.append(f"{slug} step {i}: cannot press ({e.__class__.__name__})")
        for scr, route in SCREENS.items():
            go(route)
            if find([f"[data-testid=wiki-help-{scr}]"], 10):
                ok += 1
            else:
                fails.append(f"«?» missing on {route} (wiki-help-{scr})")
        b.close()
    print(f"found: {ok}, missing: {len(fails)}, skipped: {len(skipped)}")
    for s in skipped:
        print("  skipped —", s)
    for f in fails:
        print("  MISSING —", f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
