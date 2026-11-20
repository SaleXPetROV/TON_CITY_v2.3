"""Copy the Russian source of every screen-text namespace (frontend/src/i18n/<ns>.json → "ru") to the server
(backend/data/ui_i18n_ru.json), where LibreTranslate translates it into the other languages.
Run after changing a text: python3 scripts/sync_ui_i18n.py"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "src", "i18n")
DST = os.path.join(ROOT, "backend", "data", "ui_i18n_ru.json")

out = {}
for f in sorted(os.listdir(SRC)):
    if f.endswith(".json"):
        out[f[:-5]] = json.load(open(os.path.join(SRC, f), encoding="utf-8"))["ru"]
json.dump(out, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(f"{DST}: " + ", ".join(f"{k} ({len(v)})" for k, v in out.items()))
