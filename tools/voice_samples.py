#!/usr/bin/env python3
"""Let Saba hear several German voices and pick one.

    .venv/bin/python tools/voice_samples.py            # Google voices (+ Piper to compare)
    .venv/bin/python tools/voice_samples.py --max 6    # fewer voices per gender

Writes data/voice-samples/index.html with a play button per voice and opens it.
Then put the chosen names in .env (GOOGLE_TTS_VOICE_F / GOOGLE_TTS_VOICE_M) and re-record:
    .venv/bin/python tools/build_batch.py all --force
"""
import argparse
import html
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import tts  # noqa: E402

OUT = ROOT / "data" / "voice-samples"
SAMPLE = [
    "Guten Tag, hier ist die Praxis Doktor Weber.",
    "Ihr Termin am Donnerstag geht leider nicht. Können Sie am Freitag um halb zehn kommen?",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max", type=int, default=8, help="voices per gender (default 8)")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    env = tts.config.load_env()
    rate = float(env.get("GOOGLE_TTS_RATE") or 0.92)

    rows = []
    g = tts.GoogleEngine(api_key=env.get("GOOGLE_TTS_API_KEY", ""), voice_f="-", voice_m="-", rate=rate, quiet=True)
    voices = [v for v in g.list_voices() if "de-DE" in v.get("languageCodes", [])]
    rank = {t: i for i, t in enumerate(tts.VOICE_TYPE_PREFERENCE)}
    voices.sort(key=lambda v: (rank.get(tts.voice_type(v["name"]), 99), v["name"]))
    for gender, label in (("FEMALE", "Woman"), ("MALE", "Man")):
        chosen = [v for v in voices if v.get("ssmlGender") == gender][: args.max]
        for v in chosen:
            name = v["name"]
            out = OUT / f"{name}.ogg"
            tts.log(f"  {name}")
            g.voices = {"f": name, "m": name}
            try:
                g.render([("f", s) for s in SAMPLE], out)
            except RuntimeError as e:
                tts.log(f"    skipped: {e}")
                continue
            rows.append((label, name, tts.voice_type(name), out.name))

    try:  # Piper, for comparison
        p = tts.PiperEngine()
        for spk, label in (("f", "Woman"), ("m", "Man")):
            p.render([(spk, s) for s in SAMPLE], OUT / f"piper-{spk}.ogg")
            rows.append((label, f"Piper ({label.lower()})", "Piper (current, offline)", f"piper-{spk}.ogg"))
    except Exception as e:  # Piper not installed: fine
        tts.log(f"  (Piper skipped: {e})")

    items = "\n".join(
        f"<tr><td>{html.escape(lbl)}</td><td><b>{html.escape(n)}</b><br><small>{html.escape(t)}</small></td>"
        f"<td><audio controls preload='none' src='{html.escape(f)}'></audio></td></tr>"
        for lbl, n, t, f in rows)
    page = OUT / "index.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8"><title>Voice samples</title>
<style>body{{font:18px system-ui;margin:24px;max-width:900px}}td{{padding:8px;border-bottom:1px solid #ddd}}</style>
<h1>Which voice do you like?</h1>
<p>Each voice says: <i>{html.escape(' '.join(SAMPLE))}</i></p>
<p>Write down one woman's and one man's voice name, then put them in <code>.env</code>:<br>
<code>GOOGLE_TTS_VOICE_F=…</code> and <code>GOOGLE_TTS_VOICE_M=…</code></p>
<table>{items}</table>""", encoding="utf-8")
    tts.log(f"\nOpen: {page}")
    if not args.no_open:
        subprocess.Popen(["xdg-open", str(page)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(str(e))
