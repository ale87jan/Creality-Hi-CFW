# Fase 6 — Macros y experiencia de uso

Análisis del 2026-11-10, hecho sin impresora y **ligero**: es un inventario de lo que tu configuración usa y el
fork no ofrece, y una lista de los frentes de esta fase. No he leído las macros una a una.

Notación como en [phase2-plan.md](phase2-plan.md). **Depende de las fases 1 a 5.**

## 1. Conclusiones

1. Tu configuración (`data/captures/2026-11-09_hi-v1.1.0.60/printer-config`, 15 ficheros) usa unos 50 comandos
   que el fork no ofrece y 8 secciones sin módulo (§2). Se obtiene con `tools/cfg_commands.py`, que es
   heurístico: sirve para planificar, no como lista cerrada.
2. 33 de esos comandos son del CFS y del rack externo: se resuelven en la fase 5, no aquí. Otros 7 son de
   motores y de Z (fases 2 a 4).
3. Quedan 10 comandos de parches de Creality al núcleo. Cada uno necesita una equivalencia en Kalico o
   quitarlo de las macros (§3).
4. La pantalla y la nube de Creality no pueden hablar con Kalico: usan `/tmp/klippy_uds` y órdenes propias
   [verificado: docs/phase1-plan.md:158-161]. Mientras no haya sustituto, la interfaz es Fluidd (D7).
5. La Hi no tiene git, gcc, wget ni curl [verificado: docs/phase1-plan.md:26]: el instalador no puede
   clonar el fork en la impresora, como dice hoy el roadmap. Tiene que ser un paquete `.tar.gz` con
   comprobación SHA-256.

## 2. Inventario

Orden: `python -I tools/cfg_commands.py data/captures/2026-11-09_hi-v1.1.0.60/printer-config <fork>/klippy`
[verificado: ejecutado el 2026-11-10 contra el fork en `e190fdb`].

| Grupo | Comandos | Dónde se resuelve |
| - | - | - |
| CFS | `BOX_GO_TO_EXTRUDE_POS`, `BOX_NOZZLE_CLEAN`, `BOX_CHECK_MATERIAL_REFILL`, `BOX_CUT_MATERIAL`, `BOX_END_PRINT`, `BOX_ERROR_CLEAR`, `BOX_EXTRUDER_EXTRUDE`, `BOX_EXTRUDE_MATERIAL`, `BOX_MATERIAL_CHANGE_FLUSH`, `BOX_MOVE_TO_SAFE_POS`, `BOX_TIGHTEN_UP_ENABLE`, `BOX_END`, `BOX_ERROR_RESUME_PROCESS`, `BOX_GET_REMAIN_LEN`, `BOX_GET_RFID`, `BOX_MOVE_TO_CUT`, `BOX_RESTORE_FAN`, `BOX_RETRUDE_MATERIAL`, `BOX_SAVE_FAN`, `BOX_SET_CURRENT_BOX_IDLE_MODE`, `BOX_SET_PRE_LOADING`, `BOX_SET_TEMP`, `BOX_START_PRINT`, `RESUME_BOX_ERROR_CLEAR`, `RESUME_FLUSH`, `PAUSE_CUT`, `FILAMENT_RUNOUT_FLUSH` | Fase 5. El `box.py` del fork tiene otro juego de comandos (`BOX_LOAD`, `BOX_UNLOAD`, `BOX_CUT`...) |
| Rack externo | `FILAMENT_RACK`, `FILAMENT_RACK_FLUSH`, `FILAMENT_RACK_PRE_FLUSH`, `FILAMENT_RACK_SAVE_FAN`, `FILAMENT_RACK_RESTORE_FAN`, `FILAMENT_RACK_SET_TEMP` | Fase 5, decisión 3 |
| Motores | `MOTOR_STALL_MODE`, `MOTOR_CHECK_PROTECTION_AFTER_HOME`, `MOTOR_CHECK_CUT_POS` | Fase 2: el `homing.py` del fork y `motor_control_hi` lo hacen por dentro; las macros de `sensorless.cfg` sobran |
| Z | `ZDOWN_SWITCH`, `UP_SAFE_Z`, `SET_ADJUSTMENTS_FLAG`, `NEXT_HOMEZ_NACCU` | Fases 3 y 4 |
| Núcleo de Creality | `FORCE_MOVE_E`, `CXSAVE_CONFIG`, `SET_LIMITS`, `RESTORE_LIMITS`, `SET_COOL_TEMP`, `SET_QMODE_FLAG`, `SET_RMODE_FLAG`, `ENABLE_PRESSURE_ADVANCE`, `CX_PRINT_LEVELING_CALIBRATION`, `EXCLUDE_OBJECT_RESET` | Esta fase (§3) |

