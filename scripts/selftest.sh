#!/usr/bin/env bash
# Off-printer test of hi_install.sh, hi_kalico.sh and hi_restore.sh.
#
# Usage: scripts/selftest.sh
# Needs: bash, python3, gcc, tar, sha256sum. Uses "busybox ash" when busybox
# is installed (closer to the printer), else sh.
#
# A fake bundle (stub klippy that serves the API socket) is installed into a
# temporary directory with fake /etc/init.d scripts. It checks the script
# logic (checks, dry-run, ordering, cleanup); it does not test Kalico.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
trap 'pkill -f "$T" 2>/dev/null || true; rm -rf "$T"' EXIT
SH=sh; command -v busybox >/dev/null && SH="busybox ash"
pass=0; fail=0
check() { # check <description> <command...>
    local d=$1; shift
    if "$@" >"$T/last.out" 2>&1; then pass=$((pass + 1)); echo "ok   $d"
    else fail=$((fail + 1)); echo "FAIL $d"; sed 's/^/     /' "$T/last.out" | tail -8; fi
}
refuse() { local d=$1; shift; if "$@" >"$T/last.out" 2>&1; then fail=$((fail + 1)); echo "FAIL $d (did not refuse)"; else pass=$((pass + 1)); echo "ok   $d"; fi; }

# --- fake printer -----------------------------------------------------------
mkdir -p "$T/data" "$T/tmp" "$T/initd" "$T/stock"
export HI_TEST=1 HI_ROOT="$T/data/kalico-hi" HI_TMP="$T/tmp" HI_INITD="$T/initd"
export HI_PY; HI_PY=$(command -v python3)
export HI_FAKE_MODEL=F018 HI_FAKE_FW=1.1.0.60 HI_FAKE_SLOT=A HI_START_WAIT=10
export HI_STOCK_KLIPPY="$T/stock/klippy.py"
cat > "$T/stub_klippy.py" <<'PY'
import json, os, socket, sys
sock_path = sys.argv[sys.argv.index("-a") + 1]
state = os.environ.get("STUB_PRINT_STATE", "standby")
if os.path.exists(sock_path):
    os.unlink(sock_path)
srv = socket.socket(socket.AF_UNIX); srv.bind(sock_path); srv.listen(5)
while True:
    conn, _ = srv.accept(); buf = b""
    while True:
        data = conn.recv(4096)
        if not data: break
        buf += data
        while b"\x03" in buf:
            raw, buf = buf.split(b"\x03", 1)
            req = json.loads(raw); m = req["method"]; res = {}
            if m == "info": res = {"state": "ready", "state_message": "Printer is ready", "software_version": "stub"}
            elif m == "objects/list": res = {"objects": ["extruder", "heater_bed", "print_stats"]}
            elif m == "objects/query": res = {"status": {k: {"state": state, "temperature": 21.5} for k in req["params"]["objects"]}}
            elif m == "gcode/script":
                open(sock_path + ".gcode", "a").write(req["params"]["script"] + "\n")
                conn.sendall(json.dumps({"response": "ok " + req["params"]["script"]}).encode() + b"\x03")
            conn.sendall(json.dumps({"id": req["id"], "result": res}).encode() + b"\x03")
PY
for s in app klipper moonraker; do
    cat > "$T/initd/$s" <<SH
#!/bin/sh
echo "$s \$1" >> "$T/initd.log"
SH
    chmod +x "$T/initd/$s"
done
# the fake stock klipper service really starts/stops a stub "stock klippy"
cat > "$T/initd/klipper" <<SH
#!/bin/sh
echo "klipper \$1" >> "$T/initd.log"
case \$1 in
  start) cp "$T/stub_klippy.py" "$T/stock/klippy.py"; $HI_PY "$here/hi_spawn.py" "$T/stock.pid" $HI_PY "$T/stock/klippy.py" -a "$T/tmp/klippy_uds" ;;
  stop) [ -f "$T/stock.pid" ] && kill \$(cat "$T/stock.pid"); rm -f "$T/stock.pid" "$T/tmp/klippy_uds" ;;
esac
SH

# --- fake bundle ------------------------------------------------------------
b="$T/stage/kalico-hi"; mkdir -p "$b/kalico/klippy/chelper" "$b/config" "$b/tools"
cp "$T/stub_klippy.py" "$b/kalico/klippy/klippy.py"
: > "$b/kalico/klippy/__init__.py"
cat > "$b/kalico/klippy/chelper/__init__.py" <<'PY'
class _Lib:
    def get_monotonic(self): return 1.0
