#!/usr/bin/env bash
# Compact status of the project clones under $HI_ROOT (default ~/hi).
# Usage: repos-status.sh [--fetch] [--prs]
#   --fetch  git fetch --all --prune first
#   --prs    also list open pull requests (needs gh)
set -u
root="${HI_ROOT:-$HOME/hi}"
fetch=0; prs=0
for a in "$@"; do
  case "$a" in --fetch) fetch=1 ;; --prs) prs=1 ;; *) echo "unknown option: $a" >&2; exit 2 ;; esac
done
for d in "$root"/*/; do
  [ -e "$d/.git" ] || continue
  n=$(basename "$d")
  [ "$fetch" = 1 ] && git -C "$d" fetch --all --prune -q 2>/dev/null
  br=$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)
  up=$(git -C "$d" rev-parse --abbrev-ref '@{u}' 2>/dev/null || true)
  a="?"; b="?"
  if [ -n "$up" ]; then
    read -r a b < <(git -C "$d" rev-list --left-right --count "HEAD...$up")
  fi
  dirty=$(git -C "$d" status --porcelain | wc -l)
  printf '%-22s %-30s ahead=%s behind=%s dirty=%s\n' "$n" "$br" "$a" "$b" "$dirty"
  stale=$(git -C "$d" branch -vv | grep ': gone\]' | awk '{print $1=="*"?$2:$1}' | tr '\n' ' ')
  [ -n "$stale" ] && echo "  stale local branches (remote gone): $stale"
  if [ "$prs" = 1 ] && command -v gh >/dev/null; then
    (cd "$d" && gh pr list --json number,title,headRefName,baseRefName \
      --jq '.[] | "  PR #\(.number) \(.headRefName)->\(.baseRefName): \(.title)"' 2>/dev/null)
  fi
done
exit 0
