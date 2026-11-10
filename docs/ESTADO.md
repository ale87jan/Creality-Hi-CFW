# Estado

Punto de entrada para retomar el trabajo sin contexto previo. Se actualiza en cada commit.

- **Fase actual:** 1 **validada en la Hi el 2026-11-10** (instalación, arranque, calentadores, Z, extrusor,
  Fluidd y vuelta a stock; [phase1-plan.md §8.1](phase1-plan.md)). Siguiente: fase 2, lazo cerrado de X/Y
  ([phase2-plan.md](phase2-plan.md)), que empieza en solo lectura ([roadmap.md](roadmap.md)).
- **Plan y análisis:** [phase1-plan.md](phase1-plan.md). **Tareas pequeñas pendientes:** [backlog.md](backlog.md).
- **Última actualización:** 2026-11-10.
- **Ramas protegidas** con rulesets de GitHub en los dos repos ([decisions.md](decisions.md), D19).

## Hecho

| Entregable | Dónde | Verificación |
| - | - | - |
| Cross-compilación reproducible de `c_helper.so` | `scripts/build_chelper.sh`, `scripts/Dockerfile.chelper`, `scripts/chelper_build.py` | Dos builds desde caché vacía dan el mismo SHA-256; carga en ARMv7 emulado con glibc 2.28 (`scripts/chelper_load.py`) |
| Paso 0: inventario de solo lectura de la impresora | `scripts/hi_step0.sh` | Sintaxis y ejecución con `busybox ash` en PC; ejecutado en la Hi el 2026-11-10: [phase1-plan.md §8.1](phase1-plan.md) |
| Paquete de instalación | `scripts/make_bundle.sh` | Determinista (mismo SHA-256 en dos ejecuciones) |
| Instalación, arranque de sesión y vuelta a stock | `scripts/hi_install.sh`, `scripts/hi_kalico.sh`, `scripts/hi_restore.sh` | `scripts/selftest.sh`: 31 comprobaciones con impresora simulada; **sin probar en la Hi** |
| Config mínima de fase 1 | Creality-Hi-Kalico `config/hi/printer.cfg` | Modo batch contra los diccionarios reales de las tres MCU (`test/test_hi_config.py`) |

| Análisis y plan de la fase 1 | [phase1-plan.md](phase1-plan.md) | Referencias a fichero:línea contrastadas el 2026-11-09 |
| Tareas para continuar | [backlog.md](backlog.md) | — |

Compatibilidad comprobada en PC con las versiones de Python de la Hi: 133 de 134 tests sin diccionarios y la
config mínima en modo batch ([phase1-plan.md §3.2](phase1-plan.md)).

## Siguiente acción

1. **Usuario:** revisar los pull request hacia `dev` (B01).
2. **Hecho (2026-11-10):** `c_helper.so` compilado y cargado en la Hi; paso 0 ejecutado (B03, B02).
   Salida en `data/captures/2026-11-10_hi-step0/`. `hi_install.sh --dry-run` correcto.
   Escalón 1 (ficheros en `/mnt/UDISK/kalico-hi`) hecho; **Kalico arrancó en la Hi el 2026-11-10** (escalón 2: `ready` con las tres MCU; drivers, sensores de Z, ventilador, calentadores, Z y extrusor probados; `stop` devuelve a stock). Detalle en [phase1-plan.md §8.1](phase1-plan.md).
3. **Usuario, con el hilo de la guía:** escalones 2 y 3 de [phase1-plan.md §8](phase1-plan.md).

En la impresora se han ejecutado el paso 0, la copia de ficheros del escalón 1 y el arranque del escalón 2.

El CI del fork está en rojo en el pull request Creality-Hi-Kalico #2 por fallos que ya tiene `dev` (B07); los
tests de la Hi pasan. El usuario decidió el 2026-11-10 no tocarlo por ahora.

## Fase 2 (motores X/Y)

Análisis hecho sin impresora el 2026-11-10: [phase2-plan.md](phase2-plan.md). Tareas B15 a B20. Código hecho en el fork (B16 a B19): `motor_control_hi.py` (copia aparte, D8), `motor_map_hi.json`,
`io_remap.py`, `config/hi/phase2.cfg` y 41 tests. Decisiones cerradas (D8, D9, D10). Falta todo lo de la impresora
(B20 y §8 del plan). **Paso 2.1 hecho el 2026-11-10** en stock, solo lectura: Y se lee directo; X solo con `SET_IOREMAP S=1` y comparte línea con Z ([hardware.md](hardware.md)); 2.2 cerrado sin observar el efecto del modo de stall 1 (B20 hecho). 2.3 hecho: Kalico con `startup_writes: none`, 0x81 y 0x82 responden sin fallos (ver [phase2-plan.md](phase2-plan.md) §8). Siguiente: 2.4, `SET_IOREMAP` y `QUERY_ENDSTOPS` en Kalico. Hallazgo principal: la Hi no usa los pines de stall como final
de carrera de X/Y y hay que portar `io_remap.py` en esta fase.

