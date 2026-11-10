#!/bin/sh
# Switch a Creality Hi between its stock Klipper and Kalico, for one session.
#
# Run ON THE PRINTER. Nothing here is persistent: Kalico is started by hand
# and a reboot always brings the stock firmware back. Files are only written
# under /mnt/UDISK/kalico-hi and /tmp. No U-Boot variable, flash partition,
# rootfs/overlay file or motor parameter is touched.
#
#   hi_kalico.sh status
#   hi_kalico.sh start [--dry-run] [--ui] [--force]
#   hi_kalico.sh stop  [--dry-run]
#   hi_kalico.sh gcode "M105" ["..."]     run g-code on Kalico
#   hi_kalico.sh info | temps | log
#
# start: stops the Creality services (screen, cloud) and the stock Klipper,
#        then starts Kalico on its own socket. --ui also points the stock
#        Moonraker (and so Fluidd, port 4408) at Kalico.
# stop:  turns heaters, fans and motors off, stops Kalico and restarts the
#        stock services.

# The HI_* variables only exist so that scripts/selftest.sh can run this
# script off the printer. Do not set them on the printer.
ROOT=${HI_ROOT:-/mnt/UDISK/kalico-hi}
TMP=${HI_TMP:-/tmp}
INITD=${HI_INITD:-/etc/init.d}
PY=${HI_PY:-/usr/bin/python3}
STOCK_KLIPPY=${HI_STOCK_KLIPPY:-/usr/share/klipper/klippy/klippy.py}
CUR=$ROOT/current
KLIPPY=$CUR/kalico/klippy/klippy.py
# HI_CONFIG picks another phase config of the bundle (phase2.cfg, phase3.cfg).
CONF=$ROOT/config/${HI_CONFIG:-printer.cfg}
LOGDIR=$ROOT/logs
SOCK=$TMP/kalico_uds
TTY=$TMP/kalico_printer
PIDFILE=$TMP/kalico-hi.pid
MR_PIDFILE=$TMP/kalico-hi-moonraker.pid
MR_CONF=$TMP/kalico-hi-moonraker.conf
MR_STOCK_CONF=${HI_MR_CONF:-/usr/share/moonraker/moonraker.conf}
MR_PY=${HI_MR_PY:-/usr/share/moonraker-env/bin/python}
MR_SCRIPT=${HI_MR_SCRIPT:-/usr/share/moonraker/moonraker.py}
STOCK_SOCK=$TMP/klippy_uds
GCODE="$PY $CUR/tools/hi_gcode.py"
SPAWN="$PY $CUR/tools/hi_spawn.py"

DRY=0; UI=0; FORCE=0
cmd=$1; [ $# -gt 0 ] && shift
case "$cmd" in start|stop)
    for a in "$@"; do
        case "$a" in
            --dry-run) DRY=1 ;;
            --ui) UI=1 ;;
            --force) FORCE=1 ;;
            *) echo "unknown option: $a" >&2; exit 2 ;;
        esac
    done ;;
esac

say() { echo "[hi_kalico] $*"; }
die() { echo "[hi_kalico] ERROR: $*" >&2; exit 1; }
run() {
    if [ $DRY -eq 1 ]; then echo "[dry-run] $*"; else say "+ $*"; "$@"; fi
}
alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
stock_klippy_pid() { pgrep -f "$STOCK_KLIPPY" | head -1; }

# "printing"/"paused" if the stock Klipper has a job, else its state or "".
stock_print_state() {
    [ -S $STOCK_SOCK ] || return 0
    $GCODE $STOCK_SOCK query print_stats 2>/dev/null | sed -n 's/.*"state": "\([a-z]*\)".*/\1/p'
}

wait_gone() { # wait_gone <seconds> <pid>
    n=$1
    while [ "$n" -gt 0 ] && kill -0 "$2" 2>/dev/null; do sleep 1; n=$((n - 1)); done
    ! kill -0 "$2" 2>/dev/null
}

do_status() {
    sp=$(stock_klippy_pid)
    echo "stock klippy : ${sp:-not running}"
    if alive $PIDFILE; then echo "kalico       : running (pid $(cat $PIDFILE))"; else echo "kalico       : not running"; fi
    if alive $MR_PIDFILE; then echo "moonraker    : pointed at Kalico (pid $(cat $MR_PIDFILE))"; else echo "moonraker    : stock"; fi
    [ -f $CUR/BUNDLE_INFO ] && sed 's/^/bundle       : /' $CUR/BUNDLE_INFO
    alive $PIDFILE && $GCODE $SOCK info
    return 0
}

