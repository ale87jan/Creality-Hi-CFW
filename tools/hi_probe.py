#!/usr/bin/env python3
# Read-only hardware probe for the Creality Hi (F018).
#
# Runs on the printer (stock Tina OS, Python 3.9 + pyserial). It never writes
# configuration to any device:
#   mcu-dict : asks a Klipper MCU for its data dictionary ("identify").
#   motors   : reads address and parameters of the closed-loop motor drivers
#              on the RS-485 bus (READ_ADDR and SYS_PARAM read only).
#
# Stop Klipper first (/etc/init.d/klipper stop): the serial ports must be free.
# Run it after a normal boot: stock Klipper assigns the motor addresses and
# pushes the cfg values to the drivers, so the values read should match the cfg.
#
# Usage on the printer:
#   /etc/init.d/klipper stop
#   python3 hi_probe.py mcu-dict /dev/ttyS4 --out /tmp/bed_mcu.json
#   python3 hi_probe.py motors \
#       --cfg /mnt/UDISK/printer_data/config/motor_control.cfg \
#       --out /tmp/motors.json
#   /etc/init.d/klipper start
#
# Serial ports: ttyS2 main MCU, ttyS3 nozzle MCU, ttyS4 bed MCU, ttyS5 RS-485.
#
# The motor parameter id/type table comes from the motor_map.json of
# Jacob10383/k2-plus-custom-firmware (GPLv3), built for motor firmware
# mot2_002_081. The Hi ships mot2_002_071: checking that the ids match is
# the purpose of the "motors" command.
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import argparse
import json
import os
import struct
import sys
import time
import zlib

try:
    import serial
except ImportError:
    sys.exit("pyserial is required (python3 -c 'import serial')")

# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------


def port_users(port):
    """Return the PIDs that have the serial port open."""
    real = os.path.realpath(port)
    users = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fd_dir = "/proc/%s/fd" % pid
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.path.realpath(os.path.join(fd_dir, fd)) == real:
                    users.append(int(pid))
                    break
            except OSError:
                continue
    return users


def process_name(pid):
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            return f.read().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return "?"


def open_port(port, baud, force):
    if os.path.exists("/proc") and not force:
        users = [p for p in port_users(port) if p != os.getpid()]
        if users:
            names = ", ".join("%d (%s)" % (p, process_name(p)) for p in users)
            sys.exit("%s is in use by: %s\nStop Klipper first: "
                     "/etc/init.d/klipper stop" % (port, names))
    dev = serial.Serial(port=port, baudrate=baud, timeout=0.02,
                        bytesize=8, parity="N", stopbits=1,
                        xonxoff=False, rtscts=False, dsrdtr=False)
    dev.reset_input_buffer()
    return dev


# ---------------------------------------------------------------------------
# Klipper MCU protocol (identify only)
# ---------------------------------------------------------------------------

MSG_MIN = 5
MSG_DEST = 0x10
MSG_SEQ_MASK = 0x0F
MSG_SYNC = 0x7E
MSGID_IDENTIFY_RESPONSE = 0
MSGID_IDENTIFY = 1
IDENTIFY_CHUNK = 40


def crc16_ccitt(buf):
    crc = 0xFFFF
    for data in buf:
        data ^= crc & 0xFF
        data ^= (data & 0x0F) << 4
        crc = ((data << 8) | (crc >> 8)) ^ (data >> 4) ^ (data << 3)
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF])


def vlq_encode(v):
    out = bytearray()
    if v >= 0xC000000 or v < -0x4000000:
        out.append((v >> 28) & 0x7F | 0x80)
    if v >= 0x180000 or v < -0x80000:
        out.append((v >> 21) & 0x7F | 0x80)
    if v >= 0x3000 or v < -0x1000:
        out.append((v >> 14) & 0x7F | 0x80)
    if v >= 0x60 or v < -0x20:
        out.append((v >> 7) & 0x7F | 0x80)
    out.append(v & 0x7F)
    return bytes(out)


def vlq_decode(s, pos):
    c = s[pos]
    pos += 1
    v = c & 0x7F
    if (c & 0x60) == 0x60:
        v |= -0x20
    while c & 0x80:
        c = s[pos]
        pos += 1
        v = (v << 7) | (c & 0x7F)
    return v & 0xFFFFFFFF, pos


def klipper_block(seq, payload):
    head = bytes([len(payload) + MSG_MIN, MSG_DEST | (seq & MSG_SEQ_MASK)])
    body = head + payload
    return body + crc16_ccitt(body) + bytes([MSG_SYNC])


