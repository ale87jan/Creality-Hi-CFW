#!/usr/bin/env python3
"""Load c_helper.so with the dynamic linker and call into it.

Uses only ctypes, so it runs on any ARMv7 Python >= 3.6: the emulated
container of Dockerfile.chelper, or the printer itself (read-only check).
RTLD_NOW makes the loader resolve every symbol, which is what fails when the
library was linked against a newer glibc than the one present.

Usage: chelper_load.py <path/to/c_helper.so>
"""

import ctypes
import os
import platform
import sys


def main():
    path = os.path.abspath(sys.argv[1])
    lib = ctypes.CDLL(path, mode=os.RTLD_NOW)
    lib.get_monotonic.restype = ctypes.c_double
    t1 = lib.get_monotonic()
    t2 = lib.get_monotonic()
    if not (t1 > 0.0 and t2 >= t1):
        sys.exit("FAIL: get_monotonic returned %r, %r" % (t1, t2))
    # A function with pointer arguments and heap use.
    lib.trapq_alloc.restype = ctypes.c_void_p
    tq = lib.trapq_alloc()
    if not tq:
        sys.exit("FAIL: trapq_alloc returned NULL")
    lib.trapq_free.argtypes = [ctypes.c_void_p]
    lib.trapq_free(tq)
    for name in (
        "serialqueue_alloc",
        "steppersyncmgr_alloc",
        "cartesian_stepper_alloc",
        "extruder_stepper_alloc",
        "input_shaper_alloc",
        "trdispatch_alloc",
    ):
        getattr(lib, name)
    print(
        "OK: %s loads on %s, python %s, libc %s"
        % (
            os.path.basename(path),
            platform.machine(),
            platform.python_version(),
            "-".join(platform.libc_ver()),
        )
    )


if __name__ == "__main__":
    main()
