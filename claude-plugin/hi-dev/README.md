# Plugin `hi-dev`

Herramientas para gastar pocos tokens en este proyecto (decisión D20). Todo lo determinista va en scripts; la
lectura larga, en subagentes baratos.

| Pieza | Qué hace |
| - | - |
| `scripts/repos-status.sh` | Estado de todos los clones (rama, ahead/behind, sucios, ramas muertas, PR abiertos) |
| `scripts/hi-ro.sh` | SSH y Moonraker de solo lectura a la Hi, con lista blanca y salida recortada |
| `scripts/pr-flow.sh` | Rama, commit **solo de los ficheros indicados**, PR y fusión hacia `dev` |
| `scripts/docs-index.py` | Genera `docs/INDEX.md`; `--check`, `--decision Dn` |
| `hooks/guard.py` | Deniega commits en `dev`/`main`/`main-hi`, `git add -A`, lecturas enormes, datos privados en ficheros versionados; pregunta antes de escrituras de motor y cambios de rulesets |
| `hooks/reindex.py` | Regenera `docs/INDEX.md` al editar un doc con Write/Edit |
| `hooks/session_brief.sh` | Resumen de unas 12 líneas al empezar la sesión |
| `agents/` | `hi-reader` (Haiku), `hi-ro-runner` (Haiku), `hi-verifier` (Sonnet) |
| `skills/` | `pr-flow`, `hi-ro`, `token-economy` |

Instalación (la config privada va en `~/.config/hi-dev/env`, nunca en el repo):

```bash
claude plugin marketplace add ale87jan/Creality-Hi-CFW
claude plugin install hi-dev@creality-hi
```

Pruebas offline: `python3 -m unittest discover -s claude-plugin/hi-dev/tests`.
