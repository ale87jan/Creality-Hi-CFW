#!/usr/bin/env python3
"""Cross-compile Kalico's c_helper.so for the Creality Hi and check the result.

Runs inside the image of Dockerfile.chelper (Python 3.6, no third-party
modules). The source list and base compiler flags are read from
chelper/__init__.py without importing it, so they follow upstream changes.

Usage: chelper_build.py <chelper-src-dir> <out-dir> <source-rev>
"""
import ast
import hashlib
import os
import re
import subprocess
import sys

CC = "arm-linux-gnueabihf-gcc"
READELF = "arm-linux-gnueabihf-readelf"
# Same CPU/FPU selection as the stock binaries of the printer
# (readelf -A on stock python3.9 and c_helper.so: v7VE, VFPv3, NEONv1, hard).
TARGET_FLAGS = "-mcpu=cortex-a7 -mfpu=neon -mfloat-abi=hard"
# Deterministic output: fixed LTO seed, no build path in debug info.
REPRO_FLAGS = "-frandom-seed=c_helper -fdebug-prefix-map=%s=chelper"
LINK_LIBS = "-lm -lpthread"
MAX_GLIBC = (2, 29)
EXPECTED_ATTRS = {
    "Tag_CPU_arch": "v7",
    "Tag_FP_arch": "VFPv3",
    "Tag_Advanced_SIMD_arch": "NEONv1",
    "Tag_ABI_VFP_args": "VFP registers",
}


def read_build_recipe(srcdir):
    """Return (SOURCE_FILES, OTHER_FILES, COMPILE_ARGS) from __init__.py."""
    with open(os.path.join(srcdir, "__init__.py")) as f:
        tree = ast.parse(f.read())
    wanted = {"SOURCE_FILES": None, "OTHER_FILES": None, "COMPILE_ARGS": None}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                wanted[target.id] = ast.literal_eval(node.value)
    missing = [k for k, v in wanted.items() if v is None]
    if missing:
        sys.exit("chelper/__init__.py: cannot find %s" % ", ".join(missing))
    return wanted["SOURCE_FILES"], wanted["OTHER_FILES"], wanted["COMPILE_ARGS"]


def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    srcdir, outdir, rev = sys.argv[1:4]
    srcdir = os.path.abspath(srcdir)
    os.makedirs(outdir, exist_ok=True)
    sources, others, compile_args = read_build_recipe(srcdir)
    for name in sources + others:
        if not os.path.exists(os.path.join(srcdir, name)):
            sys.exit("missing source file: %s" % name)
    dest = os.path.join(outdir, "c_helper.so")
    flags = "%s %s %s" % (
        TARGET_FLAGS,
        REPRO_FLAGS % srcdir,
        compile_args % (dest, " ".join(sources)),
    )
    cmd = "cd %s && %s %s %s" % (srcdir, CC, flags, LINK_LIBS)
    print(cmd)
    subprocess.check_call(cmd, shell=True)

    # --- checks -----------------------------------------------------------
    errors = []
    header = run("%s -h %s" % (READELF, dest))
    if "hard-float ABI" not in header or "ARM" not in header:
        errors.append("not an ARM hard-float ELF")
    attrs = run("%s -A %s" % (READELF, dest))
    for key, value in EXPECTED_ATTRS.items():
        m = re.search(r"%s: (.*)" % key, attrs)
        if not m or m.group(1).strip() != value:
            errors.append("%s is %r, expected %r" % (key, m and m.group(1), value))
    versions = sorted(
        set(
            tuple(int(x) for x in v.split("."))
            for v in re.findall(r"GLIBC_(\d+(?:\.\d+)+)", run("%s -V %s" % (READELF, dest)))
        )
    )
    if not versions or versions[-1] > MAX_GLIBC:
        errors.append("needs glibc %s, printer has %s" % (versions[-1:], MAX_GLIBC))
    needed = re.findall(r"\(NEEDED\).*\[(.*)\]", run("%s -d %s" % (READELF, dest)))
    allowed = {"libc.so.6", "libm.so.6", "libpthread.so.0", "ld-linux-armhf.so.3"}
    if not set(needed) <= allowed:
        errors.append("unexpected NEEDED libraries: %s" % needed)

    digest = sha256(dest)
    src_digest = hashlib.sha256()
    for name in sorted(sources + others + ["__init__.py"]):
        src_digest.update(name.encode() + b"\0")
        with open(os.path.join(srcdir, name), "rb") as f:
            src_digest.update(f.read())
    info = [
        "file: c_helper.so",
        "sha256: %s" % digest,
        "size: %d" % os.path.getsize(dest),
        "source_rev: %s" % rev,
        "sources_sha256: %s" % src_digest.hexdigest(),
        "compiler: %s" % run("%s --version" % CC).splitlines()[0],
        "flags: %s %s" % (flags.replace(dest, "c_helper.so"), LINK_LIBS),
        "max_glibc_symbol: %s" % ".".join(str(x) for x in versions[-1]),
        "needed: %s" % " ".join(needed),
        "result: %s" % ("FAIL: " + "; ".join(errors) if errors else "OK"),
    ]
    with open(os.path.join(outdir, "c_helper.info"), "w") as f:
        f.write("\n".join(info) + "\n")
    with open(os.path.join(outdir, "c_helper.so.sha256"), "w") as f:
        f.write("%s  c_helper.so\n" % digest)
    print("\n".join(info))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
