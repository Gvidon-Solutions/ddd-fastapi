#!/usr/bin/env bash
set -euo pipefail

SOURCE_CODEX_DIR="${SOURCE_CODEX_DIR:-${HOME}/.codex}"
TARGET_CODEX_DIR="${TARGET_CODEX_DIR:-backend/app/infrastructure/arq/codex_workspace/.codex}"

SOURCE_AUTH_FILE="${SOURCE_AUTH_FILE:-${SOURCE_CODEX_DIR}/auth.json}"

mkdir -p "${TARGET_CODEX_DIR}"

if [[ ! -f "${SOURCE_AUTH_FILE}" ]]; then
  echo "auth file not found: ${SOURCE_AUTH_FILE}" >&2
  exit 1
fi

install -m 600 "${SOURCE_AUTH_FILE}" "${TARGET_CODEX_DIR}/auth.json"
echo "copied auth.json -> ${TARGET_CODEX_DIR}/auth.json"
