#!/usr/bin/env python3
# Read-only endstop probe for the Creality Hi, run on the PC against Moonraker.
#
# Sends only QUERY_ENDSTOPS (and optionally MOTOR_READ_ALL_PIN_IO) to stock Klipper
# and prints a compact line per change, so a long manual test costs few tokens.
#
#   python3 hi_endstops.py HOST --once            # one reading
#   python3 hi_endstops.py HOST --watch 120       # print only changes for 120 s
#   python3 hi_endstops.py HOST --pin-io          # also MOTOR_READ_ALL_PIN_IO
#
# Never sends motion, heating or motor-parameter commands. Saves the raw replies
# with --out so nothing has to be pasted back.
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

ALLOWED = ("QUERY_ENDSTOPS", "MOTOR_READ_ALL_PIN_IO")


def get(base, path, timeout=15):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return json.load(r)["result"]


def run(base, script):
    if script not in ALLOWED:
        sys.exit("refused: %s" % script)
    q = urllib.parse.quote(script)
    req = urllib.request.Request(base + "/printer/gcode/script?script=" + q, method="POST")
    with urllib.request.urlopen(req, timeout=30):
        pass
    time.sleep(0.4)
    store = get(base, "/server/gcode_store?count=8")["gcode_store"]
    out = []
    for e in reversed(store):
        if e["type"] == "command":
            break
        out.append(e["message"])
    return "\n".join(reversed(out))


def parse_endstops(text):
    return {k: v for k, v in re.findall(r"(\w+):\s*(open|TRIGGERED)", text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("host")
    ap.add_argument("--port", type=int, default=7125)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=float, default=0, help="seconds to watch for changes")
    ap.add_argument("--interval", type=float, default=0.7)
    ap.add_argument("--pin-io", action="store_true")
    ap.add_argument("--out", help="append raw replies to this file")
    a = ap.parse_args()
    base = "http://%s:%d" % (a.host, a.port)

    state = get(base, "/printer/info")["state"]
    print("klippy state:", state)
    if state != "ready":
        sys.exit("printer not ready")
    raw = []

    def q():
        t = run(base, "QUERY_ENDSTOPS")
        raw.append(t)
        return parse_endstops(t)

    last = q()
    print("endstops:", last)
    if a.pin_io:
        t = run(base, "MOTOR_READ_ALL_PIN_IO")
        raw.append(t)
        print("pin_io:", t.replace("\n", " | ")[:600])
    end = time.time() + a.watch
    while time.time() < end:
        time.sleep(a.interval)
        cur = q()
        if cur != last:
            print("%s change: %s" % (time.strftime("%H:%M:%S"), cur))
            last = cur
    if a.out:
        with open(a.out, "a") as f:
            f.write("\n".join(raw) + "\n")


if __name__ == "__main__":
    main()
