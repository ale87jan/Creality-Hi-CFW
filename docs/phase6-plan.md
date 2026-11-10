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

## 2b. Módulos de Kalico que evitan portar código (2026-11-10)

Pedido por el usuario. Inventario de `klippy/extras` del fork (168 módulos más `display/`, `indx/` y
`load_cell/`) hecho con un subagente; en la tabla solo entra lo que he contrastado después con los ficheros.

| Necesidad | En stock | Módulo de Kalico o del fork | Estado |
| - | - | - | - |
| Corrección de la temperatura de cama | `temp_offset_flag`, `adc_temp_list`, `actual_temp_list` (parche de Creality) [verificado: stock:adc_temperature.py:28-55] | `[adc_temperature]` con tabla propia `temperatureN`/`resistanceN` [verificado: fork:adc_temperature.py:204-240] | **Hecho**: sensor `hi_bed` en `config/hi/base.cfg`, sigue la tabla de stock con error ≤ 0,25 °C (test) |
| Ajuste del termistor de boquilla | No hay tabla en la config de la boquilla | `[thermistor]` propio por tres puntos o `beta`; `pullup_resistor`, `inline_resistor` [verificado: fork:thermistor.py:83-84, 107-116]. No hay opción de offset en grados [verificado: búsqueda del subagente; `voltage_offset` es en voltios, fork:adc_temperature.py:157] | Disponible; hace falta medir con un termopar para tener puntos |
| Inclinación fina del puente | `z_tilt` parcheado (`ADJUST_STEPPERS`) | `z_tilt.py` sin cambios; `z_tilt_ng.py` añade `Z_TILT_CALIBRATE` y `Z_TILT_AUTODETECT` [verificado: fork:z_tilt_ng.py existe; comandos según el subagente, líneas 235-246] | `[z_tilt]` hecho en `phase4.cfg`; `z_tilt_ng` sin evaluar |
| Acelerómetros e input shaper | `[lis2dw x]`, `[lis2dw y]`, `[resonance_tester]` | `lis2dw.py`, `resonance_tester.py` | Las tres secciones de stock cargan sin cambios en batch [verificado: prueba del 2026-11-10 con captura:printer.cfg:144-165] |
| Recuperación tras corte de luz | `bl24c16f` (EEPROM) y parches | `power_loss_recovery.py` del fork (`PLR_STATUS`, `PLR_RECOVER`, `PLR_DISCARD`) | No vale tal cual: exige el objeto `z_align` de la K2 (`capture_reference_frame`, `start_prepare`, `zmax`) [verificado: fork:power_loss_recovery.py:900, 1163, 1280, 1644]. Candidato a adaptar a `z_align_hi` en lugar de portar `bl24c16f` |
| Vigilancia de ventiladores | `[fan_feedback]` con `fan0_pin`..`fan2_pin` [verificado: captura:printer_params.cfg:27-32] | `fan_feedback.py` del fork, sobre el `tachometer_pin` de cada ventilador, con valores por defecto de la K2 [verificado: fork:fan_feedback.py:4-30] | Otra sintaxis: hay que pasar los pines a `tachometer_pin` [supuesto: comprobar en batch] |
| Limpieza de boquilla | `nozzle_clear` | `nozzle_cleanup.py` | Descartado (D14, [phase4-plan.md](phase4-plan.md) §4) |
| Malla, objetos, arcos, pausa, SD virtual, sensores de filamento | Secciones estándar | `bed_mesh`, `exclude_object`, `gcode_arcs`, `pause_resume`, `virtual_sdcard`, `filament_switch_sensor` | Existen [verificado: listado del subagente]; las opciones añadidas por Creality se revisan por subsistema (B37) |

Mejoras que Kalico ofrece y stock no, sin sustituir nada: control MPC (`control_mpc.py`, `MPC_CALIBRATE`),
`axis_twist_compensation`, `z_thermal_adjust`, `firmware_retraction`, `save_variables`
[verificado: existen en el listado del subagente; sin evaluar para la Hi].

## 2c. Mejoras de `nachorepara/creality-hi-klipper-tweaks` (2026-11-10)

Repositorio indicado por el usuario (MIT, commit `0de2ff9`, probado por su autor en la OTA 1.1.0.74). Son cuatro
parches de config para stock; ninguno se aplica sin que el usuario lo apruebe, uno a uno.

