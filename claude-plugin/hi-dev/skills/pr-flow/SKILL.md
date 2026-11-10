---
name: pr-flow
description: Git flow D4 for the Hi repos in three scripted steps (branch off dev, commit only listed files and open the PR, merge and clean up). Use for any change that must reach dev, instead of typing the git/gh sequence.
disable-model-invocation: true
---

Run inside the target repo. The clone may be shared with another thread: commit **only** the files you edited.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts/pr-flow.sh"
$S start docs/topic                                   # fetch, dev up to date, new branch
$S ship -m "docs(scope): title" -b "why" -- file1 file2   # commit ONLY those paths, push, PR into dev
$S finish 12                                          # merge commit, sync dev, delete local branch
```

- Prefer a separate worktree (`git worktree add ~/hi/wt-<topic> <branch>`) when another thread works in the clone.
- `finish` refuses PRs that target `main`/`main-hi`; those need the user's explicit approval (`--approved`).
- Titles are Conventional Commits, <= 72 chars, English, no `Co-Authored-By` or "Generated with".
- Only the output of the script enters the context; do not re-run `git status`/`git log` to confirm.
