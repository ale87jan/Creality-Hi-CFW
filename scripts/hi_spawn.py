#!/usr/bin/env python3
"""Start a command detached from the terminal and record its pid.

The stock Creality Hi has no nohup/setsid, so this does the classic double
fork: the command survives the end of the SSH session.

Usage: hi_spawn.py <pidfile> <command> [args...]
"""

import os
import sys


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pidfile, argv = sys.argv[1], sys.argv[2:]
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    with open(pidfile, "w") as f:
        f.write("%d\n" % os.getpid())
    os.execv(argv[0], argv)


if __name__ == "__main__":
    main()
