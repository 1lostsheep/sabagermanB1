#!/usr/bin/env python3
"""Validate a content batch, fetch its pictures and render its audio.

    .venv/bin/python tools/build_batch.py 2026-11          # one batch (+ placement)
    .venv/bin/python tools/build_batch.py all              # every batch
    .venv/bin/python tools/build_batch.py 2026-11 --check  # validate only, no downloads
    .venv/bin/python tools/build_batch.py --voices-only    # just download the Piper voices
    add --force to re-render audio that already exists
    add --engine google|piper to override TTS_ENGINE from .env

Voices: TTS_ENGINE in .env picks Google (natural, needs GOOGLE_TTS_API_KEY) or Piper
(free, offline). See tools/tts.py and tools/voice_samples.py.

Safe to re-run: only missing files are created.
Needs: ffmpeg; for Piper also pip install -r requirements-content.txt.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import content as C  # noqa: E402
from tools import tts  # noqa: E402
from tools.tts import download as _download, log  # noqa: E402

OPENMOJI_TAG = "15.1.0"
OPENMOJI_URL = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/{tag}/color/svg/{code}.svg"


def fetch_pictures(codes, force=False):
    got = 0
    for code in sorted(codes):
        dest = C.MEDIA / C.picture_rel(code)
        if dest.exists() and not force:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = OPENMOJI_URL.format(tag=OPENMOJI_TAG, code=code)
        try:
            _download(url, dest)
            got += 1
        except Exception as e:
            log(f"  ! picture {code} not found ({e}). Pick another hexcode on openmoji.org")
            dest.unlink(missing_ok=True)
    return got


def render_audio(jobs, force=False, engine_name=None):
    todo = [(p, lines) for p, lines in jobs if force or not (C.MEDIA / p).exists()]
    if not todo:
        return 0
    engine = tts.make_engine(engine_name)
    for n, (p, lines) in enumerate(todo, 1):
        log(f"  [{n}/{len(todo)}] {p}")
        engine.render(lines, C.MEDIA / p)
    return len(todo)


def report(name, errors) -> bool:
    if errors:
        log(f"✗ {name}: {len(errors)} problem(s)")
        for e in errors[:50]:
            log(f"   - {e}")
        return False
    log(f"✓ {name} is valid")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", nargs="?", help="batch id like 2026-11, 'all', or 'placement'")
    ap.add_argument("--check", action="store_true", help="validate only (also checks media exists)")
    ap.add_argument("--force", action="store_true", help="re-render audio and re-fetch pictures")
    ap.add_argument("--voices-only", action="store_true", help="download the Piper voices and stop")
    ap.add_argument("--engine", choices=["google", "piper"], help="override TTS_ENGINE from .env")
    ap.add_argument("--no-placement", action="store_true")
    args = ap.parse_args()

    if args.voices_only:
        for spk in tts.PIPER_VOICES:
            log(f"voice {spk}: {tts.ensure_piper_voice(spk).name}")
        return
    if not args.batch:
        ap.error("give a batch id (e.g. 2026-11) or 'all'")

    ids = {"all": C.batch_ids(), "placement": []}.get(args.batch, [args.batch])
    ok = True
    for bid in ids:
        if not (C.BATCHES / bid / "batch.json").exists():
            sys.exit(f"No batch at content/batches/{bid}/batch.json")
        batch = C.load_batch(bid)
        errors = C.validate_batch(batch, check_media=False)
        if not report(f"batch {bid} (JSON)", errors):
            ok = False
            continue
        if not args.check:
            n = fetch_pictures(C.pictures_of_batch(batch), args.force)
            log(f"  pictures fetched: {n}")
            n = render_audio(C.audio_jobs(batch), args.force, args.engine)
            log(f"  audio rendered: {n}")
        ok &= report(f"batch {bid} (media)", C.validate_batch(batch, check_media=True))

    # all batches together: ids must be unique across months
    all_ids = {}
    for bid in C.batch_ids():
        b = C.load_batch(bid)
        for kind in C.KINDS:
            for item in b[kind]:
                if item["id"] in all_ids and all_ids[item["id"]] != bid:
                    log(f"✗ id {item['id']} is used in {all_ids[item['id']]} and {bid}")
                    ok = False
                all_ids[item["id"]] = bid

    if not args.no_placement:
        p = C.load_placement()
        if p:
            if not report("placement (JSON)", C.validate_placement(p, check_media=False)):
                ok = False
            else:
                if not args.check:
                    fetch_pictures(C.pictures_of_placement(p), args.force)
                    render_audio(C.placement_audio_jobs(p), args.force, args.engine)
                ok &= report("placement (media)", C.validate_placement(p, check_media=True))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(str(e))
