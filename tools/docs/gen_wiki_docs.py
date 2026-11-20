"""documentation/ for GitBook = the player's «Справочник» (the same articles as in the game, on /wiki and for Willy).

    cd backend && python ../tools/docs/gen_wiki_docs.py

Writes documentation/README.md (the start page), documentation/<section>/README.md + <section>/<slug>.md for every
article (Russian, numbers = the game's defaults) and documentation/SUMMARY.md (the GitBook menu). The files are made by
backend/wiki_gitbook.render_docs — the very function the game's GitBook sync compares with, so an article that nobody
changed in GitBook keeps the game's live numbers and translations. Change the articles in backend/wiki_content/ (or
right in GitBook — the game takes them from there) and re-run.
"""
import asyncio
import os
import re
import shutil
import sys

BACK = os.path.abspath(os.getcwd())
DOC = os.path.join(os.path.dirname(BACK), "documentation")
sys.path.insert(0, BACK)


async def build() -> int:
    import wiki_gitbook as G
    files = G.render_docs(G.seed_docs(), await G.default_vars())
    if os.path.isdir(DOC):
        shutil.rmtree(DOC)
    for rel, text in files.items():
        p = os.path.join(DOC, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    # checks: every link goes somewhere, every page is in the menu
    links = re.findall(r"\]\(([^)]+)\)", files["SUMMARY.md"])
    pages = {r for r in files if r != "SUMMARY.md"}
    bad = []
    for rel, text in files.items():
        for link in re.findall(r"\]\(([^)\s]+)\)", text):
            if not link.startswith(("http", "mailto", "#")) and \
                    os.path.normpath(os.path.join(os.path.dirname(rel), link.split("#")[0])) not in files:
                bad.append((rel, link))
    orphan = sorted(pages - set(links))
    if bad or orphan or len(links) != len(set(links)):
        sys.exit(f"broken links {bad}, not in the menu {orphan}")
    return len([r for r in files if not r.endswith("README.md") and r != "SUMMARY.md"])


if __name__ == "__main__":
    print("articles", asyncio.run(build()))
