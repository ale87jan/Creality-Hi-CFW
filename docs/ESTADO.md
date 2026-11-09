# Estado

Punto de entrada para retomar el trabajo sin contexto previo. Se actualiza en cada commit.

- **Fase actual:** 1 — Kalico arrancando en la Hi con config mínima ([roadmap.md](roadmap.md)).
- **Plan y análisis:** [phase1-plan.md](phase1-plan.md). **Tareas pequeñas pendientes:** [backlog.md](backlog.md).
- **Última actualización:** 2026-11-09.

## Hecho

| Entregable | Dónde | Verificación |
| - | - | - |
| Cross-compilación reproducible de `c_helper.so` | `scripts/build_chelper.sh`, `scripts/Dockerfile.chelper`, `scripts/chelper_build.py` | Dos builds desde caché vacía dan el mismo SHA-256; carga en ARMv7 emulado con glibc 2.28 (`scripts/chelper_load.py`) |
| Paso 0: inventario de solo lectura de la impresora | `scripts/hi_step0.sh` | Sintaxis y ejecución con `busybox ash` en PC; **falta ejecutarlo en la Hi** |
| Paquete de instalación | `scripts/make_bundle.sh` | Determinista (mismo SHA-256 en dos ejecuciones) |
| Instalación, arranque de sesión y vuelta a stock | `scripts/hi_install.sh`, `scripts/hi_kalico.sh`, `scripts/hi_restore.sh` | `scripts/selftest.sh`: 31 comprobaciones con impresora simulada; **sin probar en la Hi** |
| Config mínima de fase 1 | Creality-Hi-Kalico `config/hi/printer.cfg` | Modo batch contra los diccionarios reales de las tres MCU (`test/test_hi_config.py`) |

## Siguiente acción

Pendiente de escribir: `docs/phase1-plan.md` y `docs/backlog.md` (en curso en esta misma rama).

## Decisiones pendientes del usuario

Enviadas el 2026-11-09 (se trabaja con la opción recomendada mientras tanto):

1. Cómo se instala Kalico en fase 1 (recomendada: escalonada, sin escribir en flash).
2. De dónde sale `c_helper.so` (recomendada: artefacto del paquete de instalación).
3. Interfaz en fase 1 (recomendada: consola SSH y después Fluidd).
