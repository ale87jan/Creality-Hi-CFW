#!/usr/bin/env python3
# Firmware extraction helpers for Creality Hi / K2 OTA images.
#
# Subcommands:
#   ota       <image.img> <outdir>   unpack the SWUpdate CPIO and the SquashFS
#                                    rootfs (needs 7-Zip: 7z on PATH), and
#                                    write an md5 manifest of the rootfs
#   mcu-dict  <firmware.bin> [out]   extract the Klipper data dictionary
#   bootimg   <kernel> <outdir>      split an Android boot image: vmlinux,
#                                    DTBs and the kernel .config (IKCONFIG)
#   dtb       <file.dtb>             dump a flattened device tree as text
#
# Extracted files are untrusted data: this tool only parses them.
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

# ---------------------------------------------------------------------------
# ota
# ---------------------------------------------------------------------------


def run_7z(archive, outdir):
    exe = shutil.which("7z") or shutil.which("7z.exe")
    if not exe:
        sys.exit("7z not found on PATH (install 7-Zip)")
    # -snl keeps symlinks as links; 7-Zip reports "dangerous link" errors for
    # absolute targets, which is expected for a rootfs.
    res = subprocess.run([exe, "x", "-y", "-snl", "-o" + outdir, archive],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return res.returncode, res.stdout.decode(errors="replace")


def write_manifest(rootdir, path):
    lines = []
    for base, _dirs, files in os.walk(rootdir):
        for name in files:
            full = os.path.join(base, name)
            if os.path.islink(full):
                continue
            h = hashlib.md5()
            with open(full, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            rel = os.path.relpath(full, rootdir).replace(os.sep, "/")
            lines.append("%s  %s" % (h.hexdigest(), rel))
    lines.sort(key=lambda l: l[34:])
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


def cmd_ota(args):
    outer = os.path.join(args.outdir, "outer")
    rootfs = os.path.join(args.outdir, "rootfs")
    code, log = run_7z(args.image, outer)
    if code != 0:
        sys.exit("7z failed on %s:\n%s" % (args.image, log[-2000:]))
    print("outer:", ", ".join(sorted(os.listdir(outer))))
    code, log = run_7z(os.path.join(outer, "rootfs"), rootfs)
    with open(os.path.join(args.outdir, "7z-rootfs.log"), "w") as f:
        f.write(log)
    n = write_manifest(rootfs, os.path.join(args.outdir, "manifest.txt"))
    print("rootfs: %d files (7z exit %d, see 7z-rootfs.log)" % (n, code))
    rel = os.path.join(rootfs, "etc", "openwrt_release")
    if os.path.exists(rel):
        with open(rel) as f:
            for line in f:
                if line.startswith(("DISTRIB_INFO", "DISTRIB_TARGET")):
                    print(line.strip())


# ---------------------------------------------------------------------------
# mcu-dict
# ---------------------------------------------------------------------------


def find_mcu_dict(data):
    for i in range(len(data) - 2):
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                raw = zlib.decompressobj().decompress(data[i:])
                info = json.loads(raw)
            except Exception:
                continue
            if isinstance(info, dict) and "commands" in info:
                return i, info
    return None, None


def cmd_mcu_dict(args):
    with open(args.firmware, "rb") as f:
        data = f.read()
    offset, info = find_mcu_dict(data)
    if info is None:
        sys.exit("no Klipper data dictionary found")
    cfg = info.get("config", {})
    print("offset:    %d" % offset)
    print("version:   %s" % info.get("version"))
    print("mcu:       %s @ %s Hz" % (cfg.get("MCU"), cfg.get("CLOCK_FREQ")))
    print("commands:  %d, responses: %d" % (
        len(info.get("commands", {})), len(info.get("responses", {}))))
    if args.out:
        with open(args.out, "w", newline="\n") as f:
            json.dump(info, f, indent=1, sort_keys=True)
        print("saved:     %s" % args.out)


# ---------------------------------------------------------------------------
# bootimg
# ---------------------------------------------------------------------------

FDT_MAGIC = b"\xd0\x0d\xfe\xed"


def cmd_bootimg(args):
    with open(args.kernel, "rb") as f:
        data = f.read()
    if data[:8] != b"ANDROID!":
        sys.exit("not an Android boot image")
    os.makedirs(args.outdir, exist_ok=True)
    (ksize, _kaddr, _rsize, _raddr, _ssize, _saddr, _taddr, page,
     _hver, _osver) = struct.unpack_from("<10I", data, 8)
    name = data[48:64].rstrip(b"\0").decode(errors="replace")
    cmdline = data[64:576].rstrip(b"\0").decode(errors="replace")
    print("name: %s  page: %d  kernel: %d bytes" % (name, page, ksize))
    print("cmdline: %s" % cmdline)
    kernel = data[page:page + ksize]
    gz = kernel.find(b"\x1f\x8b\x08")
    if gz >= 0:
        vmlinux = zlib.decompressobj(31).decompress(kernel[gz:])
        with open(os.path.join(args.outdir, "vmlinux"), "wb") as f:
            f.write(vmlinux)
        m = re.search(rb"Linux version [\x20-\x7e]+", vmlinux)
        if m:
            print(m.group().decode())
        ik = vmlinux.find(b"IKCFG_ST")
        if ik >= 0:
            cfg = zlib.decompressobj(31).decompress(vmlinux[ik + 8:])
            with open(os.path.join(args.outdir, "kernel.config"), "wb") as f:
                f.write(cfg)
            print("kernel.config: %d bytes" % len(cfg))
    for m in re.finditer(re.escape(FDT_MAGIC), data):
        total = struct.unpack_from(">I", data, m.start() + 4)[0]
        if 64 < total < 1 << 20:
            out = os.path.join(args.outdir, "dtb_%x.dtb" % m.start())
            with open(out, "wb") as f:
                f.write(data[m.start():m.start() + total])
            print("dtb at 0x%x: %d bytes -> %s" % (m.start(), total, out))


# ---------------------------------------------------------------------------
# dtb
# ---------------------------------------------------------------------------


def fdt_parse(blob):
    (_magic, total, off_struct, off_str, _rsv, version, _lcv, _cpu,
     size_str, _size_struct) = struct.unpack_from(">10I", blob, 0)
    blob = blob[:total]
    strings = blob[off_str:off_str + size_str]

    def string_at(off):
        return strings[off:strings.index(b"\0", off)].decode()

    nodes, path, pos = {}, [], off_struct
    while True:
        token = struct.unpack_from(">I", blob, pos)[0]
        pos += 4
        if token == 1:
            end = blob.index(b"\0", pos)
            path.append(blob[pos:end].decode())
            pos = (end + 4) & ~3
            nodes["/".join(path) or "/"] = {}
        elif token == 2:
            path.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from(">II", blob, pos)
            pos += 8
            nodes["/".join(path) or "/"][string_at(nameoff)] = \
                blob[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == 9:
            break
    return version, nodes


def fdt_value(v):
    if v and v[-1] == 0 and all(32 <= c < 127 or c == 0 for c in v):
        return v.rstrip(b"\0").decode().replace("\0", " | ")
    if len(v) % 4 == 0 and len(v) <= 64:
        return "<%s>" % " ".join(
            hex(x) for x in struct.unpack(">%dI" % (len(v) // 4), v))
    return v.hex()


def cmd_dtb(args):
    with open(args.dtb, "rb") as f:
        version, nodes = fdt_parse(f.read())
    print("version %d, %d nodes" % (version, len(nodes)))
    for name, props in nodes.items():
        print(name or "/")
        for key, value in props.items():
            print("    %s = %s" % (key, fdt_value(value)))


# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ota", help="unpack an OTA image")
    p.add_argument("image")
    p.add_argument("outdir")
    p.set_defaults(func=cmd_ota)

    p = sub.add_parser("mcu-dict", help="extract a Klipper data dictionary")
    p.add_argument("firmware")
    p.add_argument("out", nargs="?")
    p.set_defaults(func=cmd_mcu_dict)

    p = sub.add_parser("bootimg", help="split an Android boot image")
    p.add_argument("kernel")
    p.add_argument("outdir")
    p.set_defaults(func=cmd_bootimg)

    p = sub.add_parser("dtb", help="dump a device tree blob")
    p.add_argument("dtb")
    p.set_defaults(func=cmd_dtb)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
