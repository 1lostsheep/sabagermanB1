-- Saba's German B1 Coach — SQLite schema (version 1)
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);

-- Placement test now, monthly mock DTZ in Phase 3
CREATE TABLE IF NOT EXISTS assessment (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kind          TEXT NOT NULL,          -- 'placement' | 'mock'
  content_id    TEXT NOT NULL,          -- e.g. 'placement-v1'
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  progress_json TEXT NOT NULL DEFAULT '{}',  -- resume point
  levels_json   TEXT,                   -- {"speaking":"a2", ...} auto levels
  override_json TEXT                    -- Paz's manual levels, win over auto
);

CREATE TABLE IF NOT EXISTS assessment_answer (
  assessment_id INTEGER NOT NULL REFERENCES assessment(id),
  item_id       TEXT NOT NULL,
  section       TEXT NOT NULL,
  answer        TEXT,
  correct       INTEGER,                -- 1/0, NULL if not auto-scored
  level_tag     TEXT,
  PRIMARY KEY (assessment_id, item_id)
);

CREATE TABLE IF NOT EXISTS recording (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  assessment_id INTEGER,
  prompt_id     TEXT,
  path          TEXT NOT NULL,          -- relative to data/
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS writing (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  day         TEXT NOT NULL,
  kind        TEXT NOT NULL,            -- 'placement_note' | 'fill_in' | 'free'
  prompt_id   TEXT,
  text        TEXT,
  auto_score  REAL,
  paz_level   TEXT,
  ai_feedback TEXT                      -- Phase 2
);

-- Spaced repetition state, one row per word Saba has met
CREATE TABLE IF NOT EXISTS card (
  word_id       TEXT PRIMARY KEY,
  box           INTEGER NOT NULL DEFAULT 0,
  due_date      TEXT NOT NULL,
  reps          INTEGER NOT NULL DEFAULT 0,
  lapses        INTEGER NOT NULL DEFAULT 0,
  last_result   TEXT,                   -- 'good' | 'again'
  last_seen     TEXT,
  introduced_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_log (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  word_id TEXT NOT NULL,
  ts      TEXT NOT NULL,
  correct INTEGER NOT NULL,
  mode    TEXT
);

CREATE TABLE IF NOT EXISTS lesson_day (
  day          TEXT PRIMARY KEY,
  plan_json    TEXT NOT NULL,
  done_json    TEXT NOT NULL DEFAULT '[]',  -- list of finished block keys
  seconds      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS block_result (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  day        TEXT NOT NULL,
  block      TEXT NOT NULL,
  content_id TEXT,
  score      REAL,
  max        REAL,
  seconds    INTEGER NOT NULL DEFAULT 0,
  ts         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_used (
  content_id TEXT PRIMARY KEY,
  day        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hint_flag (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id   TEXT NOT NULL,
  hint_text TEXT,
  ts        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_usage (
  month         TEXT PRIMARY KEY,       -- 'YYYY-MM'
  calls         INTEGER NOT NULL DEFAULT 0,
  input_tokens  INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  est_cost_eur  REAL NOT NULL DEFAULT 0
);

-- Pictures Saba or Paz flagged as "not clear"
CREATE TABLE IF NOT EXISTS picture_flag (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL,                -- word id, or placement item:option
  label   TEXT,                         -- the German word, for Paz's page
  picture TEXT NOT NULL,                -- /media/pictures/... path at the time of flagging
  ts      TEXT NOT NULL
);
