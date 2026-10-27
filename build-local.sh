#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="nexus7-flo-diskless-builder"

command -v docker >/dev/null 2>&1 || {
  echo "Docker is required. Install/start Docker Desktop, then rerun ./build-local.sh" >&2
  exit 1
}

cd "$ROOT"

echo "==> Building local toolchain image..."
docker build -t "$IMAGE" .

echo "==> Building Nexus 7 flo RAM-only boot image..."
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e JOBS="${JOBS:-}" \
  -v "$ROOT:/src" \
  "$IMAGE" \
  bash -lc 'if [ -z "${JOBS:-}" ]; then export JOBS=$(nproc); fi; ./build.sh'

echo
echo "Done: $ROOT/out/diskless-test.img"
echo "Test only with: fastboot boot out/diskless-test.img"
echo "DO NOT use fastboot flash."
