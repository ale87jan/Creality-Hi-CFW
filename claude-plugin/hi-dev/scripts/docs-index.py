#!/usr/bin/env python3
"""Build docs/INDEX.md: a short map of docs/ so sessions need not read whole documents.

Usage (run from the repo root, or pass --root):
  docs-index.py              write docs/INDEX.md
  docs-index.py --check      exit 1 if docs/INDEX.md is out of date
  docs-index.py --decision D12   print one decision section from docs/decisions.md
"""
import argparse
import re
import sys
from pathlib import Path

SUMMARY_LEN = 200


def clean(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def cut(text, n=SUMMARY_LEN):
    text = clean(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def doc_summary(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    title, para = path.stem, []
    for ln in lines:
        if ln.startswith("# ") and title == path.stem:
            title = ln[2:].strip()
        elif ln.strip() and not ln.startswith(("#", "|", "-", ">", "`")) and title != path.stem:
            para.append(ln.strip())
        elif para:
            break
    return title, len(lines), cut(" ".join(para)) if para else ""


def decisions(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## (?=D\d+ )", text)[1:]
    rows = []
    for part in parts:
        head, _, body = part.partition("\n")
        m = re.search(r"\*\*Decisión\.\*\*\s*(.+?)(?:\n\n|\Z)", body, re.S)
        rows.append((head.strip(), cut(m.group(1)) if m else ""))
    return rows


def roadmap(path):
    rows, cur = [], None
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## "):
            cur = [ln[3:].strip(), 0, 0]
            rows.append(cur)
        elif cur and re.match(r"\s*- \[( |x)\]", ln):
            cur[2] += 1
            cur[1] += ln.strip().startswith("- [x]")
    return [(t, d, n) for t, d, n in rows if n]


def build(root):
    docs = root / "docs"
    out = ["# Índice de docs", "",
           "Generado por `claude-plugin/hi-dev/scripts/docs-index.py`; no editar a mano. "
           "Lee esto primero y abre el documento completo solo si hace falta.", "",
           "## Documentos", "", "| Doc | Líneas | Resumen |", "| - | - | - |"]
    for p in sorted(docs.rglob("*.md")):
        if p.name == "INDEX.md":
            continue
        title, n, summ = doc_summary(p)
        out.append("| [%s](%s) | %d | %s |" % (title.replace("|", "/"), p.relative_to(docs).as_posix(), n,
                                               summ.replace("|", "/")))
    dec = docs / "decisions.md"
    if dec.exists():
        out += ["", "## Decisiones", ""]
        out += ["- **%s**%s" % (h, (": " + s) if s else "") for h, s in decisions(dec)]
        out += ["", "Detalle de una: `docs-index.py --decision D12`."]
    rm = docs / "roadmap.md"
    if rm.exists():
        out += ["", "## Hoja de ruta (casillas hechas / total)", ""]
        out += ["- %s: %d/%d" % r for r in roadmap(rm)]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--decision")
    a = ap.parse_args()
    root = Path(a.root)
    if a.decision:
        text = (root / "docs/decisions.md").read_text(encoding="utf-8")
        m = re.search(r"(?ms)^## %s .*?(?=^## D\d+ |\Z)" % re.escape(a.decision), text)
        if not m:
            sys.exit("decision %s not found" % a.decision)
        print(m.group(0).rstrip())
        return
    new = build(root)
    idx = root / "docs/INDEX.md"
    if a.check:
        if not idx.exists() or idx.read_text(encoding="utf-8") != new:
            sys.exit("docs/INDEX.md is out of date: run docs-index.py")
        return
    idx.write_text(new, encoding="utf-8")
    print("wrote %s (%d lines)" % (idx, new.count("\n")))


if __name__ == "__main__":
    main()
