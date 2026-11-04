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
            values[key.strip()] = val.strip().strip('"').strip("'")
    # Real environment variables win over the file
    for key in list(values) + ["LEARNER_NAME", "PAZ_PIN", "ANTHROPIC_API_KEY", "MONTHLY_BUDGET_EUR", "PORT"]:
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def get(key: str, default=None):
    return load_env().get(key) or default
