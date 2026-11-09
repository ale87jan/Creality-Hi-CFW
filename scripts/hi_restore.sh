#!/bin/sh
# Bring a Creality Hi back to its stock Klipper after a Kalico session.
#
# Run ON THE PRINTER:
#   sh hi_restore.sh [--dry-run] [--purge]
#
# Phase 1 changes nothing persistent outside /mnt/UDISK/kalico-hi, so "back
# to stock" is: stop Kalico, start the stock services, check them. A reboot
# does the same. --purge also deletes /mnt/UDISK/kalico-hi.
# The U-Boot environment and the flash partitions are only read.

# The HI_* variables only exist for scripts/selftest.sh.
ROOT=${HI_ROOT:-/mnt/UDISK/kalico-hi}
TMP=${HI_TMP:-/tmp}
INITD=${HI_INITD:-/etc/init.d}
STOCK_KLIPPY=${HI_STOCK_KLIPPY:-/usr/share/klipper/klippy/klippy.py}
HERE=$(cd "$(dirname "$0")" && pwd)

DRY=0; PURGE=0
for a in "$@"; do
    case "$a" in
        --dry-run) DRY=1 ;;
        --purge) PURGE=1 ;;
        *) echo "unknown option: $a" >&2; exit 2 ;;
    esac
done
say() { echo "[hi_restore] $*"; }
die() { echo "[hi_restore] ERROR: $*" >&2; exit 1; }
run() {
    if [ $DRY -eq 1 ]; then echo "[dry-run] $*"; else say "+ $*"; "$@"; fi
}

say "boot slot (read-only): boot_partition=$(fw_printenv -n boot_partition 2>/dev/null) root_partition=$(fw_printenv -n root_partition 2>/dev/null)"

# 1. Stop Kalico and restart the stock services.
SWITCH=$HERE/hi_kalico.sh
[ -f "$SWITCH" ] || SWITCH=$ROOT/current/tools/hi_kalico.sh
if [ -f "$SWITCH" ]; then
    if [ $DRY -eq 1 ]; then sh "$SWITCH" stop --dry-run; else sh "$SWITCH" stop; fi
else
    say "hi_kalico.sh not found: stopping by hand"
    if [ -f "$TMP/kalico-hi.pid" ]; then run kill "$(cat "$TMP/kalico-hi.pid")"; fi
    run "$INITD/klipper" start
    run "$INITD/moonraker" restart
    run "$INITD/app" start
fi

# 2. Check that nothing of Kalico is left running and stock is back.
if [ $DRY -eq 0 ]; then
    sleep 3
    if pgrep -f "kalico-hi/current/kalico/klippy" >/dev/null; then die "a Kalico process is still running"; fi
    pgrep -f "$STOCK_KLIPPY" >/dev/null || die "stock klippy is not running: reboot the printer"
    say "stock klippy is running"
    for f in klipper klipper_mcu moonraker app mcu_update; do
        for d in /overlay/upper /overlay; do
            [ -e "$d/etc/init.d/$f" ] && say "NOTE: $d/etc/init.d/$f differs from the read-only rootfs (not changed by these scripts)"
        done
    done
fi

# 3. Optional: remove the files.
if [ $PURGE -eq 1 ]; then
    case "$ROOT" in
        */kalico-hi) run rm -rf "$ROOT" ;;
        *) die "refusing to delete '$ROOT'" ;;
    esac
    run rm -f "$TMP/kalico-hi.pid" "$TMP/kalico-hi-moonraker.pid" "$TMP/kalico-hi-moonraker.conf" "$TMP/kalico_uds" "$TMP/kalico_printer"
fi
say "done"