def klipper_parse_blocks(buf):
    """Pop complete, valid blocks from buf. Returns list of (seq, payload)."""
    blocks = []
    while buf:
        n = buf[0]
        if n < MSG_MIN or n > 64:
            del buf[0]
            continue
        if len(buf) < n:
            break
        block = bytes(buf[:n])
        if block[-1] != MSG_SYNC or crc16_ccitt(block[:-3]) != block[-3:-1]:
            del buf[0]
            continue
        del buf[:n]
        blocks.append((block[1] & MSG_SEQ_MASK, block[2:-3]))
    return blocks


def identify_request(offset):
    return (vlq_encode(MSGID_IDENTIFY) + vlq_encode(offset)
            + vlq_encode(IDENTIFY_CHUNK))


def parse_identify_response(payload):
    msgid, pos = vlq_decode(payload, 0)
    if msgid != MSGID_IDENTIFY_RESPONSE:
        return None
    offset, pos = vlq_decode(payload, pos)
    length = payload[pos]
    return offset, payload[pos + 1:pos + 1 + length]


def cmd_mcu_dict(args):
    dev = open_port(args.port, args.baud, args.force)
    dev.write(bytes([MSG_SYNC]) * 4)
    time.sleep(0.05)
    dev.reset_input_buffer()
    rx = bytearray()
    data = bytearray()
    seq = 0
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        offset = len(data)
        dev.write(klipper_block(seq, identify_request(offset)))
        got = None
        wait_end = time.monotonic() + 0.3
        while time.monotonic() < wait_end and got is None:
            rx.extend(dev.read(256))
            for blk_seq, payload in klipper_parse_blocks(rx):
                # Every MCU block carries the next sequence it expects.
                seq = blk_seq
                if not payload:
                    continue  # plain ack or nak
                parsed = parse_identify_response(payload)
                if parsed and parsed[0] == offset:
                    got = parsed[1]
        if got is None:
            continue
        if not got:
            break
        data.extend(got)
    else:
        sys.exit("timeout: no complete identify data from %s" % args.port)
    dev.close()
    info = json.loads(zlib.decompress(bytes(data)))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(info, f, indent=2, sort_keys=True)
    cfg = info.get("config", {})
    print("port:          %s" % args.port)
    print("version:       %s" % info.get("version"))
    print("build:         %s" % info.get("build_versions"))
    print("mcu:           %s" % cfg.get("MCU"))
    print("clock:         %s" % cfg.get("CLOCK_FREQ"))
    print("commands:      %d" % len(info.get("commands", {})))
    print("responses:     %d" % len(info.get("responses", {})))
    names = sorted(list(info.get("commands", {}))
                   + list(info.get("responses", {})))
    for name in names:
        print("  " + name)
    if args.out:
        print("saved:         %s" % args.out)


# ---------------------------------------------------------------------------
# RS-485 motor drivers (read only)
# ---------------------------------------------------------------------------

PACK_HEAD = 0xF7
FUNC_SYS_PARAM = 0x06
FUNC_READ_ADDR = 0x0E
SUBOP_READ = 0x02
STATUS_BITS = {0x01: "stall", 0x02: "error", 0x04: "warning"}
MOTOR_ADDRS = (0x81, 0x82, 0x83, 0x84, 0x85)

