import pytest

from app import db, usage
from app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("COACH_TODAY", "2026-11-09")  # a Monday
    monkeypatch.setenv("PAZ_PIN", "4321")
    monkeypatch.setattr("app.server.DATA", tmp_path)
    app = create_app(db_path=tmp_path / "t.db")
    app.config["TESTING"] = True
    return app.test_client()


def finish_placement(c):
    t = c.get("/api/placement").get_json()
    words = next(s for s in t["test"]["sections"] if s["id"] == "words")
    for it in words["items"]:
        c.post("/api/placement/answer", json={"item_id": it["id"], "section": "words", "level": it["level"],
                                              "answer": it["answer"], "correct": True})
    note = "Liebe Frau Becker, meine Tochter ist krank. Sie hat Fieber. Sie kommt morgen wieder. Viele Grüße"
    return c.post("/api/placement/finish", json={"ratings": [{"level": "A2", "value": 2}], "note": note}).get_json()


def test_placement_then_lessons(client):
    assert client.get("/api/state").get_json()["placement"] == "none"
    res = finish_placement(client)
    assert res["levels"]["vocabulary"] == "b1"
    assert res["levels"]["writing"] == "a2"
    assert res["levels"]["speaking"] == "a2"
    s = client.get("/api/state").get_json()
    assert s["placement"] == "done" and s["plan_kind"] == "lesson"


def test_day_plan_and_block_done(client, monkeypatch):
    finish_placement(client)
    today = client.get("/api/today").get_json()
    nw = next(b for b in today["blocks"] if b["type"] == "new_words")
    assert len(nw["words"]) == 5 and nw["topic"] == "school"
    assert all(len(w["distractors"]) == 2 for w in nw["words"])
    lst = next(b for b in today["blocks"] if b["type"] == "listening")
    assert lst["item"]["audio"].endswith(".ogg")
    r = client.post("/api/block/done", json={"key": "listening", "seconds": 700, "score": 1, "max": 2,
                                            "content_id": lst["item_id"]}).get_json()
    assert r["sittings"]["1"]["done"] == 1
    assert r["streak"] == 1  # 10+ minutes counts
    assert client.post("/api/block/done", json={"key": "nope"}).status_code == 400


def test_flashcards_mistakes_first_next_day(client, monkeypatch):
    finish_placement(client)
    today = client.get("/api/today").get_json()
    ids = next(b for b in today["blocks"] if b["type"] == "new_words")["word_ids"]
    client.post("/api/words/learned", json={"word_ids": ids})
    assert client.get("/api/review").get_json()["cards"] == []  # first review is tomorrow

    monkeypatch.setenv("COACH_TODAY", "2026-11-10")
    q = [c["id"] for c in client.get("/api/review").get_json()["cards"]]
    assert sorted(q) == sorted(ids)
    wrong = q[-1]
    for wid in q:
        client.post("/api/review", json={"word_id": wid, "correct": wid != wrong})

    monkeypatch.setenv("COACH_TODAY", "2026-11-11")
    q = [c["id"] for c in client.get("/api/review").get_json()["cards"]]
    assert q == [wrong]  # only the mistake is due, the others wait 2 days

    monkeypatch.setenv("COACH_TODAY", "2026-11-12")
    q = [c["id"] for c in client.get("/api/review").get_json()["cards"]]
    assert q[0] == wrong or wrong not in q  # mistake first (if still due)


def test_next_day_gets_next_words(client, monkeypatch):
    finish_placement(client)
    ids = next(b for b in client.get("/api/today").get_json()["blocks"] if b["type"] == "new_words")["word_ids"]
    client.post("/api/words/learned", json={"word_ids": ids})
    monkeypatch.setenv("COACH_TODAY", "2026-11-10")
    ids2 = next(b for b in client.get("/api/today").get_json()["blocks"] if b["type"] == "new_words")["word_ids"]
    assert not set(ids) & set(ids2)


def test_sunday_rest(client, monkeypatch):
    finish_placement(client)
    monkeypatch.setenv("COACH_TODAY", "2026-11-15")
    assert client.get("/api/state").get_json()["plan_kind"] == "rest"


