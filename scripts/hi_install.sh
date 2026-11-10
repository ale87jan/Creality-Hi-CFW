#!/bin/sh
# Install a Kalico bundle on a Creality Hi (phase 1: files only).
#
# Run ON THE PRINTER:
#   sh hi_install.sh [--dry-run] [--any-version] /tmp/kalico-hi-<rev>.tar.gz
# The file <bundle>.sha256 must be next to the bundle.
#
# It only writes under /mnt/UDISK/kalico-hi. It does not start Kalico, does
# not touch the stock Klipper, its config, any service, the rootfs/overlay,
# the U-Boot environment or the flash partitions. --dry-run runs every check
# and prints what would be done.
#
# Layout after install:
#   /mnt/UDISK/kalico-hi/current/   bundle (kalico/, tools/, config/, SHA256SUMS)
#   /mnt/UDISK/kalico-hi/previous/  bundle installed before this one
#   /mnt/UDISK/kalico-hi/config/    printer.cfg and its includes in use (kept across installs)
#   /mnt/UDISK/kalico-hi/logs/      klippy.log, install.log

# The HI_* variables only exist for scripts/selftest.sh (HI_TEST=1 skips the
# mount-point and python-version checks). Do not set them on the printer.
ROOT=${HI_ROOT:-/mnt/UDISK/kalico-hi}
DATA=$(dirname "$ROOT")
TMP=${HI_TMP:-/tmp}
PY=${HI_PY:-/usr/bin/python3}
WANT_MODEL=F018
WANT_FW=1.1.0.60

DRY=0; ANYVER=0; BUNDLE=
for a in "$@"; do
    case "$a" in
        --dry-run) DRY=1 ;;
        --any-version) ANYVER=1 ;;
        -*) echo "unknown option: $a" >&2; exit 2 ;;
        *) BUNDLE=$a ;;
    esac
done
[ -n "$BUNDLE" ] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

say() { echo "[hi_install] $*"; }
die() { echo "[hi_install] ERROR: $*" >&2; exit 1; }
ok() { echo "[hi_install] ok: $*"; }
run() {
    if [ $DRY -eq 1 ]; then echo "[dry-run] $*"; else say "+ $*"; "$@" || die "failed: $*"; fi
}

# --- checks (read-only) -----------------------------------------------------
say "checks"
model=${HI_FAKE_MODEL:-$(get_sn_mac.sh model 2>/dev/null)}
[ "$model" = "$WANT_MODEL" ] || die "model is '$model', expected $WANT_MODEL"
ok "model $model"

fw=${HI_FAKE_FW:-$(fw_printenv -n version 2>/dev/null)}
if [ "$fw" != "$WANT_FW" ]; then
    [ $ANYVER -eq 1 ] || die "firmware is '$fw'; the bundle was checked against $WANT_FW (use --any-version to continue)"
    say "WARNING: firmware '$fw' is not $WANT_FW"
else
    ok "firmware $fw"
fi

slot_boot=${HI_FAKE_SLOT:-$(fw_printenv -n boot_partition 2>/dev/null)}
slot_root=${HI_FAKE_SLOT:-$(fw_printenv -n root_partition 2>/dev/null)}
ok "active slot: boot_partition=$slot_boot root_partition=$slot_root (not changed by this script)"

[ -d "$DATA" ] || die "$DATA does not exist"
if [ -z "$HI_TEST" ]; then
    grep -q " $DATA " /proc/mounts || die "$DATA is not a mount point"
fi

[ -f "$BUNDLE" ] || die "bundle not found: $BUNDLE"
[ -f "$BUNDLE.sha256" ] || die "checksum file not found: $BUNDLE.sha256"
want=$(awk '{print $1; exit}' "$BUNDLE.sha256")
got=$(sha256sum "$BUNDLE" | awk '{print $1}')
if [ -z "$want" ] || [ "$want" != "$got" ]; then
    die "bundle checksum mismatch (want $want, got $got)"
fi
ok "bundle sha256 $got"

tar -tzf "$BUNDLE" > "$TMP/kalico-hi.list" 2>/dev/null || die "cannot list the bundle (corrupt archive?)"
bad=$(grep -v -E '^kalico-hi(/|$)' "$TMP/kalico-hi.list" | head -1)
[ -z "$bad" ] || die "unexpected path in bundle: $bad"
grep -q '\.\.' "$TMP/kalico-hi.list" && die "bundle has a path with '..'"
for f in kalico-hi/SHA256SUMS kalico-hi/BUNDLE_INFO kalico-hi/kalico/klippy/klippy.py \
         kalico-hi/kalico/klippy/chelper/c_helper.so kalico-hi/config/printer.cfg \
         kalico-hi/tools/hi_kalico.sh kalico-hi/tools/chelper_load.py; do
    grep -q -x "$f" "$TMP/kalico-hi.list" || die "bundle lacks $f"