# (value_id, name, type). Source: k2-plus-custom-firmware motor_map.json.
PARAMS = (
    (0, "param_flash_param_version", "uint16_t"),
    (1, "param_boot_key", "uint16_t"),
    (2, "param_flash_key_write_retries_num", "uint16_t"),
    (3, "param_system_startup_delay_ms", "uint16_t"),
    (4, "param_pwm_period_s", "float"),
    (5, "param_task_period_s", "float"),
    (6, "param_use_default_param", "uint16_t"),
    (7, "param_singleturn_control_mode", "uint16_t"),
    (8, "param_elec_angle_calibration_standar_deg", "float"),
    (9, "param_elec_offset", "float"),
    (10, "param_phase_order_invert", "int16_t"),
    (11, "param_emergency_pin_mode", "uint16_t"),
    (12, "param_stall_mode", "uint16_t"),
    (13, "param_stall_cur_A", "float"),
    (14, "param_stall_pos_err_rad", "float"),
    (20, "param_ud_cal_set", "float"),
    (21, "param_motion_dir", "float"),
    (23, "param_encoder_calibtate_official_ud_cal_set", "float"),
    (25, "param_elec_offset_err_deg", "float"),
    (26, "driver_board_param_power_supply_V", "float"),
    (28, "driver_board_param_amp_gain", "float"),
    (30, "driver_board_param_R_of_current_sample_ohm", "float"),
    (41, "motor_param_R", "float"),
    (42, "motor_param_L", "float"),
    (43, "motor_param_Ke", "float"),
    (63, "mcu_param_input_pulse_counter_trigger_mode", "uint16_t"),
    (64, "mcu_param_input_pulse_counter_filter_level", "uint16_t"),
    (66, "controller_param_en_feedforward_idiq", "uint16_t"),
    (67, "controller_param_en_feedforward_uduq", "uint16_t"),
    (70, "controller_pos_loop_pid_param_kp", "float"),
    (86, "controller_spd_loop_pid_param_kp", "float"),
    (87, "controller_spd_loop_pid_param_ki", "float"),
    (89, "controller_spd_loop_pid_param_kc", "float"),
    (94, "controller_spd_loop_pid_fal_param_en", "uint16_t"),
    (95, "controller_spd_loop_pid_fal_param_a", "float"),
    (97, "controller_spd_loop_pid_fal_param_zoom", "float"),
    (102, "controller_cur_loop_pid_param_kp", "float"),
    (103, "controller_cur_loop_pid_param_ki", "float"),
    (105, "controller_cur_loop_pid_param_kc", "float"),
    (110, "controller_cur_loop_pid_fal_param_en", "uint16_t"),
    (111, "controller_cur_loop_pid_fal_param_a", "float"),
    (113, "controller_cur_loop_pid_fal_param_zoom", "float"),
    (116, "controller_leso_param_b0k", "float"),
    (117, "controller_leso_param_b0", "float"),
    (118, "controller_leso_param_z3k", "float"),
    (119, "controller_leso_param_wp", "float"),
    (120, "controller_leso_param_ws", "float"),
    (121, "controller_leso_param_wd", "float"),
    (122, "controller_fwc_param_en", "uint16_t"),
    (123, "controller_fwc_param_I_max", "float"),
    (125, "controller_fwc_param_phi_e", "float"),
    (127, "controller_fwc_param_wm_base", "float"),
    (128, "controller_cur_filter_param_en", "uint16_t"),
    (130, "controller_cur_filter_param_fc", "float"),
    (168, "flash_manager_param_checksum_restore_en", "uint16_t"),
    (173, "protection_param_protect_en", "uint16_t"),
    (179, "protection_param_prt_peak_cur_A", "float"),
    (180, "protection_param_prt_continuous_cur_A", "float"),
    (181, "protection_param_prt_continuous_time_s", "float"),
    (182, "protection_param_prt_over_speed_rad_s", "float"),
    (183, "protection_param_prt_over_speed_time_s", "float"),
    (187, "protection_param_prt_track_max_err", "float"),
    (188, "protection_param_prt_track_err_time", "float"),
    (189, "protection_param_power_voltage_min", "float"),
    (190, "protection_param_mcu_temp_max", "float"),
    (191, "protection_err_code_backup", "uint32_t"),
    (192, "protection_warning_code_backup", "uint32_t"),
    (200, "step_controller_param_subdivision", "uint16_t"),
    (217, "zazen_param_zazen_en", "uint16_t"),
    (218, "zazen_param_zazen_trigger_time_s", "float"),
    (220, "zazen_param_zazen_gain_spd_kp", "float"),
    (221, "zazen_param_zazen_gain_spd_ki", "float"),
    (222, "zazen_param_zazen_gain_cur_kp", "float"),
    (223, "zazen_param_zazen_gain_cur_ki", "float"),
    (224, "param_flash_key", "uint16_t"),
    (225, "param_flash_checksum", "uint16_t"),
    (227, "protection_param_prt_continuous_clear_time_s", "float"),
)

TYPE_FORMATS = {"uint16_t": "<H", "int16_t": "<h",
                "uint32_t": "<I", "int32_t": "<i", "float": "<f"}


def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def rs485_frame(addr, func, payload):
    body = bytes([addr, len(payload) + 3, 0x00, func]) + bytes(payload)
    return bytes([PACK_HEAD]) + body + bytes([crc8(body[1:])])


def is_read_only(func, payload):
    """The only requests this tool is allowed to send."""
    if func == FUNC_READ_ADDR:
        return bytes(payload) == bytes([SUBOP_READ])
    if func == FUNC_SYS_PARAM:
        return len(payload) == 2 and payload[0] == SUBOP_READ
    return False


def rs485_extract(buf):
    """Pop one valid frame from buf, or return None."""
    while buf and buf[0] != PACK_HEAD:
        del buf[0]
    if len(buf) < 3:
        return None
    total = buf[2] + 3
    if buf[2] < 3:
        del buf[0]
        return None
    if len(buf) < total:
        return None
    frame = bytes(buf[:total])
    if crc8(frame[2:-1]) != frame[-1]:
        del buf[0]
        return None
    del buf[:total]
    return frame


class Bus:
    def __init__(self, dev, timeout):
        self.dev = dev
        self.timeout = timeout

    def request(self, addr, func, payload):
        if not is_read_only(func, payload):
            raise RuntimeError("refusing non read-only request")
        tx = rs485_frame(addr, func, payload)
        self.dev.reset_input_buffer()
        self.dev.write(tx)
        buf = bytearray()
        end = time.monotonic() + self.timeout
        while time.monotonic() < end:
            buf.extend(self.dev.read(64))
            while True:
                frame = rs485_extract(buf)
                if frame is None:
                    break
                if frame == tx:
                    continue  # local echo of our own request
                if frame[1] == addr and frame[4] == func:
                    return {"status": frame[3], "payload": frame[5:-1]}
        return None


