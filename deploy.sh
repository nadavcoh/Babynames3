#!/bin/bash
# deploy.sh — run this on your dev server to pull latest and restart
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo "=== Pulling latest ==="
git pull

echo "=== Installing dependencies ==="
if [ -d "venv" ]; then
    venv/bin/pip install -r requirements.txt --quiet
else
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt --quiet
fi

echo "=== Restarting app ==="
# If running under systemd:
if systemctl is-active --quiet shem-tov 2>/dev/null; then
    sudo systemctl restart shem-tov
    echo "Restarted via systemd"
# Otherwise kill existing process and relaunch in background:
else
    pkill -f "python.*app.py" 2>/dev/null || true
    nohup venv/bin/python app.py --host 0.0.0.0 --port 5000 >> app.log 2>&1 &
    echo "Restarted (PID $!), logs in app.log"
fi

echo "=== Done ==="
