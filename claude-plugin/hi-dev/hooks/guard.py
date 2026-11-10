#!/usr/bin/env python3
"""PreToolUse guard for the Hi project (Bash, Read, Write, Edit).

Reads the hook JSON on stdin and prints a permission decision as JSON:
  deny  - rule is absolute (protected branches, attribution lines, private data in tracked files)
  ask   - the user must approve (motor writes, ruleset changes, large reads are denied with advice)
No output means "no opinion". Standard library only; run with `python3 -I`.
"""
import json
import os
import re
import subprocess
import sys

PROTECTED = {"dev", "main", "main-hi"}
READ_ONLY_REPOS = {"creality-cfs-klipper"}
MAX_READ_LINES = int(os.environ.get("HI_READ_MAX_LINES", "400"))
TEXT_EXT = {".md", ".py", ".cfg", ".txt", ".json", ".log", ".sh", ".c", ".h", ".yaml", ".yml", ".toml"}

MOTOR_WRITE = re.compile(
    r"FLASH_PARAM|ENCODER_CALIBRATE|ELEC_OFFSET_CALIBRATE|MOTOR_CALIBRATE|MOTOR_SYS_PARAM"
    r"|COMMIT=1|SYS_PARAM[^\n]{0,40}(WRITE|SET|APPLY)",
    re.I,
)
REACHES_PRINTER = re.compile(r"\bssh\b|:7125|printer/gcode|gcode/script|hi-ro\.sh|\bscp\b", re.I)
PRIVATE = re.compile(
    r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b"
    r"|_ssh_key|/mnt/c/Users|C:\\Users|/home/[a-z][a-z0-9_-]*/"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
GIT_WRITE = re.compile(r"\bgit\s+(?:-C\s+(\S+)\s+)?(commit|push|merge|rebase|reset|cherry-pick|am)\b")
ATTRIBUTION = re.compile(r"co-authored-by|generated with", re.I)
BLANKET_ADD = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?add\s+(?:-\S+\s+)*(-A|--all|-u|--update|\.)(\s|$|&|;)")
BLANKET_COMMIT = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b[^\n]*\s(-a|-am|--all)(\s|$)")
RULESET_CHANGE = re.compile(
    r"gh\s+api\b(?=[^\n]*rulesets)[^\n]*(?:-X|--method)[ =]*(?:DELETE|PUT|PATCH)", re.I
)


def out(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": "[hi-dev] " + reason,
    }}))
    sys.exit(0)


def git(args, cwd):
    try:
        r = subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def effective_cwd(cmd, cwd, dash_c):
    m = re.match(r"\s*cd\s+(\S+)\s*(?:&&|;)", cmd)
    base = os.path.join(cwd, os.path.expanduser(m.group(1))) if m else cwd
    if dash_c:
        base = os.path.join(base, os.path.expanduser(dash_c))
    return base


def check_bash(cmd, cwd):
    if REACHES_PRINTER.search(cmd) and MOTOR_WRITE.search(cmd):
        out("ask", "this command can write motor parameters or calibrate; it needs the user's explicit approval")
    if RULESET_CHANGE.search(cmd):
        out("ask", "changing or deleting a GitHub ruleset needs the user's approval")
    if BLANKET_ADD.search(cmd) or BLANKET_COMMIT.search(cmd):
        out("deny", "the clone may be shared with another thread: stage and commit explicit paths only "
                    "(git add <file>..., git commit -m ... -- <file>...), never -A, -a, -u or '.'")
    for m in GIT_WRITE.finditer(cmd):
        verb = m.group(2)
        where = effective_cwd(cmd, cwd, m.group(1))
        top = git(["rev-parse", "--show-toplevel"], where)
        if top and os.path.basename(top) in READ_ONLY_REPOS:
            out("deny", "%s is a read-only reference repository" % os.path.basename(top))
        branch = git(["rev-parse", "--abbrev-ref", "HEAD"], where)
        if verb != "push" and branch in PROTECTED:
            out("deny", "git %s on protected branch %s: create a task branch off dev (pr-flow.sh start)" % (verb, branch))
        if verb == "commit" and ATTRIBUTION.search(cmd):
            out("deny", "commits carry no Co-Authored-By or 'Generated with' lines (project rule)")
        if verb == "push":
            tail = cmd[m.end():].split("&&")[0].split(";")[0]
            if re.search(r"(^|\s)(--force\S*|-f)(\s|$)", tail):
                out("deny", "force push is not allowed")
            targets = {t.split(":")[-1] for t in tail.split() if not t.startswith("-")}
            if branch in PROTECTED or targets & PROTECTED:
                out("deny", "direct push to a protected branch: use a task branch and a pull request")


def check_read(ti):
    path = ti.get("file_path", "")
    if ti.get("limit") or ti.get("offset") or ti.get("pages") or ti.get("allow_large"):
        return
    if os.path.splitext(path)[1].lower() not in TEXT_EXT or not os.path.isfile(path):
        return
    try:
        with open(path, "rb") as f:
            lines = sum(1 for _ in f)
    except OSError:
        return
    if lines > MAX_READ_LINES:
        out("deny", "%s has %d lines. Read docs/INDEX.md first, use `docs-index.py --decision Dn`, Grep, "
                    "the hi-reader agent, or Read with offset/limit." % (os.path.basename(path), lines))


def check_write(ti):
    path = ti.get("file_path", "")
    if os.path.basename(path) == "CLAUDE.local.md" or "/hi/" not in path.replace("\\", "/") + "/":
        return
    text = ti.get("content") or ti.get("new_string") or ""
    m = PRIVATE.search(text)
    if m:
        out("deny", "tracked files must not contain private data (printer address, key, PC paths): %r. "
                    "Put it in CLAUDE.local.md." % m.group(0)[:20])


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool == "Bash":
        check_bash(ti.get("command", ""), cwd)
    elif tool == "Read":
        check_read(ti)
    elif tool in ("Write", "Edit"):
        check_write(ti)


if __name__ == "__main__":
    main()
