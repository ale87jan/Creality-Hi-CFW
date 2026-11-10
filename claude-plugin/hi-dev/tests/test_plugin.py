"""Offline tests for the hi-dev plugin: python3 -m unittest discover -s claude-plugin/hi-dev/tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
GUARD = PLUGIN / "hooks" / "guard.py"
HIRO = PLUGIN / "scripts" / "hi-ro.sh"
INDEX = PLUGIN / "scripts" / "docs-index.py"
REINDEX = PLUGIN / "hooks" / "reindex.py"


def guard(tool, tool_input, cwd="/tmp", env=None):
    r = subprocess.run(["python3", "-I", str(GUARD)], input=json.dumps(
        {"tool_name": tool, "tool_input": tool_input, "cwd": cwd}),
        capture_output=True, text=True, env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def make_repo(branch):
    d = tempfile.mkdtemp()
    for c in (["init", "-q", "-b", branch], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
              ["commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", "-C", d] + c, check=True)
    return d


class GuardBash(unittest.TestCase):
    def test_commit_on_protected_branch_denied(self):
        for b in ("dev", "main", "main-hi"):
            self.assertEqual(guard("Bash", {"command": "git commit -m 'x'"}, make_repo(b)), "deny")

    def test_commit_on_task_branch_allowed(self):
        self.assertIsNone(guard("Bash", {"command": "git commit -m 'feat: x' -- a.txt"}, make_repo("feat/x")))

    def test_attribution_denied(self):
        self.assertEqual(guard("Bash", {"command": "git commit -m 'x' -m 'Co-Authored-By: a'"},
                               make_repo("feat/x")), "deny")

    def test_blanket_staging_denied(self):
        for c in ("git add -A", "git add .", "git add -u", "git commit -am 'x'", "git -C r add --all"):
            self.assertEqual(guard("Bash", {"command": c}, make_repo("feat/x")), "deny", c)
        self.assertIsNone(guard("Bash", {"command": "git add docs/a.md"}, make_repo("feat/x")))

    def test_push_rules(self):
        self.assertEqual(guard("Bash", {"command": "git push origin dev"}, make_repo("feat/x")), "deny")
        self.assertEqual(guard("Bash", {"command": "git push --force origin feat/x"}, make_repo("feat/x")), "deny")
        self.assertIsNone(guard("Bash", {"command": "git push -u origin feat/x"}, make_repo("feat/x")))

    def test_motor_writes_ask_only_when_reaching_printer(self):
        self.assertEqual(guard("Bash", {"command": "ssh root@h 'echo MOTOR_FLASH_PARAM COMMIT=1'"}), "ask")
        self.assertIsNone(guard("Bash", {"command": "grep -rn ENCODER_CALIBRATE docs/"}))

    def test_ruleset_change_asks(self):
        self.assertEqual(guard("Bash", {"command": "gh api -X DELETE repos/o/r/rulesets/1"}), "ask")
        self.assertIsNone(guard("Bash", {"command": "gh api repos/o/r/rulesets"}))


class GuardReadWrite(unittest.TestCase):
    def test_large_read_denied_unless_limited(self):
        f = Path(tempfile.mkdtemp()) / "big.md"
        f.write_text("x\n" * 1000)
        self.assertEqual(guard("Read", {"file_path": str(f)}), "deny")
        self.assertIsNone(guard("Read", {"file_path": str(f), "limit": 50}))
        small = f.with_name("small.md")
        small.write_text("x\n" * 10)
        self.assertIsNone(guard("Read", {"file_path": str(small)}))

    def test_private_data_denied_in_tracked_files(self):
        p = "/home/u/hi/Creality-Hi-CFW/docs/a.md"
        self.assertEqual(guard("Write", {"file_path": p, "content": "ssh root@" + ".".join(["10", "1", "2", "3"])}), "deny")
        self.assertIsNone(guard("Write", {"file_path": p, "content": "ssh root@printer"}))
        self.assertIsNone(guard("Write", {"file_path": "/home/u/hi/Creality-Hi-CFW/CLAUDE.local.md",
                                          "content": "192.168.1.5"}))


class HiRo(unittest.TestCase):
    def run_ro(self, *args):
        return subprocess.run(["bash", str(HIRO), "--dry", *args], capture_output=True, text=True,
                              env={**os.environ, "HI_DEV_ENV": "/nonexistent"})

    def test_allowlist(self):
        self.assertEqual(self.run_ro("run", "cat", "/proc/uptime").returncode, 0)
        for bad in (["run", "rm", "-rf", "/"], ["run", "cat", "a;reboot"], ["run", "cat", "$(id)"],
                    ["run", "tail", "-f", "/var/log/x"], ["run", "dmesg", "-c"], ["run", "fw_setenv", "a", "b"]):
            self.assertNotEqual(self.run_ro(*bad).returncode, 0, bad)

    def test_moonraker_allowlist(self):
        self.assertEqual(self.run_ro("moon", "/printer/query_endstops/status").returncode, 0)
        self.assertEqual(self.run_ro("moon", "/printer/objects/query?toolhead&extruder").returncode, 0)
        for bad in ("/printer/gcode/script?script=G28", "/printer/print/start", "/printer/emergency_stop",
                    "/machine/reboot"):
            self.assertNotEqual(self.run_ro("moon", bad).returncode, 0, bad)


class DocsIndex(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        d = self.root / "docs"
        d.mkdir()
        (d / "a.md").write_text("# Alpha\n\nFirst paragraph of alpha.\n")
        (d / "roadmap.md").write_text("# Hoja\n\n## Fase 1\n\n- [x] one\n- [ ] two\n")
        (d / "decisions.md").write_text(
            "# Decisiones\n\n## D1 — First (2026-01-01)\n\n**Decisión.** Use A.\n\n**Consecuencias.** None.\n\n"
            "## D2 — Second\n\n**Decisión.** Use B.\n")

    def run_idx(self, *args):
        return subprocess.run(["python3", "-I", str(INDEX), "--root", str(self.root), *args],
                              capture_output=True, text=True)

    def test_build_check_and_decision(self):
        self.assertEqual(self.run_idx().returncode, 0)
        text = (self.root / "docs/INDEX.md").read_text()
        for needle in ("Alpha", "First paragraph of alpha.", "D1 — First", "Use B.", "Fase 1: 1/2"):
            self.assertIn(needle, text)
        self.assertEqual(self.run_idx("--check").returncode, 0)
        (self.root / "docs/a.md").write_text("# Alpha\n\nChanged.\n")
        self.assertNotEqual(self.run_idx("--check").returncode, 0)
        r = self.run_idx("--decision", "D2")
        self.assertIn("Use B.", r.stdout)
        self.assertNotIn("Use A.", r.stdout)

    def test_reindex_hook(self):
        self.run_idx()
        doc = self.root / "docs/a.md"
        doc.write_text("# Alpha\n\nNew text.\n")
        subprocess.run(["python3", "-I", str(REINDEX)], input=json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": str(doc)}}), text=True, check=True)
        self.assertIn("New text.", (self.root / "docs/INDEX.md").read_text())


class Manifests(unittest.TestCase):
    def test_json_files_are_valid(self):
        plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(plugin["name"], "hi-dev")
        self.assertRegex(plugin["version"], r"^\d+\.\d+\.\d+$")
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertIn("PreToolUse", hooks)
        market = PLUGIN.parent.parent / ".claude-plugin" / "marketplace.json"
        data = json.loads(market.read_text())
        for entry in data["plugins"]:
            self.assertTrue((market.parent.parent / entry["source"] / ".claude-plugin" / "plugin.json").is_file())


if __name__ == "__main__":
    unittest.main()
