#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/root/Crypto-signal-bot"
BRANCH="${1:-main}"
LOCKFILE="/var/lock/crypto-deploy.lock"
LOGFILE="/var/log/crypto-deploy.log"
VENV_ACTIVATE="${REPO_DIR}/venv/bin/activate"
SERVICE_NAME="crypto-bot.service"
KEEP_PREV="/root/crypto-deploy-prev.txt"

mkdir -p "$(dirname "$LOGFILE")"
touch "$LOGFILE"

exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "$(date -Iseconds) Deploy in progress — exiting" | tee -a "$LOGFILE"
  exit 0
fi

{
  echo "==== $(date -Iseconds) Starting deploy (branch=$BRANCH) ===="

  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "ERROR: $REPO_DIR is not a git repo" | tee -a "$LOGFILE"
    exit 2
  fi

  cd "$REPO_DIR"

  CURRENT_COMMIT=$(git rev-parse --verify HEAD || echo "none")
  echo "$CURRENT_COMMIT" > "$KEEP_PREV"

  git fetch --prune origin "$BRANCH"
  git reset --hard "origin/$BRANCH"

  if [ -f requirements.txt ] && [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck disable=SC1090
    source "$VENV_ACTIVATE"
    pip install -r requirements.txt
    deactivate || true
  fi

  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME"
  sleep 3

  if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Service $SERVICE_NAME active after restart"
  else
    echo "ERROR: $SERVICE_NAME not active after restart. Rolling back..." | tee -a "$LOGFILE"
    PREV_COMMIT=$(cat "$KEEP_PREV" || echo "")
    if [ -n "$PREV_COMMIT" ] && [ "$PREV_COMMIT" != "none" ]; then
      git reset --hard "$PREV_COMMIT"
      systemctl restart "$SERVICE_NAME" || true
      echo "Rolled back to $PREV_COMMIT"
    fi
    exit 3
  fi

  echo "Deployed commit: $(git rev-parse --short HEAD)"
  echo "==== $(date -Iseconds) Deploy finished ===="
} 2>&1 | tee -a "$LOGFILE"

flock -u 9
