#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/project-studio}"
APP_USER="${APP_USER:-ubuntu}"
PORT="${PORT:-8080}"

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

sudo tee /etc/systemd/system/project-studio.service >/dev/null <<SERVICE
[Unit]
Description=Project Studio Dashboard
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable --now project-studio.service
sudo systemctl status project-studio.service --no-pager --lines 30
