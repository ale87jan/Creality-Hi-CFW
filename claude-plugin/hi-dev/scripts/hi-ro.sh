#!/usr/bin/env bash
# Read-only access to the printer (SSH commands; Moonraker GET straight from this PC), with a command allowlist and capped output.
#
# Usage:
#   hi-ro.sh [--dry] [--max BYTES] run <command...>   e.g. run cat /etc/os-release
#   hi-ro.sh [--dry] [--max BYTES] moon <path>        Moonraker GET, e.g. moon /printer/query_endstops/status
#
# Config (never committed): HI_HOST (user@address) and HI_KEY (private key path), from the
# environment or from the file ~/.config/hi-dev/env (override with HI_DEV_ENV).
# --dry prints the remote command and exits without connecting (used by the tests).
set -u
cfg="${HI_DEV_ENV:-$HOME/.config/hi-dev/env}"
# shellcheck disable=SC1090
[ -f "$cfg" ] && . "$cfg"

dry=0; max="${HI_MAX_BYTES:-4000}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry) dry=1; shift ;;
    --max) max="$2"; shift 2 ;;
    *) break ;;
  esac
done
mode="${1:-}"; [ $# -gt 0 ] && shift

die() { echo "hi-ro: $*" >&2; exit 2; }

ALLOWED_CMDS=" cat ls df uname uptime free ps head tail wc stat grep fw_printenv dmesg date id md5sum sha256sum "
# Moonraker GET paths that cannot move, heat or run G-code.
MOON_RE='^/(printer/(info|objects/(list|query)|query_endstops/status|gcode/help)|server/(info|config|temperature_store|files/(list|metadata)|history/(list|totals)))(\?[A-Za-z0-9_=&.%+-]*)?$'

case "$mode" in
  run)
    [ $# -ge 1 ] || die "run needs a command"
    cmd="$*"
    case "$cmd" in
      *[\;\&\|\<\>\$\`\(\)\{\}\\]*|*$'\n'*) die "shell metacharacters are not allowed" ;;
    esac
    first="${1}"
    case "$ALLOWED_CMDS" in *" $first "*) ;; *) die "command not in the read-only allowlist: $first" ;; esac
    case "$first" in
      tail|head) case " $cmd " in *" -f "*|*" -F "*) die "follow mode is not allowed" ;; esac ;;
      dmesg) case " $cmd " in *" -c "*|*" -C "*|*" --clear "*|*" --read-clear "*) die "dmesg clear is not allowed" ;; esac ;;
    esac
    remote="$cmd"
    ;;
  moon)
    [ $# -eq 1 ] || die "moon needs exactly one path"
    [[ "$1" =~ $MOON_RE ]] || die "Moonraker path not in the read-only allowlist: $1"
    moon_path="$1"   # fetched from this PC: the printer has neither curl nor wget
    ;;
  *) die "usage: hi-ro.sh [--dry] [--max BYTES] run <cmd...> | moon <path>" ;;
esac

if [ "$dry" = 1 ]; then echo "${remote:-GET http://HOST:7125$moon_path}"; exit 0; fi
: "${HI_HOST:?set HI_HOST in the environment or in $cfg}"
: "${HI_KEY:?set HI_KEY in the environment or in $cfg}"
if [ "$mode" = moon ]; then
  out=$(curl -s --max-time 10 "http://${HI_HOST#*@}:7125$moon_path" 2>&1); rc=$?
  printf '%s' "$out" | head -c "$max"
  [ "${#out}" -gt "$max" ] && printf '\n[hi-ro: output cut at %s bytes]\n' "$max"
  exit "$rc"
fi
out=$(timeout 25 ssh -i "$HI_KEY" -o BatchMode=yes -o ConnectTimeout=8 "$HI_HOST" "$remote" 2>&1)
rc=$?
printf '%s' "$out" | head -c "$max"
[ "${#out}" -gt "$max" ] && printf '\n[hi-ro: output cut at %s bytes]\n' "$max"
exit "$rc"