| Parche | Qué hace en stock | Cómo quedaría en Kalico | Estado |
| - | - | - | - |
| 01 | El segundo `G28 Z` de la preparación se salta `ZDOWN` con `ZDOWN_SWITCH ENABLE=0` y una bandera de sesión; el autor mide 57-61 s frente a 17-23 s [verificado: ref:patches/01] | En el `[homing_override]` de `phase4.cfg`: saltar `ZDOWN` si Z ya está referenciado (los motores no se han soltado desde la alineación) | Hecho el 2026-11-10 [usuario]: macro `_HI_ALIGN`; `G28 ALIGN=1` fuerza la alineación [verificado: test `test_phase4_aligns_only_when_z_was_not_homed`]. Comprobar en la Hi (paso 4.6) |
| 02 | `touch_cnt: 3` a `1` y `closure_temp: 160` en `[nozzle_clear]`; el autor mide 168 s frente a 102 s [verificado: ref:patches/02] | Variables `touch_cnt` y `seal_temp` de `clean.cfg` | Hecho el 2026-11-10 con los valores del usuario: `touch_cnt: 2` (antes 4) y sellado a 160 °C por defecto, con parámetro `SEAL_TEMP=` en `NOZZLE_WIPE` y `NOZZLE_CLEAN` [verificado: test `test_sealing_temperature_is_a_parameter`]. El G-code de `NOZZLE_WIPE` ya no es idéntico al de sus macros originales |
| 03 | `M109`/`M190` no esperan si no hay ningún eje referenciado [verificado: ref:patches/03] | Mismas macros. Riesgo propio: `creality_cfs` usa `M109` como guarda de fusión antes de extruir; con el parche no esperaría si nada está referenciado | No se incorpora (2026-11-10) [usuario]: su `START_PRINT` ya fija la boquilla con `M104` sin esperar y sus `M140`/`M190` propios (calentamiento de cama con sobreimpulso y frenado) ocupan esas órdenes [verificado: captura:print_macros.cfg:139, 160; captura:config_macros.cfg:19-104]. Esas macros solo usan órdenes estándar y se portan tal cual |
| 04 | `probe_count` de `9,9` a `5,5` (opcional) [verificado: ref:patches/04] | Valor de `[bed_mesh]` | No se incorpora (2026-11-10) [usuario]: se mantiene `9, 9` |

## 2d. Notas para portar las macros del usuario (2026-11-10)

Base decidida: la configuración del usuario (§6, decisión 1). Inventario repetido contra el fork en `fd4b419`:
46 comandos ausentes y 7 secciones sin módulo [verificado: `tools/cfg_commands.py`, 2026-11-10].

- `print_macros.cfg` usa de lo ausente: `BOX_START_PRINT`, `BOX_END_PRINT`, `BOX_END`, `BOX_TIGHTEN_UP_ENABLE`,
  `BOX_ERROR_RESUME_PROCESS`, `BOX_SET_CURRENT_BOX_IDLE_MODE`, `RESUME_BOX_ERROR_CLEAR`, `RESUME_FLUSH`,
  `ENABLE_PRESSURE_ADVANCE`, `NEXT_HOMEZ_NACCU` y `EXCLUDE_OBJECT_RESET` [verificado: salida del inventario].
- `M140`/`M190` del usuario (cama con sobreimpulso y frenado, `config_macros.cfg`) solo usan órdenes estándar y
  la macro `PRINTER_PARAM`: se portan tal cual.
- La malla es por temperatura, no por impresión: `_MESH_IF_NEEDED` carga el perfil `<temp>c` y solo llama a
  `G29` si no existe [verificado: captura:custom_mesh.cfg:68-85] [usuario]. Se mantiene `9, 9`.
- `G29` del usuario: el `ZDOWN_SWITCH ENABLE=1` + `G28 Z` tras el reposo térmico pasa a `G28 Z ALIGN=1` (D17).
  Usa `SET_ADJUSTMENTS_FLAG`, `CXSAVE_CONFIG` y `printer.custom_macro.g28_ext_temp`, sin equivalente comprobado
  (B36) [verificado: captura:custom_mesh.cfg:12-66].
- **Hecho (2026-11-10):** `config/hi/heat.cfg` (sus `M140`/`M190`), `config/hi/mesh.cfg` (`[bed_mesh]`, `G29`,
  `_MESH_IF_NEEDED`) y `phase6.cfg`; 3 tests en `test/test_hi_mesh.py`. Equivalencias usadas:
  `CXSAVE_CONFIG` es `SAVE_CONFIG RESTART=0` [verificado: fork:configfile.py:868]; `g28_ext_temp` es un valor
  de config, 140 [verificado: captura:printer_params.cfg:24]; `relative_reference_index: 40` es
  `zero_reference_position: 130, 130`; `move_check_distance` sube de 1 a 3, el mínimo de Kalico [verificado:
  error de carga en batch]; `SET_ADJUSTMENTS_FLAG` se quita [supuesto: guardaba la corrección de inclinación
  para el siguiente `ZDOWN`; leerlo en stock, B36]. Diferencia propia: se restaura la aceleración tras el
  mallado (su macro la dejaba a un cuarto). `PRINT_PREPARED` no se llama hasta portar `START_PRINT`.
- B36 necesita el `klippy/` de stock, que no está en git: hay que traerlo del PC del usuario (carpeta
  `firmware`), que debe estar encendido.

## 3. Comandos del núcleo de Creality

| Comando | Candidato en Kalico | Estado |
| - | - | - |
| `SET_LIMITS` / `RESTORE_LIMITS` | `motion_limits.py` del fork (`save_motion_limits`, `restore_motion_limits`) o `SET_VELOCITY_LIMIT` | [supuesto: leer qué guarda cada uno] |
| `FORCE_MOVE_E` | `FORCE_MOVE STEPPER=extruder` o `G1 E` con `M83` | [supuesto] |
| `CXSAVE_CONFIG` | `SAVE_CONFIG RESTART=0` [verificado: fork:configfile.py:868] | Usado en `mesh.cfg`; que el de Creality no reinicia es [supuesto] |
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

1. **Base de las macros** (cerrada el 2026-11-10: la configuración del usuario): tu configuración, sustituyendo los comandos de Creality (recomendada: conserva tu
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
