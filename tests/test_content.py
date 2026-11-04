import copy
import json

import pytest

from app import content as C


def good_batch():
    return {
        "meta": {"schema_version": 1, "batch_id": "2099-01",
                 "topics": [{"id": "doctor", "title_en": "Doctor", "title_de": "Arzt", "hint_am": "ሐኪም", "picture": "1F3E5"}]},
        "words": [{"id": "w-x-arzt", "topic": "doctor", "level": "A1", "de": "der Arzt", "article": "der",
                   "en": "doctor", "hint_am": "ሐኪም", "picture": "1F9D1-200D-2695-FE0F",
                   "example": {"de": "Ich gehe heute zum Arzt.", "en": "I go to the doctor today.",
                               "blocks": [["Ich", "who"], ["gehe", "verb"], ["heute", "when"], ["zum Arzt", "where"]]}}],
        "listening": [{"id": "l-x", "topic": "doctor", "level": "A2", "kind": "phone_message", "title_en": "Call",
                       "lines": [{"speaker": "f", "de": "Hallo."}],
                       "questions": [{"q_de": "Wer?", "q_en": "Who?", "options": ["a", "b"], "answer": 0},
                                     {"q_de": "Wann?", "q_en": "When?", "options": ["a", "b", "c"], "answer": 2}]}],
        "reading": [{"id": "r-x", "topic": "doctor", "level": "A1", "kind": "sign", "title_de": "T", "text_de": "Text",
                     "glossary": [], "questions": [{"q_de": "?", "q_en": "?", "options": ["a", "b"], "answer": 1}]}],
        "letters": [{"id": "b-x", "topic": "doctor", "level": "A2", "task_en": "t", "task_de": "t",
                     "points": [{"de": "a", "en": "a"}] * 4,
                     "lines": [{"role": "greeting", "de": "Liebe Frau Weber,"}, {"role": "reason", "de": "ich bin krank."},
                               *[{"role": "point", "de": f"Punkt {i}."} for i in range(4)],
                               {"role": "closing", "de": "Viele Grüße"}, {"role": "name", "de": "Saba"}],
                     "gaps": [{"line": 1, "word": "krank", "options": ["krank", "froh"]}]}],
        "tasks": [{"id": "t-x", "topic": "doctor", "level": "A1", "kind": "fill_form", "prompt_en": "Fill in.",
                   "material_de": "Frau Haile", "fields": [{"label_de": "Name", "label_en": "Name", "answer": ["Haile"]}]}],
        "speaking": [{"id": "s-x", "de": "Ich heiße Saba.", "en": "My name is Saba.", "hint_am": "ስሜ ሳባ ነው።"}],
    }


def test_good_batch_is_valid():
    assert C.validate_batch(good_batch(), check_media=False) == []


@pytest.mark.parametrize("mutate,expect", [
    (lambda b: b["words"].append(copy.deepcopy(b["words"][0])), "duplicate id"),
    (lambda b: b["words"][0].update(id="arzt"), "must start with 'w-'"),
    (lambda b: b["words"][0].update(topic="space"), "not in batch.json"),
    (lambda b: b["words"][0].update(hint_am=""), "missing 'hint_am'"),
    (lambda b: b["words"][0].update(picture=""), "missing 'picture'"),
    (lambda b: b["words"][0].update(article="den"), "article must be"),
    (lambda b: b["words"][0]["example"]["blocks"].pop(), "don't match"),
    (lambda b: b["words"][0]["example"].update(blocks=[["Ich", "who"], ["heute", "when"], ["gehe", "verb"], ["zum Arzt", "where"]],
                                               de="Ich heute gehe zum Arzt."), "slot 2"),
    (lambda b: b["listening"][0]["questions"][1].update(answer=3), "index into options"),
    (lambda b: b["listening"][0]["questions"].pop(), "at least 2"),
    (lambda b: b["letters"][0]["lines"].pop(2), "exactly 4 points"),
    (lambda b: b["letters"][0]["gaps"][0].update(word="müde"), "not in line"),
    (lambda b: b["tasks"][0].update(fields=[]), "needs 'fields'"),
    (lambda b: b["meta"].update(schema_version=2), "schema_version"),
])
def test_bad_batches_are_rejected(mutate, expect):
    b = good_batch()
    mutate(b)
    errors = C.validate_batch(b, check_media=False)
    assert any(expect in e for e in errors), errors


def test_missing_media_reported(tmp_path):
    errors = C.validate_batch(good_batch(), media_root=tmp_path, check_media=True)
    assert any("audio/2099-01/w-x-arzt.ogg" in e for e in errors)
    assert any("pictures/openmoji/1F9D1-200D-2695-FE0F.svg" in e for e in errors)


def test_audio_jobs_cover_everything():
    paths = [p for p, _ in C.audio_jobs(good_batch())]
    assert paths == ["audio/2099-01/w-x-arzt.ogg", "audio/2099-01/w-x-arzt-ex.ogg",
                     "audio/2099-01/l-x.ogg", "audio/2099-01/b-x.ogg", "audio/2099-01/s-x.ogg"]


def test_load_all_merges_batches(tmp_path):
    for bid in ("2099-01", "2099-02"):
        b = good_batch()
        b["meta"]["batch_id"] = bid
        d = tmp_path / bid
        d.mkdir()
        (d / "batch.json").write_text(json.dumps(b["meta"]))
        for kind in C.KINDS:
            items = [dict(i, id=i["id"] + bid[-1]) for i in b[kind]]
            (d / f"{kind}.json").write_text(json.dumps(items))
    merged = C.load_all(tmp_path)
    assert len(merged["words"]) == 2 and len(merged["topics"]) == 1
    assert merged["by_id"]["w-x-arzt2"]["batch"] == "2099-02"


def test_shipped_content_is_valid():
    """Every committed batch and the placement test must pass, including media."""
    for bid in C.batch_ids():
        assert C.validate_batch(C.load_batch(bid)) == [], bid
    p = C.load_placement()
    if p:
        assert C.validate_placement(p) == []
