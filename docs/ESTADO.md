# Estado

Punto de entrada para retomar el trabajo sin contexto previo. Se actualiza en cada commit.

- **Fase actual:** 1 — Kalico arrancando en la Hi con config mínima ([roadmap.md](roadmap.md)).
- **Plan y análisis:** [phase1-plan.md](phase1-plan.md). **Tareas pequeñas pendientes:** [backlog.md](backlog.md).
- **Última actualización:** 2026-11-10.

## Hecho

| Entregable | Dónde | Verificación |
| - | - | - |
| Cross-compilación reproducible de `c_helper.so` | `scripts/build_chelper.sh`, `scripts/Dockerfile.chelper`, `scripts/chelper_build.py` | Dos builds desde caché vacía dan el mismo SHA-256; carga en ARMv7 emulado con glibc 2.28 (`scripts/chelper_load.py`) |
| Paso 0: inventario de solo lectura de la impresora | `scripts/hi_step0.sh` | Sintaxis y ejecución con `busybox ash` en PC; **falta ejecutarlo en la Hi** |
| Paquete de instalación | `scripts/make_bundle.sh` | Determinista (mismo SHA-256 en dos ejecuciones) |
| Instalación, arranque de sesión y vuelta a stock | `scripts/hi_install.sh`, `scripts/hi_kalico.sh`, `scripts/hi_restore.sh` | `scripts/selftest.sh`: 31 comprobaciones con impresora simulada; **sin probar en la Hi** |
| Config mínima de fase 1 | Creality-Hi-Kalico `config/hi/printer.cfg` | Modo batch contra los diccionarios reales de las tres MCU (`test/test_hi_config.py`) |

| Análisis y plan de la fase 1 | [phase1-plan.md](phase1-plan.md) | Referencias a fichero:línea contrastadas el 2026-11-09 |
| Tareas para continuar | [backlog.md](backlog.md) | — |

Compatibilidad comprobada en PC con las versiones de Python de la Hi: 133 de 134 tests sin diccionarios y la
config mínima en modo batch ([phase1-plan.md §3.2](phase1-plan.md)).

## Siguiente acción

1. **Usuario:** revisar los pull request hacia `dev` (B01).
2. **Usuario:** compilar `c_helper.so` en su PC y ejecutar el paso 0 en la impresora (B03, B02).
3. **Modelo:** analizar `step0.txt` (B02).

Nada se ha ejecutado todavía en la impresora.

El CI del fork está en rojo en el pull request Creality-Hi-Kalico #2 por fallos que ya tiene `dev` (B07); los
tests de la Hi pasan. Arreglarlo es una tarea aparte que necesita decisión del usuario.

## Dónde está el trabajo

- Rama `claude/project-thread-fnrqje` en los dos repos, creada desde `dev` y subida a GitHub el 2026-11-10, con
  pull request hacia `dev` en cada uno.
- Fork: commit `feat(hi): add phase 1 bring-up config with batch tests` (`config/hi/printer.cfg`, `test/hi/`,
  `test/test_hi_config.py`).

## Decisiones

Las tres enviadas el 2026-11-09 se aprobaron el 2026-11-10 con la opción recomendada: D5, D6 y D7 en
[decisions.md](decisions.md). Quedan sin confirmar expresamente las cuatro tomadas por defecto
([phase1-plan.md §10](phase1-plan.md)).
