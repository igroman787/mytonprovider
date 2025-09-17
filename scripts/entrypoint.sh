#!/usr/bin/env bash
set -euo pipefail

SEED_DIR="/usr/local/share/mytonprovider/storage-seed"
STORAGE="${MYTONPROVIDER_STORAGE_PATH:?MYTONPROVIDER_STORAGE_PATH is required}"

if [ ! -d "${STORAGE}/db" ] || [ ! -d "${STORAGE}/provider" ]; then
  echo "[entrypoint] seeding ${STORAGE} from image (missing db/provider)..."
  mkdir -p "${STORAGE}"
  if [ -d "${SEED_DIR}" ] && [ -n "$(ls -A "${SEED_DIR}" 2>/dev/null || true)" ]; then
    cp -an "${SEED_DIR}/." "${STORAGE}/"
  else
    echo "[warn] seed dir ${SEED_DIR} is empty or missing — nothing to copy"
  fi
  chown -R admin:admin "${STORAGE}" || true
fi

unit_exists() {
  local u="$1"
  [[ "$u" == *.service ]] || u="${u}.service"
  for d in /etc/systemd/system; do
    if [ -e "$d/$u" ]; then
      printf '%s' "$u"
      return 0
    fi
  done
  return 1
}

start_if_present() {
  local base="$1"
  local u
  if unit_exists "$base"; then
    u="$(unit_exists "$base")"
    systemctl start "$base" && echo "[ok] started!" || echo "[warn] $u start failed"
  else
    echo "[skip] $base: unit not found"
  fi
}

systemctl daemon-reload || true

start_if_present ton-storage
start_if_present ton-storage-provider
start_if_present mytonprovider-updater
start_if_present mytonproviderd

echo "Service started!"
exec /usr/bin/systemctl