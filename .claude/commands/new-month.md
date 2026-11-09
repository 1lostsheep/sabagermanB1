---
description: Generate next month's content batch for Saba (words, listening, reading, letters, tasks)
argument-hint: "[YYYY-MM] [optional notes, e.g. 'more Jobcenter, she finds reading hard']"
---

You are preparing a new monthly content batch for Saba's German B1 Coach. Arguments: $ARGUMENTS

## 1. Read first
- `CLAUDE.md` (design rules: very simple English, no grammar jargon, at most 5 new words a day).
- `content/FORMAT.md` (the exact JSON format; follow it to the letter).
- The previous batch in `content/batches/`, so you continue rather than repeat. **Never reuse an existing id.**
- Her progress. If `data/coach.db` exists, run:
  ```bash
  .venv/bin/python - <<'PY'
  import json, sqlite3
  c = sqlite3.connect("data/coach.db"); c.row_factory = sqlite3.Row
  a = c.execute("select levels_json, override_json from assessment order by id desc limit 1").fetchone()
  print("levels:", dict(a) if a else None)
  print("cards:", c.execute("select count(*), sum(box>=3) from card").fetchone()[:])
  print("hardest words:", [dict(r) for r in c.execute("select word_id, lapses, box from card where lapses>0 order by lapses desc limit 15")])
  print("block scores (30 days):", [dict(r) for r in c.execute("select block, round(avg(score*1.0/max),2) ratio, count(*) n from block_result where max>0 and day >= date('now','-30 day') group by block")])
  print("flagged Amharic hints:", [dict(r) for r in c.execute("select item_id, hint_text from hint_flag")])
  PY
  ```
  Use it to decide what to do:
  - Give more items and easier texts to weak areas.
  - Recycle the hardest words in new example sentences.
  - **Fix every flagged Amharic hint** in the batch where it first appeared.

## 2. Plan the month (tell Paz in 5 lines before writing)
- About 24 lesson days (Mon–Fri, 4 weeks; Saturdays are tests and need no new content). That gives:
  - **about 120 words**: at most 5 per day and 20 per topic, in topic order;
  - **about 24 listening items** with 2–3 questions each;
  - **about 12 reading texts**;
  - **about 12 model letters**: writing and reading alternate days;
  - **about 24 real-life tasks**, mixing `read_note`, `choose_reply` and `fill_form`;
  - **about 8 speaking phrases**.
- Topics come from Saba's real life in Mönchengladbach: school letters for the children, doctor, Jobcenter, landlord, shopping and neighbours. Later months add work, authorities (Ämter), transport and leisure. Move from A1–A2 towards B1 month by month, depending on her levels.
- DTZ focus: Speaking B1 and Writing B1 (letter recipe), with Listening and Reading at least A2. Exam-style formats are:
  - announcements, phone messages and radio for listening;
  - signs, adverts, letters and forms for reading.

## 3. Write the batch
- Folder: `content/batches/<YYYY-MM>/`. Write `batch.json` plus the six item files.
- Each word needs:
  - an article if it is a noun;
  - an English meaning in A2 English;
  - a short Amharic hint;
  - an OpenMoji hexcode for its picture. Check that the emoji really shows the word; prefer a concrete object;
  - an example sentence whose `blocks` have the action word in slot 2.
- Numbers, times and abbreviations go in `say`, written out the way they are spoken.
- Use the family names listed in CLAUDE.md (Saba, Phillip in Klasse 12, Amariam in Klasse 8).

## 4. Build and check
```bash
.venv/bin/python tools/build_batch.py <YYYY-MM>   # validates, fetches pictures, renders audio (voice from TTS_ENGINE)
.venv/bin/pytest -q
```
If a picture hexcode is not found, choose another one from openmoji.org. Fix every validation error.

## 5. Finish
- Show Paz one sample of each content type and the topic plan.
- Commit: `git add content && git commit -m "Content batch <YYYY-MM>: <topics>"`. Push only if Paz asks.
- The app picks up new batches on its own; there is no restart needed.
