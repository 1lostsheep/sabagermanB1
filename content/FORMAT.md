# Content format (schema_version 1)

Every month gets one **batch** folder: `content/batches/<YYYY-MM>/`. The app loads **all** batches in name order. Old batches stay, because Saba's flashcards refer to their words.

```
content/batches/2026-11/
  batch.json      topics in teaching order
  words.json      new words and phrases (each with a picture, audio and an Amharic hint)
  listening.json  listening scripts, turned into audio by Piper
  reading.json    real-life texts with questions
  letters.json    model letters with gap-fill
  tasks.json      small real-life tasks
  speaking.json   "about me" phrases to listen and repeat (until Phase 2)
content/placement/v1/placement.json
content/media/pictures/arasaac/<id>.png         fetched by tools/build_batch.py
content/media/audio/<batch_id>/<id>.ogg         rendered by tools/build_batch.py
```

## General rules
- **IDs** must be unique across *all* batches and must never change once published, because SRS history depends on them.
  - Prefixes: `w-` word, `l-` listening, `r-` reading, `b-` letter (Brief), `t-` task, `s-` speaking phrase.
  - Add the batch id when a name could repeat, for example `l-2611-praxis-termin`.
- **English** (`*_en`) must be very simple (A2): short sentences and everyday words.
- **Amharic hints** (`hint_am`) are short and in Ge'ez script. Saba sees them only when she taps 💡.
- **Never use grammar jargon** in any field Saba sees.
- **Levels** are `"A1"`, `"A2"` or `"B1"`.
- **Topics** are `school`, `doctor`, `jobcenter`, `landlord`, `shopping` and `neighbours`, plus new ones as needed, each listed in `batch.json`.
- **Text for speech:** the voice engine (Google or Piper, see `TTS_ENGINE`) reads `de` (or `say`, if given). Write times and numbers the way people say them. Example: `"say": "um halb zehn"` for the text `"9:30"`. Use real abbreviations only in `de`.
- **Speakers:** `"f"` is a woman's voice and `"m"` is a man's voice.
- **Pictures:** `"arasaac:<id>"`, a picture from ARASAAC (https://arasaac.org). Find ids with `.venv/bin/python tools/arasaac.py Arzt Termin` and pick the one that shows the meaning most clearly; colourful situation pictures beat plain objects. An OpenMoji hexcode such as `"1F9D1-200D-2695-FE0F"` also works as a fallback.
- **Choices:** every question has `options` (2–4 short strings) and `answer`, the 0-based index of the right option. Questions show German first (`q_de`), with English below it (`q_en`).

## batch.json
```json
{
  "schema_version": 1,
  "batch_id": "2026-11",
  "title_en": "Everyday life 1",
  "level": "A1-A2",
  "topics": [
    {"id": "school", "title_en": "School", "title_de": "Schule", "picture": "1F3EB", "hint_am": "ትምህርት ቤት"}
  ]
}
```

## words.json
```json
[{
  "id": "w-arzt", "topic": "doctor", "level": "A1",
  "de": "der Arzt", "article": "der", "plural": "die Ärzte",
  "en": "doctor", "hint_am": "ሐኪም",
  "picture": "arasaac:2467",
  "example": {
    "de": "Ich gehe heute zum Arzt.",
    "en": "I go to the doctor today.",
    "blocks": [["Ich", "who"], ["gehe", "verb"], ["heute", "when"], ["zum Arzt", "where"]]
  }
}]
```
- `article` is `der`, `die`, `das` or `null` for phrases and verbs. It is shown as a colour: der blue, die purple, das green.
- `example.blocks` drives the coloured "build the sentence" game. Joining the block texts with spaces, plus the final punctuation, must give `example.de`. Roles:
  - `who`: the person or thing doing it;
  - `verb`: the action word, always slot 2, orange;
  - `verb_end`: a second action part at the end, such as *anrufen* in *Ich möchte … anrufen*; orange outline;
  - `when`, `where`, `what`, `how`, `who2` (to whom), `ask` (a question word), `not` and `other`.
- At most **5 new words per topic-day**. The app takes the next 5 words of one topic per lesson.
- Audio is rendered automatically: `audio/<batch>/<id>.ogg` for the word and `audio/<batch>/<id>-ex.ogg` for the example.

## listening.json
```json
[{
  "id": "l-2611-praxis", "topic": "doctor", "level": "A2", "kind": "phone_message",
  "title_en": "A message from the doctor's office",
  "lines": [{"speaker": "f", "de": "Guten Tag, hier ist die Praxis Dr. Weber.", "say": "Guten Tag, hier ist die Praxis Doktor Weber."}],
  "questions": [{
    "q_de": "Wann ist der neue Termin?", "q_en": "When is the new appointment?",
    "options": ["Montag, 9 Uhr", "Dienstag, 10:30 Uhr", "Freitag, 8:15 Uhr"], "answer": 1
  }]
}]
```
- `kind` is one of `announcement`, `phone_message`, `conversation` or `radio`.
- Use 2–3 questions per item. It is rendered to `audio/<batch>/<id>.ogg`, with a short pause between lines.

## reading.json
```json
[{
  "id": "r-2611-elternabend", "topic": "school", "level": "A2", "kind": "letter",
  "title_de": "Einladung zum Elternabend",
  "text_de": "Liebe Eltern,\nam Dienstag ...",
  "glossary": [{"de": "der Elternabend", "en": "parents' evening", "hint_am": "..."}],
  "questions": [{"q_de": "...", "q_en": "...", "options": ["...", "..."], "answer": 0}]
}]
```
`kind` is one of `letter`, `sign`, `ad`, `form`, `message` or `notice`.

## letters.json
A model letter follows the **letter recipe**: greeting, reason, 4 points and closing.
```json
[{
  "id": "b-2611-krank", "topic": "school", "level": "A2",
  "task_en": "Your son is sick. Write to his teacher.",
  "task_de": "Ihr Sohn ist krank. Schreiben Sie an die Lehrerin.",
  "points": [{"de": "Grund", "en": "why"}, {"de": "wie lange", "en": "how long"},
             {"de": "Hausaufgaben", "en": "homework"}, {"de": "Arzt-Brief", "en": "doctor's note"}],
  "lines": [
    {"role": "greeting", "de": "Liebe Frau Weber,", "en": "Dear Mrs Weber,"},
    {"role": "reason",   "de": "mein Sohn Abel ist krank.", "en": "my son Abel is sick."},
    {"role": "point",    "de": "...", "en": "..."},
    {"role": "closing",  "de": "Viele Grüße", "en": "Best wishes"},
    {"role": "name",     "de": "Saba", "en": "Saba"}
  ],
  "gaps": [{"line": 1, "word": "krank", "options": ["krank", "müde", "froh"]}]
}]
```
- `role` is one of `greeting`, `reason`, `point`, `closing` or `name`. Use exactly 4 `point` lines.
- Each gap blanks the first `word` in `lines[line].de`. Saba taps the right option.
- Rendered to `audio/<batch>/<id>.ogg`, which reads the whole model letter.

## tasks.json
```json
[{
  "id": "t-2611-zettel", "topic": "school", "level": "A1", "kind": "read_note",
  "prompt_en": "Read the note from school.",
  "material_title": "Zettel von der Schule",
  "material_de": "Am Freitag ist kein Unterricht.",
  "questions": [{"q_de": "...", "q_en": "...", "options": ["...", "..."], "answer": 0}]
}]
```
- `kind` is one of:
  - `read_note`: questions about the material;
  - `choose_reply`: the material is a message and the question asks for the best reply;
  - `fill_form`: the material describes a person, followed by `fields`.
- `fields` (for `fill_form` only) look like `[{"label_de": "Nachname", "label_en": "Family name", "answer": ["Haile"]}]`. Each `answer` lists every accepted spelling; matching is gentle, so it ignores case, ä/ae and extra spaces.

## speaking.json
```json
[{"id": "s-name", "topic": "about_me", "de": "Ich heiße Saba.", "en": "My name is Saba.", "hint_am": "..."}]
```

## placement/v1/placement.json
See the file itself. Its sections are `words`, `listening`, `reading`, `speaking` and `writing`. Audio goes to `audio/placement-v1/<id>.ogg`.

## Workflow
1. Write or modify JSON. The `/new-month` command in Claude Code does this.
2. Run `.venv/bin/python tools/build_batch.py 2026-11`. It validates the batch, fetches pictures and renders audio. Missing items are created and existing ones are kept, so it is safe to run again.
3. Run `.venv/bin/pytest -q`, then commit the JSON and media.
