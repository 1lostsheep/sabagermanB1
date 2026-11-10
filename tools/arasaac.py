"""ARASAAC pictures (https://arasaac.org): free pictograms made for language learners.

Licence: CC BY-NC-SA 4.0. Author: Sergio Palao. Owner: Government of Aragón (Spain).
Fine for this private, non-commercial family app. See LICENSES.md.

    .venv/bin/python tools/arasaac.py Arzt Termin "zum Arzt gehen"   # show picture ids for words

In content JSON a picture is written as "arasaac:<id>", e.g. "arasaac:6561".
tools/build_batch.py downloads it to content/media/pictures/arasaac/<id>.png.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.arasaac.org/v1/pictograms"
IMAGE = "https://static.arasaac.org/pictograms/{id}/{id}_300.png"


def search(term: str, lang: str = "de", limit: int = 8) -> list[dict]:
    """Best matches first: exact keyword matches, then the rest. Skips sensitive pictures."""
    url = f"{API}/{lang}/search/{urllib.parse.quote(term)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            items = json.loads(r.read())
    except Exception:
        return []
    out = []
    t = term.lower()
    for it in items:
        if it.get("sex") or it.get("violence"):
            continue
        kws = [k["keyword"] for k in it.get("keywords", [])]
        exact = any(k.lower() == t for k in kws)
        out.append({"id": it["_id"], "keywords": kws, "exact": exact})
    out.sort(key=lambda x: not x["exact"])  # stable: keeps ARASAAC's own ranking otherwise
    return out[:limit]


def download(pid: int, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(IMAGE.format(id=pid), timeout=60) as r:
        dest.write_bytes(r.read())


if __name__ == "__main__":
    for term in sys.argv[1:]:
        print(f"{term}:")
        for c in search(term):
            print(f"  arasaac:{c['id']:<6} {'*' if c['exact'] else ' '} {', '.join(c['keywords'][:4])}")
