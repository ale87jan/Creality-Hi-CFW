#!/usr/bin/env bash
# Build the Kalico bundle that hi_install.sh installs on the Creality Hi.
#
# Usage: scripts/make_bundle.sh [--skip-build] [--no-loadtest] <path-to-Creality-Hi-Kalico> [out-dir]
#
# Output (default out-dir: build): kalico-hi-<rev>.tar.gz and its .sha256.
# The bundle holds the tracked klippy/ tree of the checkout (HEAD), the
# cross-compiled c_helper.so (build_chelper.sh), config/hi/printer.cfg and the
# on-printer tools of this repository. The archive is deterministic: the same
# two commits give the same sha256.
# --skip-build reuses build/chelper if it was built from the same sources.
set -euo pipefail

skip=0; chelper_opts=()
while [ $# -gt 0 ]; do
    case "$1" in
        --skip-build) skip=1; shift ;;
        --no-loadtest) chelper_opts+=(--no-loadtest); shift ;;
        -*) echo "unknown option: $1" >&2; exit 2 ;;
        *) break ;;
    esac
done
kalico=${1:?usage: make_bundle.sh [--skip-build] [--no-loadtest] <path-to-Creality-Hi-Kalico> [out-dir]}
here=$(cd "$(dirname "$0")" && pwd)
out=$(mkdir -p "${2:-$here/../build}" && cd "${2:-$here/../build}" && pwd)

git -C "$kalico" rev-parse HEAD >/dev/null
if [ -n "$(git -C "$kalico" status --porcelain -- klippy config/hi | grep -v 'klippy/chelper/c_helper.so$' || true)" ]; then
    echo "uncommitted changes in klippy/ or config/hi of $kalico: commit them first" >&2
    exit 1
fi
rev=$(git -C "$kalico" rev-parse --short=12 HEAD)
stamp=$(git -C "$kalico" log -1 --format=%ct HEAD)
version=$(git -C "$kalico" describe --always --tags --long HEAD)
tools_rev=$(git -C "$here" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)

if [ $skip -eq 0 ]; then
    "$here/build_chelper.sh" "${chelper_opts[@]}" "$kalico" "$out/chelper"
fi
info="$out/chelper/c_helper.info"
[ -f "$info" ] || { echo "missing $info: run without --skip-build" >&2; exit 1; }
grep -q "^result: OK" "$info" || { echo "c_helper build did not pass its checks" >&2; exit 1; }
grep -q "^source_rev: $rev\$" "$info" || { echo "c_helper.so was built from another commit ($(grep ^source_rev "$info")), not $rev" >&2; exit 1; }
(cd "$out/chelper" && sha256sum -c --quiet c_helper.so.sha256)

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
b="$stage/kalico-hi"
mkdir -p "$b/kalico" "$b/config" "$b/tools"
git -C "$kalico" archive HEAD klippy COPYING | tar -x -C "$b/kalico"
cp "$out/chelper/c_helper.so" "$b/kalico/klippy/chelper/c_helper.so"
cp "$info" "$b/kalico/klippy/chelper/c_helper.info"
printf '%s\n' "$version" > "$b/kalico/klippy/.version"
git -C "$kalico" show HEAD:config/hi/printer.cfg > "$b/config/printer.cfg"
for f in hi_kalico.sh hi_restore.sh hi_step0.sh hi_gcode.py hi_spawn.py chelper_load.py; do
    cp "$here/$f" "$b/tools/$f"
done
chmod 755 "$b"/tools/*.sh
cat > "$b/BUNDLE_INFO" <<INFO
kalico_rev: $rev
kalico_version: $version
tools_rev: $tools_rev
c_helper_sha256: $(awk '{print $1}' "$out/chelper/c_helper.so.sha256")
INFO
(cd "$b" && find . -type f ! -name SHA256SUMS | LC_ALL=C sort | sed 's|^\./||' | xargs sha256sum > SHA256SUMS)

name="kalico-hi-$rev.tar.gz"
tar --sort=name --mtime="@$stamp" --owner=0 --group=0 --numeric-owner \
    -C "$stage" -cf - kalico-hi | gzip -n -9 > "$out/$name"
(cd "$out" && sha256sum "$name" > "$name.sha256")
echo "--- $out/$name"
cat "$b/BUNDLE_INFO"
cat "$out/$name.sha256"
ls -l "$out/$name" | awk '{print $5 " bytes"}'