Secciones sin módulo en el fork: `auto_addr`, `filament_rack` (fase 5); `prtouch_v3` (fase 3); `nozzle_clear`,
`bl24c16f`, `tmc_line_check`, `timer_read` (fase 4); `custom_macro` (esta fase).

## 3. Comandos del núcleo de Creality

| Comando | Candidato en Kalico | Estado |
| - | - | - |
| `SET_LIMITS` / `RESTORE_LIMITS` | `motion_limits.py` del fork (`save_motion_limits`, `restore_motion_limits`) o `SET_VELOCITY_LIMIT` | [supuesto: leer qué guarda cada uno] |
| `FORCE_MOVE_E` | `FORCE_MOVE STEPPER=extruder` o `G1 E` con `M83` | [supuesto] |
| `CXSAVE_CONFIG` | `SAVE_CONFIG`, que reinicia; el de Creality no | [supuesto: comprobar en el stock si reinicia] |
| `SET_COOL_TEMP` | Macro con `M104`/`M106` | [supuesto: ver qué hace en stock] |
| `SET_QMODE_FLAG` / `SET_RMODE_FLAG` | Modos silencioso y rápido: macros con `SET_VELOCITY_LIMIT` | [supuesto] |
| `ENABLE_PRESSURE_ADVANCE` | `SET_PRESSURE_ADVANCE` | [supuesto] |
| `CX_PRINT_LEVELING_CALIBRATION` | `BED_MESH_CALIBRATE` más `Z_TILT_ADJUST` | [supuesto] |
| `EXCLUDE_OBJECT_RESET` | Puede ser un falso positivo del inventario | Comprobar |
| `[custom_macro]` | Módulo de Creality; ver qué comandos registra | Sin analizar |

Ninguna equivalencia está comprobada: cada fila es una tarea de lectura del stock (B36).

## 4. Frentes de la fase

1. **Macros**: partir de tu configuración y sustituir comando a comando, o partir de `config/k2/macros.cfg` y
   `start_print.cfg` del fork y adaptar la geometría (§6, decisión 1).
2. **Estructura de `config/hi/`**: hoy hay `printer.cfg` (fase 1) y `phase2.cfg`. Para uso diario conviene un
   fichero por subsistema, como `config/k2/` (`printer.cfg`, `motor_control.cfg`, `prtouch.cfg`, `box.cfg`,
   `macros.cfg`, `start_print.cfg`). Ya hace falta en la fase 3 (backlog B22).
3. **Pantalla**: Fluidd al principio (D7). Sustituto para el panel de 240x320: sin analizar.
4. **Instalador**: paquete `.tar.gz` con el fork, `c_helper.so` compilado (D6) y la config; instalación y
   vuelta a stock con `hi_kalico.sh` (fase 1). Arranque automático y partición A/B: sin diseñar; el overlay es
   común a los dos slots [verificado: docs/phase1-plan.md, hallazgos].
5. **Documentación**: web con MkDocs. Sin empezar.

## 5. Qué se puede hacer sin impresora

- B36: leer en el stock qué hace cada comando del §3 y fijar la equivalencia.
- Reestructurar `config/hi/` por subsistemas, con los tests en batch actuales como red.
- Macros de impresión (`START_PRINT`, `END_PRINT`, `PAUSE`, `RESUME`, `CANCEL_PRINT`) con test en batch que
  compruebe que no usan ningún comando ausente (`tools/cfg_commands.py` da cero).

## 6. Decisiones que necesito

1. **Base de las macros**: tu configuración, sustituyendo los comandos de Creality (recomendada: conserva tu
   comportamiento actual); o las macros de la K2 adaptadas a la Hi.
2. **Pantalla**: seguir solo con Fluidd hasta imprimir bien (recomendada) o investigar ya un sustituto.
3. **Arranque automático de Kalico**: mantener el arranque manual con `hi_kalico.sh` hasta terminar la fase 5
   (recomendada) o diseñar ya el arranque por defecto, que escribe en el sistema.

## 7. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | Una macro llama a un comando ausente a mitad de impresión | Test con `tools/cfg_commands.py` sobre `config/hi/` |
| R2 | Equivalencias mal supuestas (por ejemplo, `SAVE_CONFIG` reinicia) | B36 antes de escribir macros |
| R3 | El arranque automático deja la impresora sin stock si falla | Decisión 3; vuelta a stock documentada antes de activarlo |