def status_text(status):
    names = [n for bit, n in STATUS_BITS.items() if status & bit]
    unknown = status & ~0x07
    if unknown:
        names.append("unknown=0x%02X" % unknown)
    return ",".join(names) or "ok"


def decode_value(payload, value_type):
    fmt = TYPE_FORMATS[value_type]
    if len(payload) != struct.calcsize(fmt):
        return None, "len %d (%s)" % (len(payload), payload.hex())
    value = struct.unpack(fmt, payload)[0]
    if value_type == "float":
        value = float("%.7g" % value)
    return value, None


def parse_motor_cfg(path):
    """Read x_*/y_* parameter values from a [motor_control] cfg file."""
    expected = {"x": {}, "y": {}}
    in_section = False
    with open(path) as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("["):
                in_section = line.lower() == "[motor_control]"
                continue
            if not in_section or ":" not in line:
                continue
            key, value = [s.strip() for s in line.split(":", 1)]
            axis, _, name = key.partition("_")
            if axis not in expected:
                continue
            try:
                expected[axis][name] = float(value)
            except ValueError:
                pass
    return expected


def values_match(read, want):
    return abs(read - want) <= max(1e-6, abs(want) * 1e-4)


def cmd_motors(args):
    dev = open_port(args.port, args.baud, args.force)
    bus = Bus(dev, args.timeout)
    addrs = [int(a, 0) for a in args.addr] if args.addr else MOTOR_ADDRS
    expected = None
    if args.cfg:
        expected = parse_motor_cfg(args.cfg)
        print("cfg: %s (x: %d values, y: %d values)" % (
            args.cfg, len(expected["x"]), len(expected["y"])))
    report = {}
    for addr in addrs:
        resp = bus.request(addr, FUNC_READ_ADDR, [SUBOP_READ])
        if resp is None:
            print("0x%02X: no answer" % addr)
            continue
        reported = resp["payload"][0] if resp["payload"] else None
        print("0x%02X: answers, reported_addr=%s status=%s" % (
            addr, "0x%02X" % reported if reported is not None else "?",
            status_text(resp["status"])))
        values = {}
        for pid, name, vtype in PARAMS:
            r = bus.request(addr, FUNC_SYS_PARAM, [SUBOP_READ, pid])
            if r is None:
                values[name] = {"id": pid, "error": "no answer"}
                continue
            value, err = decode_value(r["payload"], vtype)
            values[name] = {"id": pid, "value": value, "error": err,
                            "raw": r["payload"].hex()}
        report["0x%02X" % addr] = {"reported_addr": reported,
                                   "status": resp["status"],
                                   "params": values}
        print("  %-5s %-48s %-14s" % ("id", "name", "value"))
        for pid, name, _vtype in PARAMS:
            v = values[name]
            shown = v["error"] if v.get("error") else v["value"]
            print("  %-5d %-48s %-14s" % (pid, name, shown))
        if expected:
            compare(addr, values, expected)
    dev.close()
    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print("saved: %s" % args.out)


def compare(addr, values, expected):
    for axis in ("x", "y"):
        ok, bad = 0, []
        for name, want in sorted(expected[axis].items()):
            v = values.get(name)
            if v is None or v.get("error") or v.get("value") is None:
                continue
            if values_match(v["value"], want):
                ok += 1
            else:
                bad.append("%s read=%s cfg=%s" % (name, v["value"], want))
        total = ok + len(bad)
        print("  vs cfg %s: %d/%d match" % (axis.upper(), ok, total))
        for line in bad:
            print("    differs: " + line)


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Read-only probe for Creality Hi MCUs and motor drivers")
    parser.add_argument("--force", action="store_true",
                        help="skip the 'port in use' check")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("mcu-dict", help="dump a Klipper MCU data dictionary")
    p.add_argument("port", help="e.g. /dev/ttyS4 (bed_mcu)")
    p.add_argument("--baud", type=int, default=230400)
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--out", help="save the dictionary as JSON")
    p.set_defaults(func=cmd_mcu_dict)

    p = sub.add_parser("motors", help="read motor driver address/params")
    p.add_argument("--port", default="/dev/ttyS5")
    p.add_argument("--baud", type=int, default=230400)
    p.add_argument("--timeout", type=float, default=0.3)
    p.add_argument("--addr", nargs="*", help="addresses (default 0x81-0x85)")
    p.add_argument("--cfg", help="motor_control.cfg to compare against")
    p.add_argument("--out", help="save results as JSON")
    p.set_defaults(func=cmd_motors)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
