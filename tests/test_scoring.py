import pytest

from app import scoring


@pytest.mark.parametrize("items,level", [
    ([("A1", 1), ("A2", 0), ("A2", 0)], "below_a2"),          # 33%
    ([("A1", 1), ("A1", 1), ("A2", 1), ("A2", 0), ("A2", 0)], "a2"),  # exactly 60%
    ([("A1", 1), ("A2", 1), ("B1", 1), ("B1", 0)], "a2"),     # B1 50%
    ([("A1", 1), ("A2", 1), ("B1", 1), ("B1", 1), ("B1", 0)], "b1"),  # B1 66%
    ([("A1", 0), ("A2", 0), ("B1", 1), ("B1", 1)], "below_a2"),  # B1 alone is not enough
    ([("A1", 1)], "a2"),                                       # no B1 items -> max a2
    ([], "below_a2"),
])
def test_level_from_items(items, level):
    assert scoring.level_from_items(items) == level


def test_self_rating():
    assert scoring.level_from_self_rating([("A2", 2), ("A2", 1), ("B1", 0)]) == "a2"
    assert scoring.level_from_self_rating([("A2", 2), ("B1", 2)]) == "b1"
    assert scoring.level_from_self_rating([("A2", 1), ("B1", 2)]) == "below_a2"


def test_note_checks_good_note():
    text = "Liebe Frau Weber, mein Sohn ist heute krank. Er hat Fieber. Er kommt morgen wieder in die Schule. Viele Grüße, Saba"
    r = scoring.note_checks(text, keywords=["krank"])
    assert r["greeting"] and r["closing"] and r["three_sentences"] and r["topic"]
    assert r["score"] == 4 and r["level"] == "a2"


def test_note_checks_short_note():
    r = scoring.note_checks("Hallo. Krank.", keywords=["krank"])
    assert r["score"] < 4 and r["level"] == "below_a2"


@pytest.mark.parametrize("given,expected,ok", [
    ("  Müller ", "Müller", True),
    ("Mueller", "Müller", True),
    ("strasse 5", "Straße 5", True),
    ("12.03.1990", ["12.03.1990", "12.3.1990"], True),
    ("Berlin", "Bonn", False),
])
def test_answer_matches(given, expected, ok):
    assert scoring.answer_matches(given, expected) is ok


def test_final_levels_override_wins():
    out = scoring.final_levels({"speaking": "a2", "writing": "below_a2"}, {"writing": "a2", "x": "bogus"})
    assert out["speaking"] == "a2" and out["writing"] == "a2" and out["reading"] == "below_a2"


@pytest.mark.parametrize("levels,ok", [
    ({"speaking": "b1", "writing": "b1", "listening_reading": "a2"}, True),
    ({"speaking": "b1", "writing": "a2", "listening_reading": "b1"}, True),
    ({"speaking": "a2", "writing": "b1", "listening_reading": "b1"}, False),   # speaking must be B1
    ({"speaking": "b1", "writing": "below_a2", "listening_reading": "b1"}, False),  # new 2026 rule
    ({"speaking": "b1", "writing": "b1", "listening": "b1", "reading": "below_a2"}, False),  # safe side
])
def test_exam_outlook(levels, ok):
    assert scoring.exam_outlook(levels) is ok
