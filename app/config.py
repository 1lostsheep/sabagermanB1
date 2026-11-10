"""Settings from .env (tiny parser, no extra dependency)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> dict:
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip()
            if val[:1] in ('"', "'") and val.count(val[0]) >= 2:
                val = val[1:val.index(val[0], 1)]       # "quoted value" # comment
            else:
                val = val.split(" #", 1)[0].strip()     # value  # comment
            values[key.strip()] = val
    # Real environment variables win over the file
    for key in list(values) + ["LEARNER_NAME", "PAZ_PIN", "ANTHROPIC_API_KEY", "MONTHLY_BUDGET_EUR", "PORT",
                                 "TTS_ENGINE", "GOOGLE_TTS_API_KEY", "GOOGLE_TTS_VOICE_F", "GOOGLE_TTS_VOICE_M", "GOOGLE_TTS_RATE"]:
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def get(key: str, default=None):
    return load_env().get(key) or default
