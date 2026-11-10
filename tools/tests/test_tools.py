# Offline tests for tools/hi_probe.py, tools/fwextract.py and tools/cfg_commands.py.
# Run from the repo root: python -m unittest discover -s tools/tests -v
#
# hi_probe needs pyserial to import; the serial port itself is faked.

import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import types
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fwextract  # noqa: E402
import hi_probe as hp  # noqa: E402

DICT_DIR = os.path.join(ROOT, "data", "derived", "mcu-dictionaries", "hi")
CAPTURE = os.path.join(ROOT, "data", "captures", "2026-11-09_hi-v1.1.0.60",
                       "motors.json")


class FakeMCU:
    """Klipper MCU that answers identify and enforces sequence numbers."""

    def __init__(self, info):
        self.data = zlib.compress(json.dumps(info).encode())
        self.next_seq = 7
        self.out = bytearray()
        self.inp = bytearray()

    def write(self, b):
        self.inp.extend(b)
        for seq, payload in hp.klipper_parse_blocks(self.inp):
            if seq != self.next_seq:
                self.out.extend(hp.klipper_block(self.next_seq, b""))  # nak
                continue
            self.next_seq = (self.next_seq + 1) & 0xF
            _msgid, pos = hp.vlq_decode(payload, 0)
            off, pos = hp.vlq_decode(payload, pos)
            cnt, pos = hp.vlq_decode(payload, pos)
            chunk = self.data[off:off + cnt]
            resp = (hp.vlq_encode(0) + hp.vlq_encode(off)
                    + bytes([len(chunk)]) + chunk)
            self.out.extend(hp.klipper_block(self.next_seq, resp))

    def read(self, n):
        b = bytes(self.out[:n])
        del self.out[:n]
        return b

    def reset_input_buffer(self):
        self.out.clear()

    def close(self):
        pass


class FakeBus:
    """RS-485 bus with local echo, replaying values captured on the printer."""

    def __init__(self, capture):
        self.capture = capture
        self.out = bytearray()
        self.sent = []

    def write(self, b):
        self.sent.append(bytes(b))
        self.out.extend(b)  # local echo
        frame = hp.rs485_extract(bytearray(b))
        addr, func, payload = frame[1], frame[4], frame[5:-1]
        motor = self.capture.get("0x%02X" % addr)
        if motor is None:
            return
        if func == hp.FUNC_READ_ADDR:
            pl = bytes([addr])
        else:
            pid = payload[1]
            name = [n for i, n, _t in hp.PARAMS if i == pid][0]
            pl = bytes.fromhex(motor["params"][name]["raw"])
        body = bytes([addr, len(pl) + 3, 0x00, func]) + pl
        self.out.extend(bytes([0xF7]) + body + bytes([hp.crc8(body[1:])]))

    read = FakeMCU.read
    reset_input_buffer = FakeMCU.reset_input_buffer
    close = FakeMCU.close