def get_ffi(): return None, _Lib()
PY
cat > "$T/stub.c" <<'C'
#include <stdlib.h>
double get_monotonic(void) { static double t = 1.0; return t += 1.0; }
void *trapq_alloc(void) { return malloc(8); }
void trapq_free(void *p) { free(p); }
void serialqueue_alloc(void) {} void steppersyncmgr_alloc(void) {} void cartesian_stepper_alloc(void) {}
void extruder_stepper_alloc(void) {} void input_shaper_alloc(void) {} void trdispatch_alloc(void) {}
C
gcc -shared -fPIC -o "$b/kalico/klippy/chelper/c_helper.so" "$T/stub.c"
echo "[printer]" > "$b/config/printer.cfg"
echo "# base" > "$b/config/base.cfg"
cp "$here"/hi_kalico.sh "$here"/hi_restore.sh "$here"/hi_step0.sh "$here"/hi_gcode.py "$here"/hi_spawn.py "$here"/chelper_load.py "$b/tools/"
echo "kalico_rev: selftest" > "$b/BUNDLE_INFO"
(cd "$b" && find . -type f ! -name SHA256SUMS | LC_ALL=C sort | sed 's|^\./||' | xargs sha256sum > SHA256SUMS)
B="$T/kalico-hi-selftest.tar.gz"
tar -C "$T/stage" -czf "$B" kalico-hi
(cd "$T" && sha256sum "$(basename "$B")" > "$B.sha256")
K="$HI_ROOT/current/tools/hi_kalico.sh"
snapshot() { (cd "$T" && find data tmp initd.log -type f -newer "$T/mark" 2>/dev/null | sort); }

# --- hi_install.sh ----------------------------------------------------------
touch "$T/mark"; sleep 1
check "install --dry-run passes the checks" $SH "$here/hi_install.sh" --dry-run "$B"
check "install --dry-run writes nothing" test -z "$(snapshot)"
HI_FAKE_MODEL=F008 refuse "install refuses another model" $SH "$here/hi_install.sh" "$B"
HI_FAKE_FW=1.1.0.74 refuse "install refuses another firmware" $SH "$here/hi_install.sh" "$B"
cp "$B" "$T/bad.tar.gz"; cp "$B.sha256" "$T/bad.tar.gz.sha256"; printf 'x' >> "$T/bad.tar.gz"
refuse "install refuses a bundle with a wrong checksum" $SH "$here/hi_install.sh" "$T/bad.tar.gz"
check "nothing installed after the refusals" test ! -e "$HI_ROOT/current"
check "install" $SH "$here/hi_install.sh" "$B"
check "layout: current, config, logs" test -f "$HI_ROOT/current/kalico/klippy/klippy.py" -a -f "$HI_ROOT/config/printer.cfg" -a -f "$HI_ROOT/logs/install.log"
check "install copies the included config files" test -f "$HI_ROOT/config/base.cfg"
echo "# mine" >> "$HI_ROOT/config/printer.cfg"
check "second install" $SH "$here/hi_install.sh" "$B"
check "second install keeps the config and the previous bundle" test -d "$HI_ROOT/previous" -a -f "$HI_ROOT/config/printer.cfg.new" -a "$(tail -1 "$HI_ROOT/config/printer.cfg")" = "# mine"

# --- hi_kalico.sh -----------------------------------------------------------
"$T/initd/klipper" start; sleep 1; : > "$T/initd.log"
touch "$T/mark"; sleep 1
check "start --dry-run" $SH "$K" start --dry-run
check "start --dry-run changes nothing" test -z "$(snapshot)" -a -f "$T/stock.pid"
"$T/initd/klipper" stop; STUB_PRINT_STATE=printing "$T/initd/klipper" start; sleep 1; : > "$T/initd.log"
refuse "start refuses while the stock Klipper is printing" $SH "$K" start
check "refusal leaves the stock services alone" test ! -s "$T/initd.log"
"$T/initd/klipper" stop; "$T/initd/klipper" start; sleep 1; : > "$T/initd.log"
check "start" $SH "$K" start
check "start stops app, then stock klipper" test "$(tr '\n' ',' < "$T/initd.log")" = "app stop,klipper stop,"
check "Kalico runs detached, stock klippy is gone" test -f "$T/tmp/kalico-hi.pid" -a ! -f "$T/stock.pid"
refuse "second start refuses" $SH "$K" start
check "gcode" $SH "$K" gcode M105
cp "$T/last.out" "$T/gcode.out"
check "gcode output" grep -q "ok M105" "$T/gcode.out"
check "temps" $SH "$K" temps
refuse "install refuses while Kalico runs" $SH "$here/hi_install.sh" "$B"
: > "$T/initd.log"
check "stop" $SH "$K" stop
check "stop turns heaters, fans and motors off first" test "$(tr '\n' ',' < "$T/tmp/kalico_uds.gcode" | sed 's/^M105,//')" = "TURN_OFF_HEATERS,M107,M84,"
check "stop restarts stock in boot order" test "$(tr '\n' ',' < "$T/initd.log")" = "klipper start,moonraker restart,app start,"
check "Kalico is gone, stock klippy is back" test ! -f "$T/tmp/kalico-hi.pid" -a -f "$T/stock.pid"

# --- hi_restore.sh ----------------------------------------------------------
check "start again" $SH "$K" start
touch "$T/mark"; sleep 1
check "restore --dry-run" $SH "$HI_ROOT/current/tools/hi_restore.sh" --dry-run --purge
check "restore --dry-run changes nothing" test -z "$(snapshot | grep -v klippy.log || true)" -a -f "$T/tmp/kalico-hi.pid"
cp "$HI_ROOT/current/tools/hi_restore.sh" "$HI_ROOT/current/tools/hi_kalico.sh" "$T/"
check "restore --purge" $SH "$T/hi_restore.sh" --purge
check "restore removed the install and left stock running" test ! -e "$HI_ROOT" -a -f "$T/stock.pid" -a ! -f "$T/tmp/kalico-hi.pid"
"$T/initd/klipper" stop

echo "--- $pass passed, $fail failed (shell: $SH)"
[ $fail -eq 0 ]
