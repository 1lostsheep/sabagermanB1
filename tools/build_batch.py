#!/usr/bin/env python3
"""Validate a content batch, fetch its pictures and render its audio.

    .venv/bin/python tools/build_batch.py 2026-11          # one batch (+ placement)
    .venv/bin/python tools/build_batch.py all              # every batch
    .venv/bin/python tools/build_batch.py 2026-11 --check  # validate only, no downloads
    .venv/bin/python tools/build_batch.py --voices-only    # just download the Piper voices
    add --force to re-render audio that already exists

Safe to re-run: only missing files are created.
Needs: pip install -r requirements-content.txt, and ffmpeg.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import content as C  # noqa: E402

VOICE_DIR = ROOT / "tools" / "voices"
OPENMOJI_TAG = "15.1.0"
OPENMOJI_URL = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/{tag}/color/svg/{code}.svg"
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE"
GH = "https://github.com/rhasspy/piper/releases/download/v0.0.2"
# speaker -> list of (name, kind, url) to try in order. Hugging Face has the better
# 'medium' voice; GitHub has older 'low' voices as a fallback.
VOICES = {
    "m": [("de_DE-thorsten-medium", "file", f"{HF}/thorsten/medium/de_DE-thorsten-medium.onnx"),
          ("de-thorsten-low", "tar", f"{GH}/voice-de-thorsten-low.tar.gz")],
    "f": [("de_DE-kerstin-low", "file", f"{HF}/kerstin/low/de_DE-kerstin-low.onnx"),
          ("de-kerstin-low", "tar", f"{GH}/voice-de-kerstin-low.tar.gz")],
}
LENGTH_SCALE = 1.1      # a little slower than normal: friendlier for a learner
LINE_PAUSE_S = 0.7


def log(msg):
    print(msg, flush=True)


def _download(url, dest: Path):
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def ensure_voice(speaker: str) -> Path:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for name, _, _ in VOICES[speaker]:
        if (VOICE_DIR / f"{name}.onnx").exists():
            return VOICE_DIR / f"{name}.onnx"
    for name, kind, url in VOICES[speaker]:
        try:
            log(f"  downloading voice {name} ...")
            if kind == "file":
                _download(url, VOICE_DIR / f"{name}.onnx")
                _download(url + ".json", VOICE_DIR / f"{name}.onnx.json")
            else:
                import tarfile
                with tempfile.TemporaryDirectory() as tmp:
                    tgz = Path(tmp) / "v.tgz"
                    _download(url, tgz)
                    with tarfile.open(tgz) as t:
                        for m in t.getmembers():
                            if m.name.endswith((".onnx", ".onnx.json")):
                                m.name = Path(m.name).name
                                t.extract(m, VOICE_DIR, filter="data")
            return VOICE_DIR / f"{name}.onnx"
        except Exception as e:  # try the next source
            log(f"  (could not get {name}: {e})")
            for ext in (".onnx", ".onnx.json"):
                (VOICE_DIR / f"{name}{ext}").unlink(missing_ok=True)
    sys.exit(f"No voice available for speaker '{speaker}'. Check the internet connection.")


class Speaker:
    def __init__(self):
        from piper import PiperVoice, SynthesisConfig
        self.voices = {s: PiperVoice.load(ensure_voice(s)) for s in VOICES}
        self.cfg = SynthesisConfig(length_scale=LENGTH_SCALE)

    def render(self, lines, out: Path):
        """lines: [(speaker, text)]. Writes an .ogg (Opus) file."""
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for n, (spk, text) in enumerate(lines):
                p = Path(tmp) / f"{n}.wav"
                with wave.open(str(p), "wb") as wf:
                    self.voices[spk].synthesize_wav(text, wf, syn_config=self.cfg)
                parts.append(p)
            # join lines with a short pause, then encode to Opus (small files)
            inputs, filters = [], []
            for n, p in enumerate(parts):
                inputs += ["-i", str(p)]
                filters.append(f"[{n}:a]aresample=24000,aformat=channel_layouts=mono,apad=pad_dur={LINE_PAUSE_S}[a{n}]")
            concat = "".join(f"[a{n}]" for n in range(len(parts)))
            graph = ";".join(filters) + f";{concat}concat=n={len(parts)}:v=0:a=1,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse[out]"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph,
                            "-map", "[out]", "-c:a", "libopus", "-b:a", "32k", str(out)], check=True)


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


def render_audio(jobs, force=False):
    todo = [(p, lines) for p, lines in jobs if force or not (C.MEDIA / p).exists()]
    if not todo:
        return 0
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is missing: sudo apt install ffmpeg")
    spk = Speaker()
    for n, (p, lines) in enumerate(todo, 1):
        log(f"  [{n}/{len(todo)}] {p}")
        spk.render(lines, C.MEDIA / p)
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
    ap.add_argument("batch", nargs="?", help="batch id like 2026-11, or 'all'")
    ap.add_argument("--check", action="store_true", help="validate only (also checks media exists)")
    ap.add_argument("--force", action="store_true", help="re-render audio and re-fetch pictures")
    ap.add_argument("--voices-only", action="store_true")
    ap.add_argument("--no-placement", action="store_true")
    args = ap.parse_args()

    if args.voices_only:
        for s in VOICES:
            log(f"voice {s}: {ensure_voice(s).name}")
        return
    if not args.batch:
        ap.error("give a batch id (e.g. 2026-11) or 'all'")

    ids = C.batch_ids() if args.batch == "all" else [args.batch]
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
            n = render_audio(C.audio_jobs(batch), args.force)
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
                    render_audio(C.placement_audio_jobs(p), args.force)
                ok &= report("placement (media)", C.validate_placement(p, check_media=True))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