do_start() {
    [ -f $KLIPPY ] || die "Kalico is not installed in $CUR (run hi_install.sh)"
    [ -f $CONF ] || die "missing $CONF"
    alive $PIDFILE && die "Kalico is already running (pid $(cat $PIDFILE))"
    state=$(stock_print_state)
    case "$state" in
        printing|paused) die "the stock Klipper has a job ($state): not switching" ;;
        "") if [ -n "$(stock_klippy_pid)" ] && [ $FORCE -eq 0 ]; then
                die "cannot read the print state of the stock Klipper; use --force if the printer is idle"
            fi ;;
    esac
    say "stock print state: ${state:-unknown}"
    [ $DRY -eq 1 ] || mkdir -p $LOGDIR

    # 1. Creality services talk to the stock socket; stop them for the session.
    run $INITD/app stop
    # 2. Stock Klipper must release the serial ports.
    run $INITD/klipper stop
    if [ $DRY -eq 0 ]; then
        sp=$(stock_klippy_pid)
        [ -n "$sp" ] && { wait_gone 15 "$sp" || die "stock klippy (pid $sp) did not stop"; }
    fi
    # 3. Kalico, detached, with its own socket and pty.
    if [ $DRY -eq 1 ]; then
        echo "[dry-run] HOME=$ROOT $SPAWN $PIDFILE $PY $KLIPPY $CONF -l $LOGDIR/klippy.log -a $SOCK -I $TTY"
    else
        say "starting Kalico"
        rm -f $PIDFILE
        HOME=$ROOT $SPAWN $PIDFILE $PY $KLIPPY $CONF -l $LOGDIR/klippy.log -a $SOCK -I $TTY \
            || die "could not start Kalico (stock is stopped: run '$0 stop')"
        sleep 1
        n=${HI_START_WAIT:-60}
        while [ $n -gt 0 ]; do
            sleep 2; n=$((n - 2))
            alive $PIDFILE || { tail -20 $LOGDIR/klippy.log; die "Kalico exited; see $LOGDIR/klippy.log (stock is stopped: run '$0 stop')"; }
            out=$($GCODE $SOCK info 2>/dev/null)
            case "$out" in
                *"state: ready"*) break ;;
                *"state: error"*|*"state: shutdown"*) break ;;
            esac
        done
        $GCODE $SOCK info
    fi
    # 4. Optional: stock Moonraker pointed at Kalico.
    if [ $UI -eq 1 ]; then
        run $INITD/moonraker stop
        if [ $DRY -eq 1 ]; then
            echo "[dry-run] sed 's|^klippy_uds_address:.*|klippy_uds_address: $SOCK|' $MR_STOCK_CONF > $MR_CONF"
            echo "[dry-run] HOME=/mnt/UDISK $SPAWN $MR_PIDFILE $MR_PY $MR_SCRIPT -c $MR_CONF -l $LOGDIR/moonraker.log"
        else
            sed "s|^klippy_uds_address:.*|klippy_uds_address: $SOCK|" $MR_STOCK_CONF > $MR_CONF
            grep -q "^klippy_uds_address: $SOCK" $MR_CONF || die "could not rewrite klippy_uds_address in $MR_CONF"
            HOME=/mnt/UDISK $SPAWN $MR_PIDFILE $MR_PY $MR_SCRIPT -c $MR_CONF -l $LOGDIR/moonraker.log \
                || die "moonraker did not start"
        fi
    fi
    say "done. Back to stock: '$0 stop' or reboot."
}

do_stop() {
    if alive $PIDFILE; then
        if [ $DRY -eq 0 ]; then
            say "turning heaters, fans and motors off"
            $GCODE $SOCK "TURN_OFF_HEATERS" "M107" "M84" 2>&1 | sed 's/^/  /'
        fi
        pid=$(cat $PIDFILE)
        run kill "$pid"
        if [ $DRY -eq 0 ]; then
            wait_gone 10 "$pid" || { say "still alive, sending KILL"; kill -9 "$pid"; wait_gone 5 "$pid"; }
        fi
    else
        say "Kalico is not running"
    fi
    [ $DRY -eq 1 ] || rm -f $PIDFILE $SOCK
    if alive $MR_PIDFILE; then
        run kill "$(cat $MR_PIDFILE)"
        [ $DRY -eq 1 ] || { sleep 2; rm -f $MR_PIDFILE $MR_CONF; }
    fi
    # Stock services back, in boot order (rc.d: S55klipper, S56moonraker, S99app).
    run $INITD/klipper start
    run $INITD/moonraker restart
    run $INITD/app start
    if [ $DRY -eq 0 ]; then
        sleep 5
        sp=$(stock_klippy_pid)
        if [ -n "$sp" ]; then
            say "stock klippy running (pid $sp)"
        else
            die "stock klippy is NOT running: reboot the printer"
        fi
    fi
}

case "$cmd" in
    status) do_status ;;
    start) do_start ;;
    stop) do_stop ;;
    gcode) [ $# -ge 1 ] || die "usage: $0 gcode \"M105\""; $GCODE $SOCK "$@" ;;
    info|temps) $GCODE $SOCK "$cmd" ;;
    log) tail -n 40 $LOGDIR/klippy.log ;;
    *) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
