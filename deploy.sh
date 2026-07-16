#!/usr/bin/env bash
#
# deploy.sh — pull the latest master and restart the stack on this server.
#
# Usage:
#   ./deploy.sh          # fetch, fast-forward to origin/master, recreate changed containers
#   ./deploy.sh --build  # also rebuild any locally-built images before restarting
#
# Safe to run repeatedly: exits early when already up to date.
set -euo pipefail

cd "$(dirname "$0")"

ts() { date -u +%FT%TZ; }

echo "[deploy $(ts)] fetching origin/master..."
git fetch --quiet origin master

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "[deploy $(ts)] already up to date at ${LOCAL:0:7}; nothing to do."
  exit 0
fi

echo "[deploy $(ts)] updating ${LOCAL:0:7} -> ${REMOTE:0:7}"
# --ff-only guarantees we never create a merge commit or silently diverge;
# it fails loudly if the server has committed local changes that need attention.
git pull --ff-only origin master

if [ "${1:-}" = "--build" ]; then
  echo "[deploy $(ts)] building images..."
  docker compose build
fi

echo "[deploy $(ts)] recreating containers..."
docker compose up -d

echo "[deploy $(ts)] done:"
docker compose ps
