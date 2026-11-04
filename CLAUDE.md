# CLAUDE.md — Saba's German B1 Coach

Read README.md for the full plan. This file is the short version for every session.

## What this is
A local German-learning app for **Saba**, so she passes the **DTZ at B1**. Paz builds and maintains it with Claude Code and generates new content every month.

- **Exam rule (since 1 Nov 2026):** B1 in Speaking, B1 in one other area, and at least A2 in the third. Strategy: B1 in Speaking and Writing, and at least A2 in Listening and Reading.
- **Saba never uses a terminal.** A desktop icon opens the app full-screen in Chrome (`--app --start-fullscreen`).

## Fixed decisions (ask Paz before changing any of these)
- Target machine: an Ubuntu 24.04 LTS laptop. Linux first, but keep it portable to Windows (no Linux-only code in `app/`).
- A local web app: a Python 3 + Flask backend, a vanilla JS front end (no build step), and SQLite in `data/coach.db`. It binds to 127.0.0.1 only. Saba's data never leaves the laptop.
- Offline first. Daily lessons run on content prepared in advance: versioned JSON in `content/batches/<YYYY-MM>/` plus media in `content/media/`.
- The Claude API is used **only** for speaking practice, letter marking and the monthly assessment/re-plan (Phase 2+).
  - The key comes from `.env` and is never committed.
  - Every call must go through `app/usage.py`, which keeps the monthly counter and checks the budget.
- Speech runs on the laptop: faster-whisper for STT (Phase 2) and Piper for TTS (it renders content audio now).
- Content is written by **Claude Code** through `/new-month`, then validated and rendered by `tools/build_batch.py`. It does not go through the API.
- Pictures are OpenMoji (CC BY-SA 4.0). Keep `LICENSES.md` up to date whenever a new media source is added.

## Design rules for Saba (most important)
1. Explanations are in **very simple English (A2)**, with an **icon** next to every instruction.
2. Every hard word or rule has an **optional Amharic hint** she can tap. Hints are **off by default**, and she can flag a hint that is wrong.
3. Every new word has a **picture and audio**.
4. **One task per screen**, big buttons, very little text, **at most 5 new words per lesson**.
5. Audio can **always be replayed and slowed down** (1×, 0.75×, 0.6×).
6. **Warm tone**:
   - no red crosses and no error red; say "Try again 💪" instead;
   - praise effort;
   - greet her by name;
   - keep the streak and "words I know" visible.
7. **No grammar jargon.** Show grammar visually:
   - coloured blocks for word order, with the verb always orange and always in slot 2;
   - article colours: der = blue, die = purple, das = green.
8. Order of skills: listen, then speak, then read, then write.

## Layout
- `app/`: the Flask server (`server.py`) and pure logic, kept separate from Flask so it can be tested:
  - `srs.py`: Leitner spaced repetition;
  - `streak.py`: streak and words known;
  - `scoring.py`: levels and exercise scoring;
  - `lesson_plan.py`: the daily plan;
  - `content.py`: loading and validating content.
- `web/`: `index.html`, `css/app.css`, `js/main.js` (router), and `js/screens/*.js` with one module per screen.
- `content/FORMAT.md`: **the content JSON spec**. Read it before touching content.
- `tools/build_batch.py`: validates a batch, fetches OpenMoji SVGs and renders Piper audio.
- `launcher/`: the desktop file, the systemd user service and `launch.sh`.
- `tests/`: pytest.

## Commands
```bash
./setup.sh                      # one-time install on the laptop (idempotent)
.venv/bin/python -m app.server  # run the server by hand (http://127.0.0.1:8765)
.venv/bin/pytest -q             # tests
.venv/bin/python tools/build_batch.py 2026-11          # validate + fetch pictures + render audio
.venv/bin/python tools/build_batch.py 2026-11 --check  # validate only
```
The monthly content workflow is `/new-month` (see `.claude/commands/new-month.md`).

## Phases
1. **Phase 1 (done):** placement test, daily lesson runner, flashcards with SRS, progress screen, Paz's page, content pipeline and the first batch. Speaking and AI marking show "coming soon" cards.
2. **Phase 2:** voice speaking partner (whisper, Claude, Piper) and AI letter marking.
3. **Phase 3:** monthly mock DTZ, level estimates, automatic re-plan and weekly email to Paz.
4. **Phase 4:** monthly content refresh from her report.

## Working style
- Small steps, with a commit after each working step.
- Ask Paz when the README doesn't answer something; don't guess.
- Never commit `.env` or `data/`.
