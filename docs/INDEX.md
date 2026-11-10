# Índice de docs

Generado por `claude-plugin/hi-dev/scripts/docs-index.py`; no editar a mano. Lee esto primero y abre el documento completo solo si hace falta.

## Documentos

| Doc | Líneas | Resumen |
| - | - | - |
| [Estado](ESTADO.md) | 98 | Punto de entrada para retomar el trabajo sin contexto previo. Se actualiza en cada commit. |
| [Diferencias entre firmwares OTA Creality Hi (CR4NU200360C20)](analysis/firmware-versions.md) | 113 | Versiones analizadas: V1.1.0.50, V1.1.0.60 (instalada), V1.1.0.65, V1.1.0.73 y V1.1.0.74. Análisis del 2026-11-09. |
| [Viabilidad: portar el CFW de la K2 Plus a la Creality Hi](analysis/k2-port-feasibility.md) | 132 | Análisis del 2026-11-09: estático, más pruebas de solo lectura en la impresora (sección siguiente). |
| [Arranque automático de Kalico: diseño (B13)](autostart-plan.md) | 88 | Estado: **diseño en papel** (2026-11-10, pedido por el usuario). Opción A elegida (D18). Nada de esto está escrito en scripts ni se ha ejecutado en la impresora. Hoy Kalico solo se arranca a mano con… |
| [Backlog](backlog.md) | 431 | Tareas pequeñas y autocontenidas, pensadas para ejecutarse sin el contexto de la conversación que las creó. Antes de empezar una: leer ESTADO.md y la sección citada de phase1-plan.md. Al terminar: ma… |
| [Decisiones](decisions.md) | 355 | Registro de decisiones de diseño. Cada entrada: contexto, decisión y consecuencias. |
| [Hardware de la Creality Hi (F018)](hardware.md) | 76 | Nivel de confianza: **[P]** verificado en la impresora, **[F]** leído en el firmware o la config de stock, **[I]** inferido. Ver RESEARCH.md. |
| [Fase 1 — Kalico arrancando en la Hi: análisis y plan](phase1-plan.md) | 399 | Fecha: 2026-11-09. Alcance: las tres MCU, steppers Z/Z1/E, temperaturas y ventiladores, sobre el Tina de stock V1.1.0.60. Fuera: motores X/Y, sonda, CFS, bus RS-485. |
| [Fase 2 — Motores X/Y de lazo cerrado](phase2-plan.md) | 199 | Análisis del 2026-11-10, hecho sin impresora. Alcance: que Kalico hable con los drivers X/Y por RS-485, mueva X/Y y haga homing de X e Y. Fuera: homing de Z y sonda (fase 3), `z_align` (fase 4), CFS… |
| [Fase 3 — Sonda de presión y homing de Z](phase3-plan.md) | 116 | Análisis del 2026-11-10, hecho sin impresora y **más ligero que el de la fase 2**: cubre la compatibilidad estática del módulo y el camino de `G28 Z`; no he leído entera la lógica de armado y disparo… |
| [Fase 4 — Módulos legibles de la Hi](phase4-plan.md) | 378 | Análisis del 2026-11-10, hecho sin impresora. Alcance: los cinco módulos Python de Creality que la Hi trae en claro y que el fork no tiene: `z_align.py`, `nozzle_clear.py`, `bl24c16f.py`, `tmc_line_c… |
| [Fase 5 — CFS](phase5-plan.md) | 247 | Análisis del 2026-11-10, hecho sin impresora y **ligero**: cubre qué partes del código de CFS del fork valen para la Hi y cuáles no, a partir de las opciones, los pines y la rutina de corte. No he le… |
| [Fase 6 — Macros y experiencia de uso](phase6-plan.md) | 189 | Análisis del 2026-11-10, hecho sin impresora y **ligero**: es un inventario de lo que tu configuración usa y el fork no ofrece, y una lista de los frentes de esta fase. No he leído las macros una a u… |
| [Protocolo de las MCU de Klipper](protocols/mcu.md) | 49 | Las tres MCU de la Hi llevan Klipper de Creality (2024-2025) con el protocolo estándar: mensajes con VLQ, CRC-16 CCITT, sincronización `0x7E` y diccionario de datos comprimido con zlib. Kalico (host… |
| [Bus RS-485 (`/dev/ttyS5`, 230400 8N1)](protocols/rs485.md) | 100 | Bus compartido por los motores de lazo cerrado y el CFS. Fuentes: código abierto de la K2 (`serial_485.py`, `motor_control.py`, `box_protocol.py` de `Jacob10383/k2-plus-custom-firmware`), el |
| [Hoja de ruta](roadmap.md) | 95 | Objetivo: sustituir el Klipper antiguo de Creality por **Kalico** con módulos abiertos, portando el CFW de la K2 Plus (Jacob10383/k2-plus-custom-firmware) y conservando el sistema Tina de stock de la… |
| [Pantalla de la Hi con Kalico: opciones](screen-plan.md) | 306 | Estado: análisis sin impresora (2026-11-10). Decisiones ya tomadas en el §0; la base de la pantalla táctil (opción H frente a E) sigue abierta. Mientras tanto sigue vigente la decisión D7 (consola SS… |

## Decisiones

- **D1 — Base del host: Kalico de Jacob10383 (2026-11-09)**: Partir del fork de Jacob10383.
- **D2 — El código vive en un fork propio del Kalico de Jacob10383 (2026-11-09)**: Fork propio del Kalico de Jacob10383.
- **D3 — Dos repositorios, como el CFW de la K2 (2026-11-09)**: Dos repositorios:
- **D4 — Ramas, commits e integración (2026-11-09)**: | Repo | Ramas | | - | - | | `Creality-Hi-CFW` | `main` estable (releases) y `dev` de integración | | `Creality-Hi-Kalico` | `main` espejo de Jacob10383/kalico; `dev` de integración (rama por defecto…
- **D5 — Fase 1 escalonada, sin escribir en flash (2026-11-10)**: Escalonada: Kalico vive en `/mnt/UDISK/kalico-hi` y se lanza a mano parando el Klipper de stock.
- **D6 — `c_helper.so` como artefacto del paquete de instalación (2026-11-10)**: Artefacto del paquete: `scripts/build_chelper.sh` lo compila y `scripts/make_bundle.sh` lo mete en el `.tar.gz` con su SHA-256. El fork conserva el binario de Jacob sin tocar.
- **D7 — Interfaz en fase 1: consola SSH y después Fluidd (2026-11-10)**: Primer arranque con socket propio (`/tmp/kalico_uds`) y consola por SSH (`hi_kalico.sh gcode`); cuando el arranque básico esté comprobado, el Moonraker de stock apuntando a Kalico (`hi_kalico.sh star…
- **D8 — `motor_control` de la Hi como copia aparte (2026-11-10)**: Copia aparte: `klippy/extras/motor_control_hi.py` en el fork, recortada para la Hi (solo X/Y, sin motor E, sin túnel `transparent`, sin calibración de corte). `motor_control.py` de la K2 no se toca.
- **D9 — Escrituras a los drivers X/Y por niveles (2026-11-10)**: Opción `startup_writes` en `[motor_control_hi]` con tres niveles: `none` (asigna direcciones y solo lee; valor por defecto), `stall` (añade el modo de stall y el borrado de fallos; necesario para el…
- **D10 — Homing de la fase 2: solo X e Y (2026-11-10)**: Solo X e Y. `G28` y `G28 Z` dan error en `config/hi/phase2.cfg`; Z se levanta con `SET_KINEMATIC_POSITION`, como en la fase 1. El homing de Z llega con la sonda en la fase 3.
- **D11 — Sonda: `prtouch.py` de la K2 tal cual (2026-11-10)**: Tal cual. La Hi solo aporta `config/hi/phase3.cfg`.
- **D12 — Alineación de Z antes que la sonda (2026-11-10)**: En la impresora se prueba primero la alineación (`ZDOWN`) y después la sonda.
- **D13 — `z_align` portado del módulo de la Hi (2026-11-10)**: Portar el de la Hi: `z_align_hi.py` con `ZDOWN`, `UP_SAFE_Z`, `CHECK_ZLIMIT` y `ZDOWN_SWITCH`.
- **D14 — Limpieza de boquilla: macros del usuario con guarda y reset (2026-11-10)**: `config/hi/clean.cfg` con sus macros portadas. Se mantiene la guarda (`busy`) y se añade `NOZZLE_CLEAN_RESET` para liberarla a mano.
- **D15 — Módulos de la Hi que se portan en la fase 4 (2026-11-10)**: Se portan `z_align` (D13), la limpieza de boquilla (D14) y `tmc_line_check`. `bl24c16f` queda sin fecha y `timer_read` no se porta.
- **D16 — CFS: `creality_cfs.py` de gitstonelabs sobre `serial_485` (2026-11-10)**: Usar `creality_cfs.py` con una opción `serial` añadida que lo hace hablar por `serial_485`. Comandos `CFS_*`; los alias `BOX_*` de stock se dejan para la fase 6.
- **D17 — `G28 Z` no repite la alineación del pórtico (2026-11-10)**: En `phase4.cfg`, `ZDOWN` solo si Z no está referenciado al empezar el `G28`. `G28 ALIGN=1` la fuerza. `ZDOWN_SWITCH ENABLE=0` sigue desactivándola siempre.
- **D18 — Arranque automático con un servicio propio que conmuta (2026-11-10)**: Opción A, "por ahora" [usuario]: `/etc/init.d/kalico_hi` repite la conmutación manual de la fase 1, gobernado por ficheros bandera en `/mnt/UDISK/kalico-hi`. No se modifica ningún fichero de stock.
- **D19 — Protección de ramas con rulesets de GitHub (2026-11-10)**: Rulesets activos [P, `gh api repos/.../rulesets`], todos sin push forzado ni borrado:
- **D20 — Plugin `hi-dev` para ahorrar tokens (2026-11-10)**: [usuario] Plugin versionado en este repo (`claude-plugin/hi-dev`, marketplace `creality-hi`) con scripts de solo lectura, subagentes Haiku por defecto (Sonnet para verificar), skills de flujo y hooks…

Detalle de una: `docs-index.py --decision D12`.

## Hoja de ruta (casillas hechas / total)

- Fase 0 — Investigación (hecha): 4/4
- Fase 1 — Kalico arrancando en la Hi: 6/8
- Fase 2 — Motores X/Y de lazo cerrado: 0/5
- Fase 3 — Sonda: 0/3
- Fase 4 — Módulos legibles de la Hi: 1/5
- Fase 5 — CFS: 0/4
- Fase 6 — Macros y experiencia de uso: 0/5
