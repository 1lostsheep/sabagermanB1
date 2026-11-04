from datetime import date, timedelta

from app import lesson_plan as lp

MON = date(2026, 11, 9)


def content():
    words = [{"id": f"w-s{i}", "topic": "school"} for i in range(7)]
    words += [{"id": f"w-d{i}", "topic": "doctor"} for i in range(3)]
    return {
        "topics": [{"id": "school"}, {"id": "doctor"}],
        "words": words,
        "listening": [{"id": "l-d", "topic": "doctor"}, {"id": "l-s", "topic": "school"}],
        "reading": [{"id": "r-s", "topic": "school"}],
        "letters": [{"id": "b-s", "topic": "school"}],
        "tasks": [{"id": "t-s", "topic": "school"}, {"id": "t-d", "topic": "doctor"}],
    }


def keys(plan):
    return [b["key"] for b in plan["blocks"]]


def test_weekday_has_two_sittings_and_max_5_words():
    p = lp.build_day_plan(MON, content(), set(), {}, due_count=3)
    assert p["kind"] == "lesson"
    nw = next(b for b in p["blocks"] if b["key"] == "new_words")
    assert len(nw["word_ids"]) == 5 and nw["topic"] == "school"
    assert {b["sitting"] for b in p["blocks"]} == {1, 2}
    assert keys(p)[:3] == ["review", "new_words", "listening"]
    assert next(b for b in p["blocks"] if b["key"] == "speaking")["coming_soon"]


def test_topic_items_preferred():
    p = lp.build_day_plan(MON, content(), set(), {}, due_count=0)
    listening = next(b for b in p["blocks"] if b["key"] == "listening")
    assert listening["item_id"] == "l-s"
    assert "review" not in keys(p)  # nothing due yet on day 1


def test_words_never_mix_topics():
    c = content()
    introduced = {f"w-s{i}" for i in range(5)}
    p = lp.build_day_plan(MON, c, introduced, {}, 0)
    assert next(b for b in p["blocks"] if b["key"] == "new_words")["word_ids"] == ["w-s5", "w-s6"]


def test_writing_and_reading_alternate_on_weekdays():
    kinds = []
    d = MON
    while len(kinds) < 6:
        if d.weekday() < 5:
            p = lp.build_day_plan(d, content(), set(), {}, 0)
            kinds.append("writing" if "writing" in keys(p) else "reading")
        d += timedelta(days=1)
    assert all(a != b for a, b in zip(kinds, kinds[1:]))  # includes Fri -> Mon


def test_saturday_is_mini_test_and_sunday_rest():
    sat, sun = MON + timedelta(days=5), MON + timedelta(days=6)
    p = lp.build_day_plan(sat, content(), set(), {}, 2, week_words=["w-s0", "w-s1"])
    assert p["kind"] == "weekly_test" and keys(p) == ["review", "weekly_test", "writing"]
    p = lp.build_day_plan(sun, content(), set(), {}, 2)
    assert p["kind"] == "rest" and p["blocks"][0]["optional"]
    assert lp.build_day_plan(sun, content(), set(), {}, 0)["blocks"] == []


def test_pick_item_repeats_oldest_when_all_used():
    items = [{"id": "a"}, {"id": "b"}]
    assert lp.pick_item(items, {"a": "2026-11-02", "b": "2026-11-01"}) == "b"
    assert lp.pick_item(items, {"a": "2026-11-02"}) == "b"
    assert lp.pick_item([], {}) is None


def test_no_new_words_left():
    c = content()
    p = lp.build_day_plan(MON, c, {w["id"] for w in c["words"]}, {}, 5)
    assert "new_words" not in keys(p)


def test_words_of_last_week():
    intro = {"a": MON - timedelta(days=7), "b": MON - timedelta(days=6), "c": MON - timedelta(days=1), "d": MON}
    assert lp.words_of_last_week(intro, MON) == ["b", "c"]