class HiProbeTest(unittest.TestCase):
    def test_crc_and_vlq(self):
        self.assertEqual(hp.crc8(b"123456789"), 0xF4)  # CRC-8/SMBUS check
        # Klipper's crc16_ccitt is CRC-16/MCRF4XX: check value 0x6F91.
        self.assertEqual(hp.crc16_ccitt(b"123456789"), b"\x6f\x91")
        for v in (0, 1, 0x5F, 0x60, 0x2FFF, 0x3000, 123456, 0x180000,
                  2 ** 31, 2 ** 32 - 1):
            self.assertEqual(hp.vlq_decode(hp.vlq_encode(v), 0)[0],
                             v & 0xFFFFFFFF)

    def test_read_only_guard(self):
        self.assertTrue(hp.is_read_only(0x0E, [2]))
        self.assertTrue(hp.is_read_only(0x06, [2, 41]))
        for func, payload in ((0x06, [1, 41, 0, 0, 0, 0]), (0x07, [5]),
                              (0x0E, [1]), (0x11, [2]), (0x0C, [5])):
            self.assertFalse(hp.is_read_only(func, payload))
            with self.assertRaises(RuntimeError):
                hp.Bus(None, 0.1).request(0x81, func, payload)

    def test_identify(self):
        path = os.path.join(DICT_DIR, "mcu0_110_G32-mcu0_020_000.json")
        with open(path) as f:
            info = json.load(f)
        fake = FakeMCU(info)
        hp.serial.Serial = lambda **kw: fake
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dict.json")
            args = types.SimpleNamespace(port="fake", baud=230400, force=True,
                                         timeout=5, out=out)
            with contextlib.redirect_stdout(io.StringIO()):
                hp.cmd_mcu_dict(args)
            with open(out) as f:
                self.assertEqual(json.load(f), info)

    def test_motors_replay(self):
        with open(CAPTURE) as f:
            capture = json.load(f)
        bus = FakeBus(capture)
        hp.serial.Serial = lambda **kw: bus
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "motors.json")
            args = types.SimpleNamespace(port="fake", baud=230400, force=True,
                                         timeout=0.05, addr=None, cfg=None,
                                         out=out)
            with contextlib.redirect_stdout(io.StringIO()):
                hp.cmd_motors(args)
            with open(out) as f:
                result = json.load(f)
        self.assertEqual(sorted(result), ["0x81", "0x82"])
        for addr in ("0x81", "0x82"):
            for name, entry in result[addr]["params"].items():
                self.assertEqual(entry["value"],
                                 capture[addr]["params"][name]["value"], name)
        for frame in bus.sent:
            self.assertTrue(hp.is_read_only(frame[4], frame[5:-1]))


class FwExtractTest(unittest.TestCase):
    def test_find_mcu_dict(self):
        info = {"commands": {"identify offset=%u count=%c": 1}, "version": "x"}
        blob = b"\x00" * 100 + b"\x78\x9c" + b"\x11" * 50
        blob += zlib.compress(json.dumps(info).encode()) + b"\xff" * 20
        offset, found = fwextract.find_mcu_dict(blob)
        self.assertEqual(found, info)
        self.assertGreater(offset, 100)

    def test_fdt_roundtrip(self):
        # Minimal FDT: root node with one string property.
        strings = b"model\0"
        prop = b"hi\0\0"
        struct_blk = (struct.pack(">I", 1) + b"\0\0\0\0"
                      + struct.pack(">III", 3, 3, 0) + prop
                      + struct.pack(">II", 2, 9))
        off_struct = 40
        off_str = off_struct + len(struct_blk)
        total = off_str + len(strings)
        header = struct.pack(">10I", 0xD00DFEED, total, off_struct, off_str,
                             40, 17, 16, 0, len(strings), len(struct_blk))
        _ver, nodes = fwextract.fdt_parse(header + struct_blk + strings)
        self.assertEqual(fwextract.fdt_value(nodes["/"]["model"]), "hi")


class CfgCommandsTest(unittest.TestCase):
    def test_reports_missing_commands_and_sections(self):
        import cfg_commands

        with tempfile.TemporaryDirectory() as tmp:
            cfg = os.path.join(tmp, "printer.cfg")
            with open(cfg, "w") as stream:
                stream.write(
                    "[stepper_x]\n[timer_read]\n[probe]\n"
                    "[gcode_macro PAUSE]\nrename_existing: _PAUSE_BASE\n"
                    "gcode:\n  _PAUSE_BASE\n  FORCE_MOVE_E S=1\n"
                    "  # CXSAVE_CONFIG\n  {% if x %}\n  QUERY_PROBE\n"
                    "  MY_MACRO\n[gcode_macro my_macro]\ngcode:\n  G28\n"
                )
            extras = os.path.join(tmp, "klippy", "extras")
            os.makedirs(extras)
            with open(os.path.join(extras, "probe.py"), "w") as stream:
                stream.write('register("QUERY_PROBE", f)\nregister("G28", g)\n')
            commands, sections = cfg_commands.missing(
                [cfg], os.path.join(tmp, "klippy")
            )
        self.assertEqual(commands, [("FORCE_MOVE_E", 1, "printer.cfg")])
        self.assertEqual(sections, ["timer_read"])


if __name__ == "__main__":
    unittest.main()