def test_paz_page_needs_pin(client):
    finish_placement(client)
    assert client.get("/api/paz/summary").status_code == 401
    assert client.post("/api/paz/login", json={"pin": "0000"}).status_code == 401
    assert client.post("/api/paz/login", json={"pin": "4321"}).status_code == 200
    d = client.get("/api/paz/summary").get_json()
    assert d["placement"]["auto"]["writing"] == "a2"
    client.post("/api/paz/override", json={"area": "writing", "level": "b1"})
    d = client.get("/api/paz/summary").get_json()
    assert d["placement"]["levels"]["writing"] == "b1"


def test_hint_flag_shows_on_paz_page(client):
    client.post("/api/hint-flag", json={"item_id": "w-schule", "hint_text": "ትምህርት ቤት"})
    client.post("/api/paz/login", json={"pin": "4321"})
    flags = client.get("/api/paz/summary").get_json()["hint_flags"]
    assert flags[0]["item_id"] == "w-schule"


def test_usage_counter(tmp_path):
    conn = db.connect(tmp_path / "u.db")
    db.init(conn)
    from datetime import date
    d = date(2026, 11, 9)
    usage.record(conn, 1000, 500, d)
    usage.record(conn, 1000, 500, d)
    m = usage.this_month(conn, d)
    assert m["calls"] == 2 and m["input_tokens"] == 2000
    assert usage.can_spend(conn, 25, d)
    assert not usage.can_spend(conn, 0.001, d)
    assert usage.this_month(conn, date(2026, 12, 1))["calls"] == 0


def test_pin_ignores_spaces(client):
    assert client.post("/api/paz/login", json={"pin": " 4321 "}).status_code == 200


def test_picture_flag_shows_on_paz_page_until_replaced(client):
    finish_placement(client)
    w = next(b for b in client.get("/api/today").get_json()["blocks"] if b["type"] == "new_words")["words"][0]
    assert client.post("/api/picture-flag", json={"item_id": w["id"], "label": w["de"], "picture": w["picture"]}).status_code == 200
    client.post("/api/picture-flag", json={"item_id": w["id"], "label": w["de"], "picture": w["picture"]})
    # a picture that is no longer used in the content does not show
    client.post("/api/picture-flag", json={"item_id": "w-old", "label": "alt", "picture": "/media/pictures/arasaac/1.png"})
    assert client.post("/api/picture-flag", json={"picture": "/etc/passwd"}).status_code == 400
    client.post("/api/paz/login", json={"pin": "4321"})
    flags = client.get("/api/paz/summary").get_json()["picture_flags"]
    assert len(flags) == 1 and flags[0]["item_id"] == w["id"] and flags[0]["n"] == 2


def test_daily_goal_and_extra_practice_time(client):
    finish_placement(client)
    s = client.get("/api/state").get_json()
    assert s["goal_minutes"] == 30 and s["minutes_today"] == 0
    r = client.post("/api/time", json={"seconds": 600}).get_json()
    assert r["minutes_today"] == 10
    assert client.post("/api/paz/goal", json={"minutes": 45}).status_code == 401
    client.post("/api/paz/login", json={"pin": "4321"})
    assert client.post("/api/paz/goal", json={"minutes": 2}).status_code == 400
    assert client.post("/api/paz/goal", json={"minutes": 45}).get_json()["goal_minutes"] == 45
    assert client.get("/api/state").get_json()["goal_minutes"] == 45


def test_goal_rises_5_minutes_each_week_up_to_75(client, monkeypatch):
    assert client.get("/api/state").get_json()["goal_minutes"] == 30       # Mon 9 Nov: week 1
    monkeypatch.setenv("COACH_TODAY", "2026-11-15")                          # Sunday, same week
    assert client.get("/api/state").get_json()["goal_minutes"] == 30
    monkeypatch.setenv("COACH_TODAY", "2026-11-16")                          # next Monday
    assert client.get("/api/state").get_json()["goal_minutes"] == 35
    monkeypatch.setenv("COACH_TODAY", "2026-12-21")                          # 6 weeks later
    assert client.get("/api/state").get_json()["goal_minutes"] == 60
    monkeypatch.setenv("COACH_TODAY", "2027-03-01")
    assert client.get("/api/state").get_json()["goal_minutes"] == 75        # capped
