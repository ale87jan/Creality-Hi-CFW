#!/usr/bin/env python3
"""PostToolUse hook: rebuild docs/INDEX.md when a doc under docs/ is written or edited.

Deterministic script, no model involved, no output (zero tokens). Standard library only.
"""
import json
import os
import subprocess
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    path = (data.get("tool_input") or {}).get("file_path", "")
    if not path.endswith(".md") or os.path.basename(path) == "INDEX.md":
        return
    parts = os.path.abspath(path).split(os.sep)
    if "docs" not in parts:
        return
    root = os.sep.join(parts[: len(parts) - 1 - parts[::-1].index("docs")]) or os.sep
    if not os.path.isfile(os.path.join(root, "docs", "INDEX.md")):
        return  # only repos that already have an index
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "docs-index.py")
    subprocess.run([sys.executable, "-I", script, "--root", root], capture_output=True, timeout=20)


if __name__ == "__main__":
    main()
