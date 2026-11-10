---
name: token-economy
description: Working rules to spend few tokens on the Hi project - which script or cheap agent to use for each recurring task. Read at the start of a session or before a long read.
---

| Need | Use | Not |
| - | - | - |
| Project state of all clones | `scripts/repos-status.sh [--fetch] [--prs]` | several `git status`/`git log` calls |
| What the docs say | `docs/INDEX.md`, then `scripts/docs-index.py --decision Dn`, then Read with offset/limit | reading whole docs (2900+ lines) |
| Long text to digest | agent `hi-reader` (Haiku) | reading it in the main session |
| Printer facts | skill `hi-ro` / agent `hi-ro-runner` (Haiku) | ad-hoc ssh with raw output |
| Check claims or `file:line` refs | agent `hi-verifier` (Sonnet) | re-reading every file yourself |
| Branch, commit, PR, merge | skill `pr-flow` | typing the git/gh sequence |

Habits:
- Deterministic work goes to a script that prints a summary; long jobs run in the background (no polling).
- Haiku by default; Sonnet only to verify or analyse. Ask the user before any Opus agent.
- `docs/INDEX.md` rebuilds itself when a doc is edited with Write/Edit (hook); after edits made through Bash run
  `scripts/docs-index.py`.
- The guard hook denies large reads, direct commits on `dev`/`main`/`main-hi`, blanket `git add -A`, and asks
  before motor-parameter writes: when it says no, follow its advice instead of retrying.
