#!/usr/bin/env bash
# Cross-compile Kalico's c_helper.so for the Creality Hi with Docker.
#
# Usage: scripts/build_chelper.sh [--no-loadtest] <path-to-Creality-Hi-Kalico> [out-dir]
#
# Output (default out-dir: build/chelper): c_helper.so, c_helper.so.sha256,
# c_helper.info and, unless --no-loadtest, loadtest.txt.
# Needs Docker with BuildKit (Docker Desktop, or docker buildx). The load test
# runs an ARMv7 container under emulation.
set -euo pipefail

target=export-tested
if [ "${1:-}" = "--no-loadtest" ]; then
    target=export
    shift
fi
kalico=${1:?usage: build_chelper.sh [--no-loadtest] <path-to-Creality-Hi-Kalico> [out-dir]}
here=$(cd "$(dirname "$0")" && pwd)
out=${2:-"$here/../build/chelper"}
src="$kalico/klippy/chelper"
[ -f "$src/__init__.py" ] || { echo "not a Kalico checkout: $kalico" >&2; exit 1; }

rev=$(git -C "$kalico" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
if [ -n "$(git -C "$kalico" status --porcelain -- klippy/chelper 2>/dev/null | grep -v 'c_helper.so$' || true)" ]; then
    rev="$rev-dirty"
fi

mkdir -p "$out"
# CHELPER_BUILD_ARGS: extra "docker build" arguments, only needed on networks
# behind a proxy (see the APT_MIRROR note in Dockerfile.chelper).
# shellcheck disable=SC2086
DOCKER_BUILDKIT=1 docker build ${CHELPER_BUILD_ARGS:-} \
    -f "$here/Dockerfile.chelper" \
    --build-context scripts="$here" \
    --build-arg SOURCE_REV="$rev" \
    --target "$target" \
    --output "type=local,dest=$out" \
    "$src"

echo "--- $out"
cat "$out/c_helper.info"
[ -f "$out/loadtest.txt" ] && cat "$out/loadtest.txt"
(cd "$out" && sha256sum -c c_helper.so.sha256)