done
ok "bundle layout ($(wc -l < "$TMP/kalico-hi.list") entries)"
rm -f "$TMP/kalico-hi.list"

size_kb=$(( $(wc -c < "$BUNDLE") / 1024 ))
need_kb=$(( size_kb * 6 + 20480 ))
free_kb=$(df -k "$DATA" | awk 'END{print $4}')
[ "$free_kb" -ge "$need_kb" ] || die "not enough space in $DATA: ${free_kb} kB free, ${need_kb} kB needed"
ok "space: ${free_kb} kB free, ${need_kb} kB needed"

[ -n "$HI_TEST" ] || $PY - <<'PYEOF' || die "python environment does not match (see above)"
import sys
if sys.version_info[:2] != (3, 9):
    sys.exit("python is %s, expected 3.9" % sys.version.split()[0])
missing = []
for name in ("cffi", "greenlet", "jinja2", "markupsafe", "serial", "numpy", "zlib"):
    try:
        __import__(name)
    except Exception as e:
        missing.append("%s (%s)" % (name, e))
if missing:
    sys.exit("missing python modules: " + ", ".join(missing))
PYEOF
ok "python 3.9 with cffi, greenlet, jinja2, markupsafe, serial, numpy, zlib"

if [ -f "$TMP/kalico-hi.pid" ] && kill -0 "$(cat "$TMP/kalico-hi.pid")" 2>/dev/null; then
    die "Kalico is running; stop it first (hi_kalico.sh stop)"
fi
ok "Kalico is not running"

# --- install ----------------------------------------------------------------
NEW=$ROOT/new
say "install into $ROOT"
run mkdir -p "$ROOT/logs" "$ROOT/config"
run rm -rf "$NEW"
run mkdir -p "$NEW"
run tar -xzf "$BUNDLE" -C "$NEW"
if [ $DRY -eq 1 ]; then
    echo "[dry-run] verify every file against $NEW/kalico-hi/SHA256SUMS"
    echo "[dry-run] load test: $PY tools/chelper_load.py kalico/klippy/chelper/c_helper.so"
    echo "[dry-run] cffi test: klippy.chelper.get_ffi()"
    echo "[dry-run] rm -rf $ROOT/previous; mv $ROOT/current $ROOT/previous; mv $NEW/kalico-hi $ROOT/current"
    echo "[dry-run] cp $ROOT/current/config/*.cfg $ROOT/config/ (each only if missing; otherwise <name>.new)"
    say "dry run finished: nothing was written"
    exit 0
fi
B=$NEW/kalico-hi
( cd "$B" && sha256sum -c SHA256SUMS > "$TMP/kalico-hi.sums" 2>&1 ) || {
    grep -v ': OK$' "$TMP/kalico-hi.sums" | head -5
    rm -rf "$NEW"; die "extracted files do not match SHA256SUMS"
}
ok "$(grep -c ': OK$' "$TMP/kalico-hi.sums") files match SHA256SUMS"
rm -f "$TMP/kalico-hi.sums"

$PY "$B/tools/chelper_load.py" "$B/kalico/klippy/chelper/c_helper.so" || { rm -rf "$NEW"; die "c_helper.so does not load on this system"; }
( cd "$B/kalico" && $PY -c "import klippy.chelper as c; ffi, lib = c.get_ffi(); print('OK: cffi binding, monotonic=%.3f' % lib.get_monotonic())" ) \
    || { rm -rf "$NEW"; die "klippy.chelper does not load through cffi"; }

[ -d "$ROOT/previous" ] && run rm -rf "$ROOT/previous"
[ -d "$ROOT/current" ] && run mv "$ROOT/current" "$ROOT/previous"
run mv "$B" "$ROOT/current"
run rm -rf "$NEW"
# Config files (printer.cfg and the files it includes): a file already in
# use is never overwritten; the bundle's version goes next to it as .new.
for src in "$ROOT"/current/config/*.cfg; do
    name=$(basename "$src")
    if [ -f "$ROOT/config/$name" ]; then
        if ! cmp -s "$src" "$ROOT/config/$name"; then
            run cp "$src" "$ROOT/config/$name.new"
            say "kept the existing $name; the bundle's version is in $ROOT/config/$name.new"
        fi
    else
        run cp "$src" "$ROOT/config/$name"
    fi
done
run chmod +x "$ROOT/current/tools/hi_kalico.sh" "$ROOT/current/tools/hi_restore.sh"
{
    echo "$(date '+%Y-%m-%d %H:%M:%S') installed $(basename "$BUNDLE") sha256=$got fw=$fw slot=$slot_root"
    cat "$ROOT/current/BUNDLE_INFO"
} >> "$ROOT/logs/install.log"
sync
say "installed. Next: $ROOT/current/tools/hi_kalico.sh start --dry-run"
