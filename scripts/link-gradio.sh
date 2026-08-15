#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-}"
GRADIO_DIR="${2:-gradio}"

usage() {
  cat <<'USAGE'
Usage: scripts/link-gradio.sh TARGET_DIR [GRADIO_DIR]

Create TARGET_DIR/gradio as a symlink to GRADIO_DIR. If symlinking fails,
fall back to copying GRADIO_DIR. Relative paths are resolved from the
repository root. GRADIO_DIR defaults to gradio.
USAGE
}

resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "${ROOT_DIR}/$1" ;;
  esac
}

if [[ "${TARGET_DIR}" == "-h" || "${TARGET_DIR}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${TARGET_DIR}" ]]; then
  echo "Missing required TARGET_DIR." >&2
  usage >&2
  exit 2
fi

TARGET_DIR="$(resolve_path "${TARGET_DIR}")"
GRADIO_DIR="$(resolve_path "${GRADIO_DIR}")"

if [[ ! -d "${GRADIO_DIR}" ]]; then
  echo "Missing gradio directory: ${GRADIO_DIR}" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"

DEST="${TARGET_DIR}/gradio"
if [[ -e "${DEST}" || -L "${DEST}" ]]; then
  rm -rf "${DEST}"
fi

LINK_TARGET="${GRADIO_DIR}"
if command -v realpath >/dev/null 2>&1; then
  LINK_TARGET="$(realpath --relative-to="${TARGET_DIR}" "${GRADIO_DIR}")"
fi

if ln -s "${LINK_TARGET}" "${DEST}"; then
  echo "Linked ${DEST} -> ${LINK_TARGET}"
else
  echo "Symlink failed; copying ${GRADIO_DIR} to ${DEST}" >&2
  cp -R "${GRADIO_DIR}" "${DEST}"
fi
