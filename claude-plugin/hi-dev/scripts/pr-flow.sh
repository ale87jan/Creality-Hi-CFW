#!/usr/bin/env bash
# Git flow D4 in one command each, run inside the target repo.
#   pr-flow.sh start <type/topic>              branch off an up-to-date dev
#   pr-flow.sh ship -m "<title>" [-b "<body>"] -- <file>...   commit ONLY those files, push, open PR into dev
#   pr-flow.sh finish <pr> [--approved]        merge by merge commit, sync dev, drop local branch
# Merging into main or main-hi needs the user's approval: pass --approved only after they gave it.
set -eu

die() { echo "pr-flow: $*" >&2; exit 2; }
PROTECTED=" dev main main-hi "
TYPES="feat|fix|docs|refactor|test|perf|build|ci|chore|revert"
cmd="${1:-}"; [ $# -gt 0 ] && shift

case "$cmd" in
  start)
    name="${1:-}"
    [[ "$name" =~ ^($TYPES)/[a-z0-9][a-z0-9._-]*$ ]] || die "branch must look like type/topic (types: $TYPES)"
    git fetch -q --prune origin
    git switch -q dev
    git pull -q --ff-only
    git switch -q -c "$name"
    echo "on $name (from dev $(git rev-parse --short HEAD))"
    ;;
  ship)
    title=""; body=""; files=()
    while [ $# -gt 0 ]; do
      case "$1" in
        -m) title="$2"; shift 2 ;;
        -b) body="$2"; shift 2 ;;
        --) shift; files=("$@"); break ;;
        *) die "unknown option: $1" ;;
      esac
    done
    br=$(git rev-parse --abbrev-ref HEAD)
    case "$PROTECTED" in *" $br "*) die "refusing to commit on protected branch $br" ;; esac
    [[ "$title" =~ ^($TYPES)(\([a-z0-9_-]+\))?!?:\ .+ ]] || die "title must be a Conventional Commit"
    [ "${#title}" -le 72 ] || die "title longer than 72 characters"
    if printf '%s\n%s' "$title" "$body" | grep -qiE 'co-authored-by|generated with'; then
      die "no Co-Authored-By or 'Generated with' lines"
    fi
    # The clone may be shared with another thread: commit only the listed paths, never `git add -A`.
    [ "${#files[@]}" -ge 1 ] || die "list the files to commit after --"
    git add -- "${files[@]}"
    if [ -n "$body" ]; then git commit -q -m "$title" -m "$body" -- "${files[@]}"
    else git commit -q -m "$title" -- "${files[@]}"; fi
    git push -q -u origin "$br"
    gh pr create --base dev --title "$title" --body "${body:-$title}" | tail -1
    ;;
  finish)
    pr="${1:-}"; shift || true
    [[ "$pr" =~ ^[0-9]+$ ]] || die "finish needs a PR number"
    approved=0; [ "${1:-}" = "--approved" ] && approved=1
    base=$(gh pr view "$pr" --json baseRefName --jq .baseRefName)
    if [ "$base" != "dev" ] && [ "$approved" != 1 ]; then
      die "PR #$pr targets $base: needs the user's explicit approval (--approved)"
    fi
    head=$(gh pr view "$pr" --json headRefName --jq .headRefName)
    gh pr merge "$pr" --merge
    git switch -q dev
    git pull -q --ff-only
    git fetch -q --prune origin
    git branch -d "$head" 2>/dev/null || true
    echo "merged #$pr into $base; local dev at $(git rev-parse --short HEAD)"
    ;;
  *) die "usage: pr-flow.sh start <type/topic> | ship -m <title> [-b <body>] -- <file>... | finish <pr> [--approved]" ;;
esac