## Fase 3 (sonda)

Análisis ligero hecho el 2026-11-10: [phase3-plan.md](phase3-plan.md). Tareas B21 a B24. El `prtouch.py` de la K2
es compatible con la Hi sin tocar código y carga en batch con los diccionarios reales. Config y tests hechos
(B22): `config/hi/phase3.cfg`, con `config/hi/` repartido en `base.cfg` y `motors.cfg`; el paquete lleva ahora
todos los `.cfg` y `HI_CONFIG` elige cuál arranca. Decisión 1 del §7 cerrada (D11: módulo de la K2 tal cual) y la 2 también (D12: `z_align` se prueba antes que la sonda); queda la 3. Limpieza de boquilla: ver [phase4-plan.md §4](phase4-plan.md).

## Fase 4 (módulos de la Hi)

Análisis hecho el 2026-11-10: [phase4-plan.md](phase4-plan.md). Tareas B25 a B30. Solo `z_align` es necesario:
forma parte del `G28 Z` de stock. Ni el módulo de la K2 (pide `safeDist` y `z_align_force_stop`) ni el de la Hi
(depende de cuatro parches de Creality) valen tal cual. Hecho `z_align_hi.py`, portado del de la Hi (D13), con
`align.cfg` para probarlo antes que la sonda (D12) y `phase4.cfg` con la macro de `G28`; 12 tests. Limpieza de
boquilla hecha (B27, B28): `clean.cfg` con las macros del usuario portadas (D14), 5 tests, sin probar en la Hi.
Temperatura de cama corregida como en stock con `[adc_temperature hi_bed]` (B40; módulos de Kalico
aprovechables en [phase6-plan.md §2b](phase6-plan.md)). `tmc_line_check` portado (D15, B30), 8 tests. `[z_tilt]` de Kalico añadido a `phase4.cfg`. Falta conservar la
corrección de inclinación (B26b, solo ahorro de tiempo).

## Fase 5 (CFS)

Actualización 2026-11-10: comparadas las tramas del fork con las de la referencia de gitstonelabs (B31, B31b).
La capa de órdenes del fork no coincide con la Hi en `0x0A`, `0x0D`, `0x0F` y `0x11`; recomendación: opción D
(decidida: D16).
Hecho `creality_cfs.py` con transporte por `serial_485`, `cfs.cfg` y `phase5.cfg` (B34, 12 tests, con `CFS_PURGE` en la papelera); sin probar en
la Hi. Hechos `T0`..`T3`. Fase 6 empezada: `heat.cfg`, `mesh.cfg`, `print.cfg` y `phase6.cfg` (macros del usuario: cama, malla, inicio, fin, pausa y cancelación) y `modes.cfg` (modos silencioso y rápido, pausa de primera capa, `M600`): inventario de macros completo. Arranque automático diseñado en papel ([autostart-plan.md](autostart-plan.md), B13). Faltan los alias `BOX_*` y las tramas no pedidas.

Análisis ligero hecho el 2026-11-10: [phase5-plan.md](phase5-plan.md). Tareas B31 a B35. Las capas de bus y
protocolo del fork valen; `box.py` no vale tal cual (pin del sensor de corte, corte hacia -X y zona trasera de
la K2 fijos en el código). `gitstonelabs/creality-cfs-klipper` (GPLv3, validado en una Hi) es la candidata para
la coreografía, pero abre el puerto serie por su cuenta y hay que pasarlo a `serial_485`. Falta leer las dos
lógicas (B32, B31b) antes de decidir.

## Fase 6 (macros y uso)

Inventario hecho el 2026-11-10: [phase6-plan.md](phase6-plan.md). Tareas B36 a B39. La configuración del
usuario usa unos 50 comandos que el fork no ofrece (`tools/cfg_commands.py`); 33 son del CFS. El instalador no
puede clonar el fork en la Hi (no hay git): será un paquete.

## Dónde está el trabajo

- Rama `claude/project-thread-fnrqje` en los dos repos, creada desde `dev` y subida a GitHub el 2026-11-10, con
  pull request hacia `dev` en cada uno.
- Fork: commit `feat(hi): add phase 1 bring-up config with batch tests` (`config/hi/printer.cfg`, `test/hi/`,
  `test/test_hi_config.py`).

## Decisiones

Las tres enviadas el 2026-11-09 se aprobaron el 2026-11-10 con la opción recomendada: D5, D6 y D7 en
[decisions.md](decisions.md). Quedan sin confirmar expresamente las cuatro tomadas por defecto
([phase1-plan.md §10](phase1-plan.md)).
