"""Scoring and level mapping for DTZ areas.

Levels are: 'below_a2', 'a2', 'b1'.
"""
import re
import unicodedata

LEVELS = ["below_a2", "a2", "b1"]
AREAS = ["speaking", "listening", "reading", "writing", "listening_reading"]
PASS_RATIO = 0.6


def level_from_items(items) -> str:
    """items: iterable of (level_tag, correct) where level_tag is 'A1'|'A2'|'B1'.

    below_a2: under 60% of the A1+A2 items right
    a2:       60%+ of A1+A2 items, but under 60% of B1 items (or no B1 items)
    b1:       60%+ of A1+A2 items and 60%+ of B1 items
    """
    base = [bool(c) for tag, c in items if tag.upper() in ("A1", "A2")]
    b1 = [bool(c) for tag, c in items if tag.upper() == "B1"]
    if not base or sum(base) / len(base) < PASS_RATIO:
        return "below_a2"
    if b1 and sum(b1) / len(b1) >= PASS_RATIO:
        return "b1"
    return "a2"


def level_from_self_rating(ratings) -> str:
    """ratings: iterable of (level_tag, value) with value 2='I can', 1='a little', 0='not yet'."""
    def avg(tag):
        vals = [v for t, v in ratings if t.upper() == tag]
        return sum(vals) / len(vals) if vals else 0
    a2, b1 = avg("A2"), avg("B1")
    if a2 >= 1.5 and b1 >= 1.5:
        return "b1"
    if a2 >= 1.5:
        return "a2"
    return "below_a2"


GREETINGS = ("liebe", "lieber", "hallo", "sehr geehrte", "guten tag", "hi ")
CLOSINGS = ("viele grüße", "liebe grüße", "mit freundlichen grüßen", "freundliche grüße",
            "gruß", "grüße", "tschüss", "bis bald", "danke")


def sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?\n]+", text)
    return [p for p in (s.strip() for s in parts) if len(p.split()) >= 2]


def note_checks(text: str, keywords=()) -> dict:
    """Simple structure checks for a short note. Not a real grade: AI marks letters in Phase 2.

    Returns {"greeting","closing","three_sentences","topic"} booleans, plus
    "score" (0-4), "words" and a provisional "level" (never above a2).
    """
    low = " " + unicodedata.normalize("NFC", text).lower() + " "
    checks = {
        "greeting": any(g in low for g in GREETINGS),
        "closing": any(c in low for c in CLOSINGS),
        "three_sentences": len(sentences(text)) >= 3,
        "topic": (not keywords) or any(k.lower() in low for k in keywords),
    }
    score = sum(checks.values())
    words = len(text.split())
    level = "a2" if score == 4 and words >= 15 else "below_a2"
    return {**checks, "score": score, "words": words, "level": level}


def normalize_answer(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").strip().lower()
    s = s.replace("ae", "ä").replace("oe", "ö").replace("ue", "ü").replace("ss", "ß")
    s = re.sub(r"[\s]+", " ", s)
    return s.strip(" .,!?;:")


def answer_matches(given: str, expected) -> bool:
    """Gentle check for typed answers. `expected` is a string or a list of accepted answers."""
    options = [expected] if isinstance(expected, str) else list(expected)
    g = normalize_answer(given)
    return any(g == normalize_answer(o) for o in options)


def final_levels(auto: dict | None, override: dict | None) -> dict:
    """Paz's manual level wins over the automatic one, per area."""
    out = {a: "below_a2" for a in AREAS}
    out.update({k: v for k, v in (auto or {}).items() if v in LEVELS})
    out.update({k: v for k, v in (override or {}).items() if v in LEVELS})
    return out


def exam_outlook(levels: dict) -> bool:
    """DTZ rule since 1 Nov 2026: B1 Speaking + B1 in one other area + at least A2 in the third.

    The DTZ scores Listening and Reading together as one area ('Hören/Lesen'). We use
    levels['listening_reading'] (computed from all their items together) when present,
    otherwise the lower of the two, to stay on the safe side.
    """
    rank = {lv: i for i, lv in enumerate(LEVELS)}
    sp = rank[levels.get("speaking", "below_a2")]
    if levels.get("listening_reading") in rank:
        hl = rank[levels["listening_reading"]]
    else:
        hl = min(rank[levels.get("listening", "below_a2")], rank[levels.get("reading", "below_a2")])
    wr = rank[levels.get("writing", "below_a2")]
    if sp < 2:
        return False
    others = sorted([hl, wr], reverse=True)
    return others[0] >= 2 and others[1] >= 1
