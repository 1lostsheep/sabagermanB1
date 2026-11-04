#!/usr/bin/env bash
# One-command setup for Saba's German B1 Coach on Ubuntu 24.04.
# Run it once, logged in as the user who will use the app (Saba's account):
#     ./setup.sh             # app only
#     ./setup.sh --content   # also the tools Paz needs to build content (Piper voices)
# Safe to run again (e.g. after `git pull`).
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
WITH_CONTENT=0
[[ "${1:-}" == "--content" ]] && WITH_CONTENT=1

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

say "1/6 System packages (asks for your password)"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv curl ffmpeg

if ! command -v google-chrome >/dev/null 2>&1; then
  say "Installing Google Chrome"
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/chrome.deb" https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt-get install -y -qq "$tmp/chrome.deb"
  rm -rf "$tmp"
fi

say "2/6 Python environment"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-dev.txt
if [[ $WITH_CONTENT == 1 ]]; then
  .venv/bin/pip install -q -r requirements-content.txt
  .venv/bin/python tools/build_batch.py --voices-only
fi

say "3/6 Settings (.env)"
if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env — edit PAZ_PIN and (for Phase 2) ANTHROPIC_API_KEY."
fi

say "4/6 Database"
mkdir -p data
.venv/bin/python -m app.db

say "5/6 Background service (starts with login)"
mkdir -p "$HOME/.config/systemd/user"
sed "s|@APP_DIR@|$APP_DIR|g" launcher/saba-coach.service > "$HOME/.config/systemd/user/saba-coach.service"
systemctl --user daemon-reload
systemctl --user enable --now saba-coach.service
systemctl --user restart saba-coach.service

say "6/6 Desktop icon"
chmod +x launcher/launch.sh
mkdir -p "$HOME/.local/share/applications"
sed "s|@APP_DIR@|$APP_DIR|g" launcher/saba-coach.desktop > "$HOME/.local/share/applications/saba-coach.desktop"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
mkdir -p "$DESKTOP_DIR"
cp "$HOME/.local/share/applications/saba-coach.desktop" "$DESKTOP_DIR/saba-coach.desktop"
chmod +x "$DESKTOP_DIR/saba-coach.desktop"
# Ubuntu's desktop only runs icons marked as trusted
gio set "$DESKTOP_DIR/saba-coach.desktop" metadata::trusted true 2>/dev/null || true

say "Done! Double-click 'German Coach' on the desktop."
echo "Tests:   .venv/bin/pytest -q"
echo "Server:  systemctl --user status saba-coach"
