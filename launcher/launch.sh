#!/usr/bin/env bash
# Opens Saba's German Coach full-screen. Started by the desktop icon.
# Makes sure the local server is running first.
set -u
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="$(grep -E '^PORT=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/"

is_up() { curl -fs -o /dev/null "${URL}health"; }

if ! is_up; then
  systemctl --user start saba-coach.service 2>/dev/null || true
  for _ in $(seq 1 10); do is_up && break; sleep 0.5; done
fi
if ! is_up; then
  # No systemd service (or it failed): start the server directly
  cd "$APP_DIR" && nohup "$APP_DIR/.venv/bin/python" -m app.server \
    >>"$APP_DIR/data/server.log" 2>&1 &
  for _ in $(seq 1 30); do is_up && break; sleep 0.5; done
fi

# Own browser profile: always a fresh full-screen window, and the
# microphone permission (Phase 2) is remembered for this app only.
PROFILE="$APP_DIR/data/chrome-profile"
FLAGS=(--app="$URL" --start-fullscreen --user-data-dir="$PROFILE"
       --no-first-run --no-default-browser-check --disable-translate
       --disable-features=Translate --autoplay-policy=no-user-gesture-required
       --disable-session-crashed-bubble --password-store=basic)

for b in google-chrome google-chrome-stable chromium chromium-browser; do
  if command -v "$b" >/dev/null 2>&1; then exec "$b" "${FLAGS[@]}"; fi
done
# Last resort
exec firefox --kiosk "$URL"
