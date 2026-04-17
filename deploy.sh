#!/usr/bin/env bash
# deploy.sh — Rsync the trading system to the VPS
# Usage: ./deploy.sh [vps_user@host]
# Example: ./deploy.sh root@65.x.x.x

set -e

VPS="${1:-root@trade.sanskarsaraf.in}"
REMOTE_DIR="/opt/trading-system"
LOCAL_DIR="$(dirname "$0")"

echo "🚀 Deploying trading system to ${VPS}:${REMOTE_DIR}"

rsync -avz --progress \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.env' \
  --exclude='data/db' \
  --exclude='data/logs' \
  --exclude='.DS_Store' \
  "${LOCAL_DIR}/" "${VPS}:${REMOTE_DIR}/"

echo ""
echo "✅ Files synced. Running docker compose on VPS..."
ssh "${VPS}" "cd ${REMOTE_DIR} && docker compose -f docker-compose.yml pull && docker compose -f docker-compose.yml up -d --build"

echo ""
echo "🎉 Deployment complete! Visit https://trade.sanskarsaraf.in"
