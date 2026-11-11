"""Flask server: JSON API under /api, the web app at /, media at /media.

Only listens on 127.0.0.1. All of Saba's data stays in data/coach.db.
"""
import json
import os
import random
import secrets
import time
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, abort, g, jsonify, request, send_from_directory, session

from . import config, db, lesson_plan, scoring, srs, streak, usage
from . import content as C

ROOT = config.ROOT
WEB = ROOT / "web"
DATA = ROOT / "data"


def today() -> date:
    """Local date. COACH_TODAY=YYYY-MM-DD fakes the date (testing only)."""
    fake = os.environ.get("COACH_TODAY")
    return date.fromisoformat(fake) if fake else date.today()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _card_from_row(r) -> srs.Card:
    return srs.Card(word_id=r["word_id"], box=r["box"], due_date=date.fromisoformat(r["due_date"]),
                    introduced_on=date.fromisoformat(r["introduced_on"]), reps=r["reps"], lapses=r["lapses"],
                    last_result=r["last_result"],
                    last_seen=date.fromisoformat(r["last_seen"]) if r["last_seen"] else None)


def _save_card(conn, c: srs.Card):
    conn.execute(
        "INSERT INTO card (word_id, box, due_date, reps, lapses, last_result, last_seen, introduced_on) "
        "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(word_id) DO UPDATE SET box=excluded.box, due_date=excluded.due_date, "
        "reps=excluded.reps, lapses=excluded.lapses, last_result=excluded.last_result, last_seen=excluded.last_seen",
        (c.word_id, c.box, c.due_date.isoformat(), c.reps, c.lapses, c.last_result,
         c.last_seen.isoformat() if c.last_seen else None, c.introduced_on.isoformat()))


