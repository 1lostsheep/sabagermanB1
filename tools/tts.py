"""Text-to-speech engines for lesson audio (used on Paz's side only, never by the app).

Two engines, chosen with TTS_ENGINE in .env:
- "google": Google Cloud Text-to-Speech. Natural modern voices. Needs GOOGLE_TTS_API_KEY.
            Only the German lesson text is sent to Google, never anything about Saba.
- "piper":  free, offline, runs on the laptop. Sounds more robotic. The fallback.

Both write one .ogg (Opus) file per job. A job is a list of (speaker, text) lines,
where speaker is "f" (woman) or "m" (man); several lines are joined with a short pause.
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import config  # noqa: E402

LINE_PAUSE_S = 0.7

# ---------------------------------------------------------------- shared


def log(msg):
    print(msg, flush=True)


def download(url, dest: Path):
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def join_to_ogg(wavs, out: Path):
    """Join wav files with a short pause and encode to Opus (small files)."""
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is missing: sudo apt install ffmpeg")
    out.parent.mkdir(parents=True, exist_ok=True)
    inputs, filters = [], []
    for n, p in enumerate(wavs):
        inputs += ["-i", str(p)]
        pad = f",apad=pad_dur={LINE_PAUSE_S}" if n < len(wavs) - 1 else ""
        filters.append(f"[{n}:a]aresample=24000,aformat=channel_layouts=mono{pad}[a{n}]")
    concat = "".join(f"[a{n}]" for n in range(len(wavs)))
    graph = ";".join(filters) + f";{concat}concat=n={len(wavs)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph,
                    "-map", "[out]", "-c:a", "libopus", "-b:a", "32k", str(out)], check=True)


class Engine:
    name = "?"

    def synth_wav(self, speaker: str, text: str, path: Path):
        raise NotImplementedError

    def render(self, lines, out: Path):
        """lines: [(speaker, text)] -> one .ogg file."""
        with tempfile.TemporaryDirectory() as tmp:
            wavs = []
            for n, (spk, text) in enumerate(lines):
                p = Path(tmp) / f"{n}.wav"
                self.synth_wav(spk, text, p)
                wavs.append(p)
            join_to_ogg(wavs, out)


# ---------------------------------------------------------------- Google

GOOGLE_API = "https://texttospeech.googleapis.com/v1"
# Most natural first. Any of these sounds far better than Piper.
VOICE_TYPE_PREFERENCE = ["Chirp3-HD", "Chirp-HD", "Neural2", "Wavenet", "Standard"]
GENDER = {"f": "FEMALE", "m": "MALE"}


def voice_type(name: str) -> str:
    """'de-DE-Chirp3-HD-Aoede' -> 'Chirp3-HD', 'de-DE-Neural2-C' -> 'Neural2'."""
    for t in VOICE_TYPE_PREFERENCE:
        if f"-{t}-" in name:
            return t
    return "other"


def pick_voice(voices, gender: str) -> str | None:
    """Best German voice of the gender ('FEMALE'/'MALE'), by VOICE_TYPE_PREFERENCE."""
    rank = {t: i for i, t in enumerate(VOICE_TYPE_PREFERENCE)}
    cands = [v for v in voices if "de-DE" in v.get("languageCodes", []) and v.get("ssmlGender") == gender]
    cands.sort(key=lambda v: (rank.get(voice_type(v["name"]), 99), v["name"]))
    return cands[0]["name"] if cands else None


def synth_request(text: str, voice: str, rate: float | None) -> dict:
    audio = {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}
    if rate:
        audio["speakingRate"] = rate
    return {"input": {"text": text}, "voice": {"languageCode": "de-DE", "name": voice}, "audioConfig": audio}


class GoogleEngine(Engine):
    name = "google"

    def __init__(self, api_key: str = "", voice_f: str = "", voice_m: str = "", rate: float = 0.92, quiet=False):
        self.api_key = api_key
        self.rate = rate
        self.voices = {"f": voice_f, "m": voice_m}
        if not voice_f or not voice_m:
            available = self.list_voices()
            for spk in ("f", "m"):
                self.voices[spk] = self.voices[spk] or pick_voice(available, GENDER[spk])
        if not quiet:
            log(f"  Google voices: woman = {self.voices['f']}, man = {self.voices['m']}, speed = {rate}")

    def _call(self, method, path, body=None):
        req = urllib.request.Request(f"{GOOGLE_API}/{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-Goog-Api-Key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = " ".join(e.read().decode(errors="replace").split())[:400]
            hint = ""
            if e.code in (401, 403):
                hint = ("\n  -> Check GOOGLE_TTS_API_KEY in .env, and that the 'Cloud Text-to-Speech API'"
                        " is enabled for your Google Cloud project.")
            raise RuntimeError(f"Google TTS error {e.code}: {detail}{hint}") from None

    def list_voices(self):
        return self._call("GET", "voices?languageCode=de-DE").get("voices", [])

    def synth_wav(self, speaker, text, path: Path):
        voice = self.voices[speaker]
        try:
            res = self._call("POST", "text:synthesize", synth_request(text, voice, self.rate))
        except RuntimeError as e:
            # some voice types don't accept a speed setting: try again at normal speed
            if "speaking" not in str(e).lower() and "rate" not in str(e).lower():
                raise
            res = self._call("POST", "text:synthesize", synth_request(text, voice, None))
        Path(path).write_bytes(base64.b64decode(res["audioContent"]))  # LINEAR16 = wav with header


# ---------------------------------------------------------------- Piper

VOICE_DIR = ROOT / "tools" / "voices"
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE"
GH = "https://github.com/rhasspy/piper/releases/download/v0.0.2"
# speaker -> (name, kind, url) to try in order: Hugging Face 'medium' first, old GitHub 'low' as fallback
PIPER_VOICES = {
    "m": [("de_DE-thorsten-medium", "file", f"{HF}/thorsten/medium/de_DE-thorsten-medium.onnx"),
          ("de-thorsten-low", "tar", f"{GH}/voice-de-thorsten-low.tar.gz")],
    "f": [("de_DE-kerstin-low", "file", f"{HF}/kerstin/low/de_DE-kerstin-low.onnx"),
          ("de-kerstin-low", "tar", f"{GH}/voice-de-kerstin-low.tar.gz")],
}
PIPER_LENGTH_SCALE = 1.1  # a little slower than normal


def ensure_piper_voice(speaker: str) -> Path:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for name, _, _ in PIPER_VOICES[speaker]:
        if (VOICE_DIR / f"{name}.onnx").exists():
            return VOICE_DIR / f"{name}.onnx"
    for name, kind, url in PIPER_VOICES[speaker]:
        try:
            log(f"  downloading voice {name} ...")
            if kind == "file":
                download(url, VOICE_DIR / f"{name}.onnx")
                download(url + ".json", VOICE_DIR / f"{name}.onnx.json")
            else:
                import tarfile
                with tempfile.TemporaryDirectory() as tmp:
                    tgz = Path(tmp) / "v.tgz"
                    download(url, tgz)
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
    sys.exit(f"No Piper voice available for speaker '{speaker}'. Check the internet connection.")


class PiperEngine(Engine):
    name = "piper"

    def __init__(self):
        import logging
        logging.getLogger("piper").setLevel(logging.ERROR)
        from piper import PiperVoice, SynthesisConfig
        self.voices = {s: PiperVoice.load(ensure_piper_voice(s)) for s in PIPER_VOICES}
        self.cfg = SynthesisConfig(length_scale=PIPER_LENGTH_SCALE)

    def synth_wav(self, speaker, text, path: Path):
        with wave.open(str(path), "wb") as wf:
            self.voices[speaker].synthesize_wav(text, wf, syn_config=self.cfg)


# ---------------------------------------------------------------- choose

def make_engine(name: str | None = None) -> Engine:
    """The engine from .env (TTS_ENGINE), or the one named."""
    env = config.load_env()
    name = (name or env.get("TTS_ENGINE") or "piper").lower()
    if name == "google":
        key = env.get("GOOGLE_TTS_API_KEY", "")
        if not key:
            log("  (GOOGLE_TTS_API_KEY is empty in .env; trying without a key)")
        return GoogleEngine(api_key=key, voice_f=env.get("GOOGLE_TTS_VOICE_F", ""),
                            voice_m=env.get("GOOGLE_TTS_VOICE_M", ""),
                            rate=float(env.get("GOOGLE_TTS_RATE") or 0.92))
    if name == "piper":
        return PiperEngine()
    sys.exit(f"Unknown TTS_ENGINE '{name}'. Use google or piper.")
