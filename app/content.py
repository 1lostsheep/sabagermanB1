"""Load and validate content batches (see content/FORMAT.md).

Shared by the server and tools/build_batch.py.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
BATCHES = CONTENT / "batches"
MEDIA = CONTENT / "media"
PLACEMENT = CONTENT / "placement"

SCHEMA_VERSION = 1
KINDS = ["words", "listening", "reading", "letters", "tasks", "speaking"]
LEVELS = {"A1", "A2", "B1"}
ARTICLES = {"der", "die", "das", None}
BLOCK_ROLES = {"who", "verb", "verb_end", "when", "where", "what", "how", "who2", "ask", "not", "other"}
LETTER_ROLES = {"greeting", "reason", "point", "closing", "name"}
LISTEN_KINDS = {"announcement", "phone_message", "conversation", "radio"}
READ_KINDS = {"letter", "sign", "ad", "form", "message", "notice"}
TASK_KINDS = {"read_note", "choose_reply", "fill_form"}
PICTURE_RE = re.compile(r"^[0-9A-F]{4,6}(-[0-9A-F]{4,6})*$")
ID_PREFIX = {"words": "w-", "listening": "l-", "reading": "r-", "letters": "b-", "tasks": "t-", "speaking": "s-"}


def _read(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def batch_ids(root: Path = BATCHES) -> list[str]:
    return sorted(p.name for p in root.iterdir() if (p / "batch.json").exists()) if root.exists() else []


def load_batch(batch_id: str, root: Path = BATCHES) -> dict:
    folder = root / batch_id
    data = {"meta": _read(folder / "batch.json", {})}
    for kind in KINDS:
        items = _read(folder / f"{kind}.json", [])
        for item in items:
            item["batch"] = batch_id
        data[kind] = items
    return data


def load_all(root: Path = BATCHES) -> dict:
    """All batches merged: {'topics': [...], 'words': [...], ...} plus 'by_id'."""
    merged = {"topics": [], **{k: [] for k in KINDS}}
    seen_topics = set()
    for bid in batch_ids(root):
        b = load_batch(bid, root)
        for t in b["meta"].get("topics", []):
            if t["id"] not in seen_topics:
                seen_topics.add(t["id"])
                merged["topics"].append(t)
        for kind in KINDS:
            merged[kind].extend(b[kind])
    merged["by_id"] = {i["id"]: i for kind in KINDS for i in merged[kind]}
    return merged


def load_placement(version: str = "v1", root: Path = PLACEMENT) -> dict:
    return _read(root / version / "placement.json", {})


# ---------- media paths (derived, never stored in JSON) ----------

def audio_rel(batch: str, item_id: str, suffix: str = "") -> str:
    return f"audio/{batch}/{item_id}{suffix}.ogg"


def picture_rel(code: str) -> str:
    return f"pictures/openmoji/{code}.svg"


def _say(obj) -> str:
    return obj.get("say") or obj["de"]


def audio_jobs(batch: dict) -> list[tuple[str, list[tuple[str, str]]]]:
    """[(relative ogg path, [(speaker, text), ...]), ...] for one loaded batch."""
    bid = batch["meta"]["batch_id"]
    jobs = []
    for w in batch["words"]:
        jobs.append((audio_rel(bid, w["id"]), [("m", _say(w))]))
        if w.get("example"):
            jobs.append((audio_rel(bid, w["id"], "-ex"), [("m", _say(w["example"]))]))
    for item in batch["listening"]:
        jobs.append((audio_rel(bid, item["id"]), [(ln.get("speaker", "f"), _say(ln)) for ln in item["lines"]]))
    for item in batch["letters"]:
        jobs.append((audio_rel(bid, item["id"]), [("f", _say(ln)) for ln in item["lines"]]))
    for item in batch["speaking"]:
        jobs.append((audio_rel(bid, item["id"]), [("f", _say(item))]))
    return jobs


def placement_audio_jobs(p: dict) -> list:
    pid = p["id"]
    jobs = []
    for sec in p.get("sections", []):
        if sec["id"] == "words":
            jobs += [(audio_rel(pid, i["id"]), [("m", _say(i))]) for i in sec["items"]]
        elif sec["id"] == "listening":
            jobs += [(audio_rel(pid, i["id"]), [(ln.get("speaker", "f"), _say(ln)) for ln in i["lines"]])
                     for i in sec["items"]]
        elif sec["id"] == "speaking":
            jobs += [(audio_rel(pid, c["id"]), [("f", c["example_de"])]) for c in sec["can_do"]]
    return jobs


def pictures_of_batch(batch: dict) -> set[str]:
    codes = {w["picture"] for w in batch["words"] if w.get("picture")}
    codes |= {t["picture"] for t in batch["meta"].get("topics", []) if t.get("picture")}
    return codes


def pictures_of_placement(p: dict) -> set[str]:
    codes = set()
    for sec in p.get("sections", []):
        if sec["id"] == "words":
            for i in sec["items"]:
                codes |= set(i["options"])
    return codes


# ---------- validation ----------

def _check_questions(where, questions, errors, minimum=1):
    if not isinstance(questions, list) or len(questions) < minimum:
        errors.append(f"{where}: needs at least {minimum} question(s)")
        return
    for n, q in enumerate(questions):
        w = f"{where} question {n + 1}"
        for f in ("q_de", "q_en", "options", "answer"):
            if f not in q:
                errors.append(f"{w}: missing '{f}'")
        opts = q.get("options", [])
        if not 2 <= len(opts) <= 4:
            errors.append(f"{w}: needs 2-4 options")
        if not isinstance(q.get("answer"), int) or not 0 <= q.get("answer", -1) < len(opts):
            errors.append(f"{w}: 'answer' must be an index into options")


def _require(where, obj, fields, errors):
    for f in fields:
        if obj.get(f) in (None, "", []):
            errors.append(f"{where}: missing '{f}'")


def validate_batch(batch: dict, media_root: Path = MEDIA, check_media: bool = True) -> list[str]:
    errors: list[str] = []
    meta = batch.get("meta", {})
    bid = meta.get("batch_id", "?")
    if meta.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"batch.json: schema_version must be {SCHEMA_VERSION}")
    _require("batch.json", meta, ["batch_id", "topics"], errors)
    topics = {t.get("id") for t in meta.get("topics", [])}
    for t in meta.get("topics", []):
        _require(f"topic {t.get('id')}", t, ["id", "title_en", "title_de", "hint_am"], errors)

    ids = set()
    for kind in KINDS:
        for item in batch.get(kind, []):
            iid = item.get("id", "?")
            where = f"{kind}/{iid}"
            if iid in ids:
                errors.append(f"{where}: duplicate id")
            ids.add(iid)
            if not str(iid).startswith(ID_PREFIX[kind]):
                errors.append(f"{where}: id must start with '{ID_PREFIX[kind]}'")
            topic = item.get("topic")
            if kind != "speaking" and topic not in topics:
                errors.append(f"{where}: topic '{topic}' is not in batch.json")
            if kind != "speaking" and item.get("level") not in LEVELS:
                errors.append(f"{where}: level must be A1, A2 or B1")

    for w in batch.get("words", []):
        where = f"words/{w.get('id')}"
        _require(where, w, ["de", "en", "hint_am", "picture"], errors)
        if w.get("article") not in ARTICLES:
            errors.append(f"{where}: article must be der/die/das/null")
        if w.get("article") and not str(w.get("de", "")).startswith(w["article"] + " "):
            errors.append(f"{where}: 'de' should start with the article")
        if w.get("picture") and not PICTURE_RE.match(w["picture"]):
            errors.append(f"{where}: picture must be an OpenMoji hexcode like 1F34E")
        ex = w.get("example")
        if ex:
            _require(where + " example", ex, ["de", "en", "blocks"], errors)
            blocks = ex.get("blocks", [])
            roles = [b[1] for b in blocks if len(b) == 2]
            if any(r not in BLOCK_ROLES for r in roles):
                errors.append(f"{where}: unknown block role in {roles}")
            joined = " ".join(b[0] for b in blocks)
            if re.sub(r"[.!?]$", "", ex.get("de", "")).strip() != joined:
                errors.append(f"{where}: example blocks '{joined}' don't match example.de")
            if "verb" in roles and roles.index("verb") != 1 and roles[0] != "ask" and roles[0] != "verb":
                errors.append(f"{where}: the verb block must be in slot 2")

    for item in batch.get("listening", []):
        where = f"listening/{item.get('id')}"
        _require(where, item, ["title_en", "lines"], errors)
        if item.get("kind") not in LISTEN_KINDS:
            errors.append(f"{where}: kind must be one of {sorted(LISTEN_KINDS)}")
        for ln in item.get("lines", []):
            if ln.get("speaker") not in ("f", "m") or not ln.get("de"):
                errors.append(f"{where}: each line needs speaker f/m and 'de'")
        _check_questions(where, item.get("questions"), errors, minimum=2)

    for item in batch.get("reading", []):
        where = f"reading/{item.get('id')}"
        _require(where, item, ["title_de", "text_de"], errors)
        if item.get("kind") not in READ_KINDS:
            errors.append(f"{where}: kind must be one of {sorted(READ_KINDS)}")
        for g in item.get("glossary", []):
            _require(where + " glossary", g, ["de", "en", "hint_am"], errors)
        _check_questions(where, item.get("questions"), errors)

    for item in batch.get("letters", []):
        where = f"letters/{item.get('id')}"
        _require(where, item, ["task_en", "task_de", "points", "lines", "gaps"], errors)
        lines = item.get("lines", [])
        roles = [ln.get("role") for ln in lines]
        if any(r not in LETTER_ROLES for r in roles):
            errors.append(f"{where}: unknown line role")
        if roles.count("point") != 4 or len(item.get("points", [])) != 4:
            errors.append(f"{where}: needs exactly 4 points and 4 'point' lines")
        for r in ("greeting", "reason", "closing"):
            if r not in roles:
                errors.append(f"{where}: missing a '{r}' line")
        for g in item.get("gaps", []):
            ln = g.get("line")
            if not isinstance(ln, int) or not 0 <= ln < len(lines):
                errors.append(f"{where}: gap line out of range")
                continue
            if g.get("word") not in lines[ln].get("de", ""):
                errors.append(f"{where}: gap word '{g.get('word')}' not in line {ln}")
            if g.get("word") not in g.get("options", []):
                errors.append(f"{where}: gap options must include '{g.get('word')}'")

    for item in batch.get("tasks", []):
        where = f"tasks/{item.get('id')}"
        _require(where, item, ["prompt_en", "material_de"], errors)
        kind = item.get("kind")
        if kind not in TASK_KINDS:
            errors.append(f"{where}: kind must be one of {sorted(TASK_KINDS)}")
        elif kind == "fill_form":
            fields = item.get("fields", [])
            if not fields:
                errors.append(f"{where}: fill_form needs 'fields'")
            for f in fields:
                _require(where + " field", f, ["label_de", "label_en", "answer"], errors)
        else:
            _check_questions(where, item.get("questions"), errors)

    for item in batch.get("speaking", []):
        _require(f"speaking/{item.get('id')}", item, ["de", "en", "hint_am"], errors)

    if check_media and not errors:
        missing = [p for p, _ in audio_jobs(batch) if not (media_root / p).exists()]
        missing += [picture_rel(c) for c in pictures_of_batch(batch) if not (media_root / picture_rel(c)).exists()]
        errors += [f"missing media: {m}" for m in missing]
    return errors


def validate_placement(p: dict, media_root: Path = MEDIA, check_media: bool = True) -> list[str]:
    errors = []
    sections = {s.get("id"): s for s in p.get("sections", [])}
    for need in ("words", "listening", "reading", "speaking", "writing"):
        if need not in sections:
            errors.append(f"placement: missing section '{need}'")
    for sec_id in ("words", "listening", "reading"):
        for item in sections.get(sec_id, {}).get("items", []):
            where = f"placement/{sec_id}/{item.get('id')}"
            if item.get("level") not in LEVELS:
                errors.append(f"{where}: level must be A1/A2/B1")
            if sec_id == "words":
                if not 2 <= len(item.get("options", [])) <= 4 or not 0 <= item.get("answer", -1) < len(item.get("options", [])):
                    errors.append(f"{where}: needs 2-4 picture options and a valid answer")
            else:
                _check_questions(where, item.get("questions"), errors)
    for c in sections.get("speaking", {}).get("can_do", []):
        _require(f"placement/speaking/{c.get('id')}", c, ["level", "en", "example_de"], errors)
    _require("placement/writing", sections.get("writing", {}), ["task_en", "task_de", "keywords"], errors)
    if check_media and not errors:
        missing = [path for path, _ in placement_audio_jobs(p) if not (media_root / path).exists()]
        missing += [picture_rel(c) for c in pictures_of_placement(p) if not (media_root / picture_rel(c)).exists()]
        errors += [f"missing media: {m}" for m in missing]
    return errors
