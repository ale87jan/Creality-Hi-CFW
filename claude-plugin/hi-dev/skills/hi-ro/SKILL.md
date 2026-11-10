---
name: hi-ro
description: Read-only queries to the Hi printer (SSH allowlist and Moonraker GET) with capped output. Use to collect printer facts without raw dumps; delegate to the hi-ro-runner agent when there are several queries.
---

Setup, once per machine (never committed): create `~/.config/hi-dev/env` with `HI_HOST=user@address` and
`HI_KEY=/path/to/key` (the values are in `CLAUDE.local.md`).

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts/hi-ro.sh"
$S run fw_printenv version
$S run cat /proc/uptime
$S moon /printer/query_endstops/status
$S --max 1500 moon "/printer/objects/query?toolhead&extruder"
```

- Allowed: `cat ls df uname uptime free ps head tail wc stat grep fw_printenv dmesg date id md5sum sha256sum`, no
  shell metacharacters, no follow/clear flags. Moonraker: info, objects list/query, endstop status, G-code help,
  server info/config/files/history. Nothing that moves, heats or runs G-code.
- Anything else (motors, parameter writes, G-code) is not read-only: ask the user first.
- For three or more queries, launch the `hi-ro-runner` agent (Haiku) and use only its report.
