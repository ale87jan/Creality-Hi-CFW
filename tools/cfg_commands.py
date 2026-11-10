#!/usr/bin/env python3
# List the G-code commands and config sections of a Klipper config that a
# Klipper/Kalico source tree does not provide.
#
# Offline and read-only: it parses text files, it never imports or runs them.
# It is a heuristic to plan the macro port, not a parser:
#   - a command is the first word of a macro line (letters, digits, "_");
#   - a command is "known" when its name is defined as a macro in the config
#     or appears as a quoted upper-case string anywhere in the klippy sources.
# Expect a few false positives (rename_existing targets) and misses.
#
# Usage:
#   python -I tools/cfg_commands.py <config dir> <klippy dir>
#   python -I tools/cfg_commands.py data/captures/<capture>/printer-config \
#       ../Creality-Hi-Kalico/klippy

import argparse
import collections
import glob
import os
import re

SECTION_RE = re.compile(r"\[([^\]]+)\]")
COMMAND_RE = re.compile(r"([A-Z_][A-Z_0-9]{2,})\b")
QUOTED_RE = re.compile(r"[\"']([A-Z_][A-Z_0-9]{2,})[\"']")
RENAME_RE = re.compile(r"rename_existing\s*[:=]\s*(\S+)")
# Sections handled by the Klipper core rather than by an extras module.
CORE_SECTIONS = {"printer", "mcu", "extruder", "include", "gcode_macro"}


def scan_config(paths):
    """Return (macros, renamed, sections, used) found in the cfg files.

    used maps a command to (count, first file that uses it).
    """
    macros, renamed, sections = set(), set(), set()
    used = collections.OrderedDict()
    for path in sorted(paths):
        section = None
        with open(path, errors="replace") as stream:
            for line in stream:
                match = SECTION_RE.match(line)
                if match:
                    section = match.group(1).strip()
                    sections.add(section.split()[0])
                    if section.startswith("gcode_macro "):
                        macros.add(section.split()[1].upper())
                    continue
                rename = RENAME_RE.match(line.strip())
                if rename:
                    renamed.add(rename.group(1).upper())
                if section is None or line[:1] not in " \t":
                    continue
                text = line.strip()
                if text.startswith(("#", ";", "{")):
                    continue
                match = COMMAND_RE.match(text)
                if match:
                    name = match.group(1)
                    count, first = used.get(name, (0, os.path.basename(path)))
                    used[name] = (count + 1, first)
    return macros, renamed, sections, used


def scan_klippy(klippy_dir):
    """Return (names, modules): quoted upper-case names and extras modules."""
    names, modules = set(), set()
    pattern = os.path.join(klippy_dir, "**", "*.py")
    for path in glob.glob(pattern, recursive=True):
        with open(path, errors="replace") as stream:
            names.update(QUOTED_RE.findall(stream.read()))
    extras = os.path.join(klippy_dir, "extras")
    for entry in os.listdir(extras) if os.path.isdir(extras) else []:
        full = os.path.join(extras, entry)
        if entry.endswith(".py"):
            modules.add(entry[:-3])
        elif os.path.isdir(full):
            modules.add(entry)
    return names, modules


def missing(config_paths, klippy_dir):
    macros, renamed, sections, used = scan_config(config_paths)
    names, modules = scan_klippy(klippy_dir)
    commands = [
        (name, count, first)
        for name, (count, first) in used.items()
        if name not in names and name not in macros and name not in renamed
    ]
    commands.sort(key=lambda item: (-item[1], item[0]))
    lost_sections = sorted(
        s
        for s in sections
        if s not in modules
        and s not in CORE_SECTIONS
        and not s.startswith("stepper_")
    )
    return commands, lost_sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_dir")
    parser.add_argument("klippy_dir")
    args = parser.parse_args()
    paths = glob.glob(os.path.join(args.config_dir, "*.cfg"))
    commands, sections = missing(paths, args.klippy_dir)
    print("Commands not provided (%d):" % len(commands))
    for name, count, first in commands:
        print("  %-36s %3d  %s" % (name, count, first))
    print("Sections without module (%d):" % len(sections))
    for name in sections:
        print("  %s" % name)


if __name__ == "__main__":
    main()