def create_app(db_path=None, content_root=None):
    app = Flask(__name__, static_folder=None)
    app.config["DB_PATH"] = db_path
    app.config["CONTENT_ROOT"] = content_root or C.BATCHES
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False

    conn = db.connect(db_path)
    db.init(conn)
    secret = db.get_setting(conn, "secret_key")
    if not secret:
        secret = secrets.token_hex(32)
        db.set_setting(conn, "secret_key", secret)
    if not db.get_setting(conn, "start_date"):
        db.set_setting(conn, "start_date", today().isoformat())
    conn.close()
    app.secret_key = secret

    _cache = {}

    def content():
        """All batches, reloaded when a file changes (Paz adds a new month)."""
        root = app.config["CONTENT_ROOT"]
        stamp = max((p.stat().st_mtime for p in root.rglob("*.json")), default=0)
        if _cache.get("stamp") != stamp:
            _cache["data"] = C.load_all(root)
            _cache["stamp"] = stamp
        return _cache["data"]

    def conn():
        if "db" not in g:
            g.db = db.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def _close(_exc):
        c = g.pop("db", None)
        if c is not None:
            c.close()

    def body():
        return request.get_json(silent=True) or {}

    # ---------------- helpers ----------------

    def all_cards():
        return [_card_from_row(r) for r in conn().execute("SELECT * FROM card")]

    def active_days():
        rows = conn().execute("SELECT day, seconds, done_json, plan_json FROM lesson_day").fetchall()
        out = set()
        for r in rows:
            done = json.loads(r["done_json"])
            blocks = json.loads(r["plan_json"]).get("blocks", [])
            sittings_done = 0
            for s in (1, 2):
                keys = [b["key"] for b in blocks if b["sitting"] == s and not b.get("optional")]
                if keys and all(k in done for k in keys):
                    sittings_done += 1
            if streak.is_active_day(r["seconds"], sittings_done):
                out.add(date.fromisoformat(r["day"]))
        return out

    def word_view(w):
        """What the browser needs for one word."""
        return {
            "id": w["id"], "de": w["de"], "en": w["en"], "hint_am": w.get("hint_am"),
            "article": w.get("article"), "plural": w.get("plural"), "topic": w.get("topic"),
            "picture": "/media/" + C.picture_rel(w["picture"]),
            "audio": "/media/" + C.audio_rel(w["batch"], w["id"]),
            "example": ({**w["example"], "audio": "/media/" + C.audio_rel(w["batch"], w["id"], "-ex")}
                        if w.get("example") else None),
        }

    def with_distractors(word_ids, n=2):
        """Each word plus `n` other words for multiple choice (same topic first)."""
        cont = content()
        words = [w for w in cont["words"]]
        out = []
        for wid in word_ids:
            w = cont["by_id"].get(wid)
            if not w:
                continue
            others = [o for o in words if o["id"] != wid and o["picture"] != w["picture"]]
            same = [o for o in others if o["topic"] == w["topic"]]
            rest = [o for o in others if o["topic"] != w["topic"]]
            random.shuffle(same)
            random.shuffle(rest)
            picks = (same + rest)[:n]
            out.append({**word_view(w), "distractors": [word_view(o) for o in picks]})
        return out

    def item_view(item):
        v = dict(item)
        if item["id"].startswith(("l-", "b-", "s-")):
            v["audio"] = "/media/" + C.audio_rel(item["batch"], item["id"])
        return v

    def used_map():
        return {r["content_id"]: r["day"] for r in conn().execute("SELECT * FROM content_used")}

    def get_or_build_plan(day: date):
        row = conn().execute("SELECT * FROM lesson_day WHERE day=?", (day.isoformat(),)).fetchone()
        if row:
            return json.loads(row["plan_json"]), json.loads(row["done_json"]), row["seconds"]
        cards = all_cards()
        introduced = {c.word_id: c.introduced_on for c in cards}
        due = len(srs.review_queue(cards, day))
        plan = lesson_plan.build_day_plan(day, content(), set(introduced), used_map(), due,
                                          lesson_plan.words_of_last_week(introduced, day))
        conn().execute("INSERT INTO lesson_day (day, plan_json) VALUES (?, ?)", (day.isoformat(), json.dumps(plan)))
        conn().commit()
        return plan, [], 0

    def sitting_status(plan, done):
        out = {}
        for s in (1, 2):
            keys = [b["key"] for b in plan["blocks"] if b["sitting"] == s]
            out[s] = {"blocks": len(keys), "done": sum(1 for k in keys if k in done)}
        return out

    def placement_row():
        return conn().execute("SELECT * FROM assessment WHERE kind='placement' ORDER BY id DESC LIMIT 1").fetchone()

    def progress_numbers():
        cards = all_cards()
        t = today()
        days = active_days()
        row = conn().execute("SELECT seconds FROM lesson_day WHERE day=?", (t.isoformat(),)).fetchone()
        return {
            "streak": streak.current_streak(days, t),
            "words_known": srs.words_known(cards),
            "words_learned": len(cards),
            "minutes_today": round((row["seconds"] if row else 0) / 60),
            "goal_minutes": goal_minutes(),
            "active_days": sorted(d.isoformat() for d in days),
        }

    def goal_minutes() -> int:
        """Daily learning goal in minutes. Paz sets it on his page (default 30)."""
        try:
            return max(5, min(180, int(db.get_setting(conn(), "goal_minutes", 30))))
        except (TypeError, ValueError):
            return 30

    # ---------------- pages and files ----------------

    @app.get("/health")
    def health():
        return jsonify(ok=True)

    @app.get("/")
    def index():
        return send_from_directory(WEB, "index.html", max_age=0)

    @app.get("/web/<path:path>")
    def web(path):
        return send_from_directory(WEB, path, max_age=0)

    @app.get("/media/<path:path>")
    def media(path):
        return send_from_directory(C.MEDIA, path, max_age=86400)

    # ---------------- Saba's API ----------------

    @app.get("/api/state")
    def state():
        t = today()
        p = placement_row()
        placement = "none" if not p else ("done" if p["finished_at"] else "in_progress")
        plan = done = None
        status = None
        if placement == "done":
            plan, done, _ = get_or_build_plan(t)
            status = sitting_status(plan, done)
        return jsonify(
            name=config.get("LEARNER_NAME", "Saba"), today=t.isoformat(), weekday=t.weekday(),
            placement=placement, plan_kind=plan["kind"] if plan else None, topic=plan.get("topic") if plan else None,
            sittings=status, has_content=bool(content()["words"]), **progress_numbers())

    @app.get("/api/topics")
    def topics():
        return jsonify(content()["topics"])

    @app.get("/api/today")
    def today_plan():
        plan, done, seconds = get_or_build_plan(today())
        cont = content()
        blocks = []
        for b in plan["blocks"]:
            b = dict(b, done=b["key"] in done)
            if b["type"] == "new_words":
                b["words"] = with_distractors(b["word_ids"])
            elif b["type"] == "weekly_test":
                b["words"] = with_distractors(b["word_ids"])
            elif b.get("item_id") and b["item_id"] in cont["by_id"]:
                b["item"] = item_view(cont["by_id"][b["item_id"]])
            elif b["type"] == "speaking":
                b["phrases"] = [item_view(s) for s in cont["speaking"]]
            blocks.append(b)
        return jsonify(day=plan["day"], kind=plan["kind"], topic=plan.get("topic"), blocks=blocks,
                       seconds=seconds, sittings=sitting_status(plan, done))

    @app.post("/api/block/done")
    def block_done():
        d = body()
        t = today().isoformat()
        plan, done, _ = get_or_build_plan(today())
        key = d.get("key")
        if key not in [b["key"] for b in plan["blocks"]]:
            abort(400, "unknown block")
        seconds = max(0, min(int(d.get("seconds", 0)), 3 * 3600))
        c = conn()
        c.execute("INSERT INTO block_result (day, block, content_id, score, max, seconds, ts) VALUES (?,?,?,?,?,?,?)",
                  (t, key, d.get("content_id"), d.get("score"), d.get("max"), seconds, now_iso()))
        if d.get("content_id"):
            c.execute("INSERT INTO content_used (content_id, day) VALUES (?, ?) "
                      "ON CONFLICT(content_id) DO UPDATE SET day=excluded.day", (d["content_id"], t))
        if key not in done:
            done.append(key)
        c.execute("UPDATE lesson_day SET done_json=?, seconds=seconds+? WHERE day=?", (json.dumps(done), seconds, t))
        c.commit()
        return jsonify(ok=True, sittings=sitting_status(plan, done), **progress_numbers())

    @app.post("/api/time")
    def add_time():
        """Time spent outside the planned blocks (extra practice) counts towards today's minutes."""
        seconds = max(0, min(int(body().get("seconds", 0)), 60 * 60))
        get_or_build_plan(today())
        conn().execute("UPDATE lesson_day SET seconds = seconds + ? WHERE day = ?", (seconds, today().isoformat()))
        conn().commit()
        return jsonify(ok=True, **progress_numbers())

    @app.post("/api/words/learned")
    def words_learned():
        """Called at the end of 'New words': the words go into the flashcard deck."""
        t = today()
        c = conn()
        for wid in body().get("word_ids", []):
            if wid in content()["by_id"] and not c.execute("SELECT 1 FROM card WHERE word_id=?", (wid,)).fetchone():
                _save_card(c, srs.new_card(wid, t))
        c.commit()
        return jsonify(ok=True, **progress_numbers())

    @app.get("/api/review")
    def review_queue():
        q = srs.review_queue(all_cards(), today())
        return jsonify(cards=with_distractors([c.word_id for c in q]))

    @app.get("/api/practice")
    def practice():
        """Extra practice (not scheduled): due cards first, else a random mix of met words."""
        cards = all_cards()
        due = srs.review_queue(cards, today(), limit=10)
        ids = [c.word_id for c in due]
        if len(ids) < 10:
            rest = [c.word_id for c in cards if c.word_id not in ids]
            random.shuffle(rest)
            ids += rest[: 10 - len(ids)]
        # one more activity for variety: a listening, reading or task she has already done
        cont = content()
        done = [cont["by_id"][cid] for cid in used_map() if cid in cont["by_id"]
                and cid.startswith(("l-", "r-", "t-"))]
        extra = None
        if done:
            it = random.choice(done)
            extra = {"type": {"l": "listening", "r": "reading", "t": "task"}[it["id"][0]], "item": item_view(it)}
        # a sentence to build from a word she has met
        met = [cont["by_id"][c.word_id] for c in cards if c.word_id in cont["by_id"]]
        with_blocks = [w for w in met if (w.get("example") or {}).get("blocks")]
        sentence = word_view(random.choice(with_blocks))["example"] if with_blocks else None
        return jsonify(cards=with_distractors(ids), extra=extra, sentence=sentence)

    @app.post("/api/review")
    def review_answer():
        d = body()
        row = conn().execute("SELECT * FROM card WHERE word_id=?", (d.get("word_id"),)).fetchone()
        if not row:
            abort(404)
        correct = bool(d.get("correct"))
        card = srs.review(_card_from_row(row), correct, today())
        _save_card(conn(), card)
        conn().execute("INSERT INTO review_log (word_id, ts, correct, mode) VALUES (?,?,?,?)",
                       (card.word_id, now_iso(), int(correct), d.get("mode")))
        conn().commit()
        return jsonify(ok=True, box=card.box, due=card.due_date.isoformat())

    @app.post("/api/writing")
    def save_writing():
        d = body()
        conn().execute("INSERT INTO writing (day, kind, prompt_id, text, auto_score) VALUES (?,?,?,?,?)",
                       (today().isoformat(), d.get("kind", "fill_in"), d.get("prompt_id"), d.get("text"),
                        d.get("auto_score")))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/hint-flag")
    def hint_flag():
        d = body()
        conn().execute("INSERT INTO hint_flag (item_id, hint_text, ts) VALUES (?,?,?)",
                       (d.get("item_id", "?"), d.get("hint_text"), now_iso()))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/picture-flag")
    def picture_flag():
        d = body()
        pic = str(d.get("picture", ""))
        if not pic.startswith("/media/pictures/"):
            abort(400)
        conn().execute("INSERT INTO picture_flag (item_id, label, picture, ts) VALUES (?,?,?,?)",
                       (str(d.get("item_id", "?"))[:80], str(d.get("label", ""))[:80], pic[:200], now_iso()))
        conn().commit()
        return jsonify(ok=True)

    def pictures_in_use():
        cont = content()
        used = {"/media/" + C.picture_rel(w["picture"]) for w in cont["words"] if w.get("picture")}
        used |= {"/media/" + C.picture_rel(c) for c in C.pictures_of_placement(C.load_placement())}
        return used

    @app.get("/api/progress")
    def progress():
        n = progress_numbers()
        t = today()
        week = conn().execute("SELECT COALESCE(SUM(seconds),0) s FROM lesson_day WHERE day > ?",
                              ((t - timedelta(days=7)).isoformat(),)).fetchone()["s"]
        return jsonify(minutes_week=round(week / 60), today=t.isoformat(), **n)

    # ---------------- placement ----------------

    @app.get("/api/placement")
    def placement_get():
        p = C.load_placement()
        if not p:
            abort(404, "no placement test")
        row = placement_row()
        if not row or row["finished_at"]:
            if row and row["finished_at"] and request.args.get("restart") != "1":
                return jsonify(done=True, levels=json.loads(row["levels_json"] or "{}"))
            cur = conn().execute("INSERT INTO assessment (kind, content_id, started_at) VALUES ('placement', ?, ?)",
                                 (p["id"], now_iso()))
            conn().commit()
            row = conn().execute("SELECT * FROM assessment WHERE id=?", (cur.lastrowid,)).fetchone()
        # add media URLs
        pid = p["id"]
        for sec in p["sections"]:
            for item in sec.get("items", []):
                if sec["id"] in ("words", "listening"):
                    item["audio"] = "/media/" + C.audio_rel(pid, item["id"])
                if sec["id"] == "words":
                    item["pictures"] = ["/media/" + C.picture_rel(o) for o in item["options"]]
            for cd in sec.get("can_do", []):
                cd["audio"] = "/media/" + C.audio_rel(pid, cd["id"])
        return jsonify(done=False, assessment_id=row["id"], progress=json.loads(row["progress_json"]), test=p)

    def _current_assessment():
        row = placement_row()
        if not row or row["finished_at"]:
            abort(400, "no placement in progress")
        return row

    @app.post("/api/placement/answer")
    def placement_answer():
        row = _current_assessment()
        d = body()
        conn().execute(
            "INSERT INTO assessment_answer (assessment_id, item_id, section, answer, correct, level_tag) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(assessment_id, item_id) DO UPDATE SET answer=excluded.answer, "
            "correct=excluded.correct",
            (row["id"], d["item_id"], d["section"], json.dumps(d.get("answer"), ensure_ascii=False),
             None if d.get("correct") is None else int(bool(d["correct"])), d.get("level")))
        if "progress" in d:
            conn().execute("UPDATE assessment SET progress_json=? WHERE id=?", (json.dumps(d["progress"]), row["id"]))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/placement/progress")
    def placement_progress():
        row = _current_assessment()
        conn().execute("UPDATE assessment SET progress_json=? WHERE id=?", (json.dumps(body()), row["id"]))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/placement/recording")
    def placement_recording():
        row = _current_assessment()
        f = request.files.get("audio")
        if not f:
            abort(400)
        folder = DATA / "recordings"
        folder.mkdir(parents=True, exist_ok=True)
        name = f"placement-{row['id']}-{int(time.time())}.webm"
        f.save(folder / name)
        conn().execute("INSERT INTO recording (assessment_id, prompt_id, path, created_at) VALUES (?,?,?,?)",
                       (row["id"], request.form.get("prompt_id"), f"recordings/{name}", now_iso()))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/placement/finish")
    def placement_finish():
        row = _current_assessment()
        d = body()
        p = C.load_placement()
        answers = conn().execute("SELECT * FROM assessment_answer WHERE assessment_id=?", (row["id"],)).fetchall()

        def items(section):
            return [(a["level_tag"] or "A1", a["correct"]) for a in answers
                    if a["section"] == section and a["correct"] is not None]

        writing_sec = next(s for s in p["sections"] if s["id"] == "writing")
        note = d.get("note", "")
        checks = scoring.note_checks(note, writing_sec.get("keywords", []))
        levels = {
            "vocabulary": scoring.level_from_items(items("words")),
            "listening": scoring.level_from_items(items("listening")),
            "reading": scoring.level_from_items(items("reading")),
            "listening_reading": scoring.level_from_items(items("listening") + items("reading")),
            "speaking": scoring.level_from_self_rating([(r["level"], int(r["value"])) for r in d.get("ratings", [])]),
            "writing": checks["level"],
        }
        conn().execute("INSERT INTO writing (day, kind, prompt_id, text, auto_score) VALUES (?,?,?,?,?)",
                       (today().isoformat(), "placement_note", p["id"], note, checks["score"]))
        conn().execute("UPDATE assessment SET finished_at=?, levels_json=? WHERE id=?",
                       (now_iso(), json.dumps(levels), row["id"]))
        conn().commit()
        return jsonify(ok=True, levels=levels)

    # ---------------- Paz's page ----------------

    def paz_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not session.get("paz"):
                abort(401)
            return fn(*a, **kw)
        return wrapper

    @app.post("/api/paz/login")
    def paz_login():
        if str(body().get("pin", "")).strip() == str(config.get("PAZ_PIN", "1234")).strip():
            session["paz"] = True
            return jsonify(ok=True)
        return jsonify(ok=False), 401

    @app.get("/api/paz/summary")
    @paz_required
    def paz_summary():
        t = today()
        start = t - timedelta(days=6)
        c = conn()
        cont = content()
        days = []
        for i in range(7):
            d = (start + timedelta(days=i)).isoformat()
            r = c.execute("SELECT seconds, done_json FROM lesson_day WHERE day=?", (d,)).fetchone()
            days.append({"day": d, "minutes": round((r["seconds"] if r else 0) / 60),
                         "blocks": len(json.loads(r["done_json"])) if r else 0})
        cards = all_cards()
        learned_week = [x for x in cards if x.introduced_on >= start]
        reviews = c.execute("SELECT COUNT(*) n, COALESCE(SUM(correct),0) ok FROM review_log WHERE ts >= ?",
                            (start.isoformat(),)).fetchone()
        letters = c.execute("SELECT COUNT(*) n FROM block_result WHERE block='writing' AND day >= ?",
                            (start.isoformat(),)).fetchone()["n"]
        hard = sorted([x for x in cards if x.lapses], key=lambda x: (-x.lapses, x.box))[:8]
        blocks = c.execute(
            "SELECT block, AVG(CASE WHEN max > 0 THEN score * 1.0 / max END) ratio, COUNT(*) n "
            "FROM block_result WHERE day >= ? GROUP BY block ORDER BY ratio", (start.isoformat(),)).fetchall()
        p = placement_row()
        recs = c.execute("SELECT id, created_at FROM recording ORDER BY id DESC").fetchall()
        notes = c.execute("SELECT id, day, kind, text, auto_score, paz_level FROM writing ORDER BY id DESC LIMIT 5").fetchall()
        flags = c.execute("SELECT * FROM hint_flag ORDER BY id DESC LIMIT 30").fetchall()
        in_use = pictures_in_use()
        pic_flags = [dict(r) for r in c.execute(
            "SELECT item_id, label, picture, COUNT(*) n, MAX(ts) last FROM picture_flag "
            "GROUP BY item_id, picture ORDER BY last DESC")
            if r["picture"] in in_use]  # flags on pictures already replaced drop off
        auto = json.loads(p["levels_json"]) if p and p["levels_json"] else None
        override = json.loads(p["override_json"]) if p and p["override_json"] else None
        levels = scoring.final_levels(auto, override) if auto else None
        return jsonify(
            today=t.isoformat(), days=days, minutes_week=sum(d["minutes"] for d in days),
            words_learned_week=len(learned_week), words_known=srs.words_known(cards), words_total=len(cards),
            words_available=len(cont["words"]),
            reviews=reviews["n"], review_accuracy=round(100 * reviews["ok"] / reviews["n"]) if reviews["n"] else None,
            letters_week=letters,
            weak_words=[{"de": cont["by_id"].get(x.word_id, {}).get("de", x.word_id), "en":
                         cont["by_id"].get(x.word_id, {}).get("en", ""), "lapses": x.lapses} for x in hard],
            weak_blocks=[{"block": r["block"], "percent": None if r["ratio"] is None else round(100 * r["ratio"]),
                          "count": r["n"]} for r in blocks],
            placement={"auto": auto, "override": override, "levels": levels,
                       "outlook_pass": scoring.exam_outlook(levels) if levels else None,
                       "finished": p["finished_at"] if p else None} if p else None,
            recordings=[dict(r) for r in recs], writings=[dict(r) for r in notes],
            hint_flags=[dict(r) for r in flags], picture_flags=pic_flags, streak=streak.current_streak(active_days(), t),
            api_usage=usage.this_month(c, t), api_budget_eur=float(config.get("MONTHLY_BUDGET_EUR", 25)),
            goal_minutes=goal_minutes())

    @app.post("/api/paz/override")
    @paz_required
    def paz_override():
        d = body()
        p = placement_row()
        if not p or d.get("area") not in scoring.AREAS or d.get("level") not in scoring.LEVELS + [None, ""]:
            abort(400)
        ov = json.loads(p["override_json"] or "{}")
        if d.get("level"):
            ov[d["area"]] = d["level"]
        else:
            ov.pop(d["area"], None)
        conn().execute("UPDATE assessment SET override_json=? WHERE id=?", (json.dumps(ov), p["id"]))
        conn().commit()
        return jsonify(ok=True)

    @app.post("/api/paz/goal")
    @paz_required
    def paz_goal():
        try:
            minutes = int(body().get("minutes"))
        except (TypeError, ValueError):
            abort(400)
        if not 5 <= minutes <= 180:
            abort(400)
        db.set_setting(conn(), "goal_minutes", minutes)
        return jsonify(ok=True, goal_minutes=minutes)

    @app.get("/api/paz/recording/<int:rec_id>")
    @paz_required
    def paz_recording(rec_id):
        r = conn().execute("SELECT path FROM recording WHERE id=?", (rec_id,)).fetchone()
        if not r:
            abort(404)
        return send_from_directory(DATA, r["path"])

    return app


def main():
    port = int(config.get("PORT", 8765))
    app = create_app()
    # 127.0.0.1 only: nothing on the network can reach Saba's data
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
