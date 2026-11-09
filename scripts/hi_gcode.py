#!/usr/bin/env python3
"""Minimal client for the Klipper/Kalico API socket (standard library only).

Usage:
  hi_gcode.py <socket> info              host state (ready, error...)
  hi_gcode.py <socket> temps             heaters, thermistors and fans
  hi_gcode.py <socket> query OBJ [OBJ..] raw status of printer objects
  hi_gcode.py <socket> "G-CODE" [...]    run g-code and print its output

Exit code: 0 ok, 1 the host answered with an error, 2 cannot connect.
"""

import json
import socket
import sys
import time

TIMEOUT = 120.0


class Client:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)
        self.sock.connect(path)
        self.buf = b""
        self.next_id = 1
        self.output = []

    def _read_msg(self, timeout):
        while b"\x03" not in self.buf:
            self.sock.settimeout(timeout)
            data = self.sock.recv(4096)
            if not data:
                raise ConnectionError("socket closed by the host")
            self.buf += data
        raw, self.buf = self.buf.split(b"\x03", 1)
        return json.loads(raw.decode())

    def call(self, method, params=None):
        req_id = self.next_id
        self.next_id += 1
        req = {"id": req_id, "method": method, "params": params or {}}
        self.sock.sendall(json.dumps(req).encode() + b"\x03")
        while True:
            msg = self._read_msg(TIMEOUT)
            if msg.get("id") == req_id:
                return msg
            self._async(msg)

    def _async(self, msg):
        # Output of gcode/subscribe_output arrives as {"response": "..."}
        if "response" in msg:
            self.output.append(msg["response"])

    def drain(self, seconds):
        end = time.time() + seconds
        while True:
            left = end - time.time()
            if left <= 0:
                return
            try:
                self._async(self._read_msg(left))
            except socket.timeout:
                return


def show(msg):
    if "error" in msg:
        err = msg["error"]
        print(
            "ERROR: %s"
            % (err.get("message", err) if isinstance(err, dict) else err)
        )
        return 1
    return 0


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    try:
        cli = Client(path)
    except OSError as e:
        print("cannot connect to %s: %s" % (path, e))
        sys.exit(2)
    if cmd == "info":
        msg = cli.call("info")
        if show(msg):
            sys.exit(1)
        res = msg["result"]
        print("state: %s" % res.get("state"))
        print("message: %s" % res.get("state_message", "").strip())
        print("software_version: %s" % res.get("software_version"))
        sys.exit(0 if res.get("state") == "ready" else 1)
    if cmd in ("temps", "query"):
        if cmd == "temps":
            names = cli.call("objects/list")["result"]["objects"]
            wanted = [
                n
                for n in names
                if n.split()[0]
                in (
                    "extruder",
                    "heater_bed",
                    "temperature_sensor",
                    "fan",
                    "heater_fan",
                    "fan_generic",
                )
            ]
        else:
            wanted = args
        msg = cli.call("objects/query", {"objects": {n: None for n in wanted}})
        if show(msg):
            sys.exit(1)
        for name, status in sorted(msg["result"]["status"].items()):
            print("%s: %s" % (name, json.dumps(status, sort_keys=True)))
        sys.exit(0)
    cli.call("gcode/subscribe_output", {"response_template": {}})
    rc = 0
    for script in [cmd] + args:
        msg = cli.call("gcode/script", {"script": script})
        cli.drain(0.3)
        for line in cli.output:
            print(line)
        cli.output = []
        rc |= show(msg)
    sys.exit(rc)


if __name__ == "__main__":
    main()
