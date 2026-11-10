#!/usr/bin/env bash
# SessionStart hook: print a short project brief (stdout becomes session context).
# Local-only and cheap: no network, no fetch.
set -u
root="${HI_ROOT:-$HOME/hi}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[hi-dev] Project brief (token saver)"
"$here/scripts/repos-status.sh" 2>/dev/null | head -8
estado="$root/Creality-Hi-CFW/docs/ESTADO.md"
if [ -f "$estado" ]; then
  # Only the phase number and where the detail lives; the full text stays in the file.
  ln=$(grep -n -m1 -E '^- \*\*Fase actual' "$estado" | cut -d: -f1)
  if [ -n "$ln" ]; then
    ph=$(sed -n "${ln}p" "$estado" | sed -E 's/^- \*\*Fase actual:\*\* *([0-9]+).*/\1/')
    echo "Fase actual: $ph -> detalle en docs/ESTADO.md:$ln (Read con offset/limit)"
  fi
fi
if [ -f "$root/Creality-Hi-CFW/docs/INDEX.md" ]; then
  (cd "$root/Creality-Hi-CFW" && python3 -I "$here/scripts/docs-index.py" --check 2>/dev/null) \
    || echo "WARNING: docs/INDEX.md is stale (run scripts/docs-index.py; it is also rebuilt when docs are edited)"
fi
cat <<'EOF'
Rules: read docs/INDEX.md first, not whole docs; use scripts/ and cheap subagents (hi-reader,
hi-ro-runner, hi-verifier) for reads and checks; see skill hi-dev:token-economy.
EOF
exit 0
