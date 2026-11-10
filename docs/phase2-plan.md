# Fase 2 — Motores X/Y de lazo cerrado

Análisis del 2026-11-10, hecho sin impresora. Alcance: que Kalico hable con los drivers X/Y por RS-485, mueva
X/Y y haga homing de X e Y. Fuera: homing de Z y sonda (fase 3), `z_align` (fase 4), CFS y cuchilla (fase 5).

Cada afirmación lleva `[verificado: fichero:línea]` o `[supuesto: cómo comprobarlo]`. Rutas: `fork:` es
Creality-Hi-Kalico (rama `dev`, commit `a0b3a40` en la rama de trabajo); `stock:` es el rootfs de la OTA
V1.1.0.60 (`/usr/share/klipper/`), que se lee y no se ejecuta; `captura:` es
`data/captures/2026-11-09_hi-v1.1.0.60/printer-config/`.

**Depende de la fase 1.** Nada de esto se ha probado en la Hi. Todo el plan asume que la fase 1 termina bien
(paso 0, carga de `c_helper.so`, arranque de las tres MCU) [supuesto: [phase1-plan.md](phase1-plan.md) §8].

## 1. Conclusiones

1. `motor_control.py` del fork **no arranca en la Hi tal cual**, por tres motivos independientes (§3): exige el
   motor E por el túnel `transparent` de la boquilla, que la MCU de la Hi no tiene; lleva fijos los pines de
   stall de la K2; y asigna las direcciones al revés que el stock de la Hi.
2. La lista de ejes ya es configurable (`motor_axes: x, y`), así que quitar Z y Z1 no necesita código.
3. **La Hi no hace homing de X/Y con los pines de stall.** El stock usa `endstop_pin: !PC7` para X y `^PB13`
   para Y, que no son los pines de stall (`PA8`, `PA6`). `PC7` es la misma línea que usa la sonda
   (`step_swap_pin`) y llega desde la MCU de la boquilla a través de `[io_remap]`. Esto cambia el plan del
   roadmap ("homing por stall") y adelanta `io_remap.py` de la fase 4 a la fase 2 (§4).
4. El `homing.py` del fork sirve para `G28 X Y`. `G28 Z` depende del escáner de la K2 y queda bloqueado hasta
   la fase 3 (§5).
5. El arranque de la K2 escribe en los drivers (modo de stall, borrado de fallos y, si la config trae
   parámetros, `SYS_PARAM`). Para la Hi se propone un arranque por niveles, empezando en solo lectura (§6).

## 2. Qué hace `motor_control.py` en el arranque

Secuencia al recibir `serial_485:ready` [verificado: fork:klippy/extras/motor_control.py:3290-3309]:

| Paso | Qué envía al bus | ¿Escribe en el driver? |
| - | - | - |
| `serial_target_discovery` | Pone DIR/STEP según `PIN_DIR_SEQUENCE`, broadcast `READ_ADDR 01` a 0xFF y `READ_ADDR 02` a cada dirección | Sí: cada driver toma su dirección. El stock hace lo mismo en cada arranque [supuesto: `set_motor_pin_dir` y `MOTOR_SET_ADDR` en los símbolos de stock:klippy/extras/motor_control_wrapper.cpython-39.so; confirmar con la traza del paso 2.1] |
| `extruder_target_discovery` | `READ_ADDR` por el túnel de la boquilla | No aplica a la Hi |
| `stall_mode` | `STALL_MODE 02` a todos los ejes | Sí (RAM). La Hi ya tiene `param_stall_mode` = 2 [verificado: docs/protocols/rs485.md, tabla de parámetros] |
| `protect_check` | `PROTECTION 0B` | No |
| `protect_clear` | `PROTECTION 05` solo si hay fallos | Sí: borra errores y avisos |
| `protect_recheck` | `PROTECTION 0B` | No |
| `apply_overrides` | Por cada clave `x_...`/`y_...` de `[motor_control]`: lee, y si difiere escribe `SYS_PARAM 01` y aplica `03` | **Sí**, solo si la config trae parámetros [verificado: fork:klippy/extras/motor_control.py:1611-1680] |

Después: sondeo de protección cada 60 s y lectura de temperatura de los drivers (`GET`, solo lectura)
[verificado: fork:klippy/extras/motor_control.py:2625, 2437-2439]. Si un paso falla reintenta 3 veces y deja
`is_ready = False`, sin apagar Klipper [verificado: fork:klippy/extras/motor_control.py:3527-3592].

Sin claves de parámetros en la config no hay escrituras de `SYS_PARAM`. La config de stock de la Hi trae 51
claves por eje (captura:motor_control.cfg), así que **no se puede reutilizar tal cual**: provocaría la
comparación y, si algo difiere, la escritura.

## 3. Por qué no arranca en la Hi

| Problema | Dónde | Efecto en la Hi |
| - | - | - |
| Motor E obligatorio | `managed_axes = kinematic_axes + EXTRUDER_AXES` [verificado: fork:klippy/extras/motor_control.py:2678]; el adaptador registra `config_transparent` en `nozzle_mcu` [verificado: :1778] | La boquilla de la Hi no tiene `config_transparent` [verificado: fork:test/hi/nozzle_mcu.dict; docs/protocols/mcu.md]: error al conectar |
| Pines de stall fijos | `STALL_PIN_LAYOUT`: `PB12`, `PB11`, `nozzle_mcu:PB12` [verificado: :2275-2281] | La Hi usa `PA8` y `PA6` [verificado: captura:motor_control.cfg:25-26]. `PB12` es un sensor de filamento en la Hi [verificado: captura:printer.cfg:294] |
| Direcciones | `motor_map.json`: x = 0x82, y = 0x81; `PIN_DIR_SEQUENCE` pone DIR de X a 1 y de Y a 0 [verificado: fork:klippy/extras/motor_map.json `_addr`; motor_control.py:2519-2528] | El stock deja X = 0x81, Y = 0x82 [P]. Funcionaría con las de la K2, pero el roadmap pide mantener las de stock |
| Mapa de parámetros | `motor_map.json` es de `mot2_002_081`, con valores de referencia de la K2 | Los ids valen para `071` (51/51 por eje [P]); los **valores** de referencia no son los de la Hi (el X es otro motor) |
| Calibración del corte | `MotorCutCalibrationHelper` asume la cuchilla en -X [verificado: :38-47] | La Hi corta en +X: no usar `CALIBRATE_CUT_POS` (fase 5) |

Lo que sí sirve sin cambios: `serial_485.py` (trama idéntica, `/dev/ttyS5` a 230400 por defecto
[verificado: fork:klippy/extras/serial_485.py:184-185]), el cliente de firmware, la vigilancia de stall con
`buttons` (las dos MCU tienen `config_buttons` [verificado: fork:test/hi/mcu.dict]) y `motor_axes`
[verificado: fork:klippy/extras/motor_control.py:2352-2360].

## 4. Homing de X/Y en la Hi: el hallazgo de los finales de carrera

| | K2 (config del fork) | Hi (stock) |
| - | - | - |
| `stepper_x` `endstop_pin` | `PB12` = pin de stall de X | `!PC7` |
| `stepper_y` `endstop_pin` | `PB11` = pin de stall de Y | `^PB13` |
| Pines de stall | `PB12`, `PB11` | `PA8`, `PA6` |

[verificado: fork:config/k2/printer.cfg:90,105; captura:printer.cfg:122,135; captura:motor_control.cfg:25-26]

- El Python de stock no sustituye los endstops durante el homing: `homing.py` es el de Klipper con mensajes de
  Creality y usa los endstops del raíl [verificado: stock:klippy/extras/homing.py:79-103]. Por tanto `PC7` y
  `PB13` son entradas reales de la MCU principal.
- `PC7` es también `step_swap_pin` de la sonda [verificado: captura y stock:config/F018_CR4NU200360C20/
  printer.cfg:153], y la config de stock deja comentado `# endstop_pin:!nozzle_mcu:PB0` junto al de X
  [verificado: stock:config/F018_CR4NU200360C20/printer.cfg:75-76].
- `[io_remap]` configura en la **MCU de la boquilla** que `PB0` (entrada) se copie en `PA15` (salida)
  [verificado: stock:klippy/extras/io_remap.py:20-38; captura:printer.cfg:108-114]. `nozzle_mcu:PA15` es
  `pres_swap_pin` de la sonda [verificado: docs/hardware.md:59].
- La Hi tiene sensores físicos de final de carrera en X y en Y [usuario, 2026-11-10]. Lectura más probable del
  cableado: el de X está en el cabezal (`nozzle_mcu:PB0`) y la boquilla lo reenvía por la línea `PA15` → `PC7`,
  compartida con la sonda; el de Y está en `PB13` de la placa [supuesto: paso 2.1, `QUERY_ENDSTOPS` en stock
  moviendo el cabezal a mano con los motores desactivados].
- `MOTOR_STALL_MODE DATA=1` antes del homing y `DATA=2` después siguen en el `homing_override` de stock
  [verificado: stock:config/F018_CR4NU200360C20/sensorless.cfg:154,203]. Qué cambia en el driver con el modo 1 no
  está documentado [supuesto: leer `param_stall_mode` y el pin de stall antes y después, solo lectura].

Consecuencias:

1. La config de la Hi mantiene `endstop_pin: !PC7` y `^PB13`; no se usa el pin de stall como endstop.
2. Hay que portar `io_remap.py` en esta fase. Es Python legible, 50 líneas, y las dos MCU tienen
   `config_ioRemap` y `operation_ioRemap` [verificado: fork:test/hi/nozzle_mcu.dict].
3. El reenvío solo se activa mientras X hace homing: el `homing.py` de stock envía `SET_IOREMAP S=1` antes de
   X y `S=0` después, también si falla [verificado: stock:klippy/extras/homing.py:399-413]. La línea se
   comparte con la sonda. En Kalico lo hace el propio módulo con `homing_stepper: stepper_x`, desde los eventos
   de homing y sin tocar `homing.py` [verificado: fork:klippy/extras/io_remap.py; fork:config/hi/phase2.cfg].

## 5. `homing.py` del fork con la Hi

- `G28 X Y` ordena Y y después X, entra en modo de stall 1, hace el homing con los endstops del raíl y vuelve
  al modo 2 [verificado: fork:klippy/extras/homing.py:975-989, 901-935, 1166-1206]. El stock hace X y después Y
  [verificado: stock:config/F018_CR4NU200360C20/sensorless.cfg:77,97]. El orden no es obligatorio
  [usuario, 2026-11-10].
- Antes de mover X/Y hay que levantar Z un poco para no arañar la cama [usuario, 2026-11-10]; el stock lo hace
  con `_IF_HOME_Z` dentro de `_IF_MOVE_XY` [verificado: captura:sensorless.cfg:114-125]. En la fase 2 Z no tiene
  homing: se levanta con `SET_KINEMATIC_POSITION Z=0 SET_HOMED=z` y `G1 Z5 F300`, como en la fase 1, antes de
  `G28 X` o `G28 Y`.
- Antes del primer homing tras reiniciar hace un movimiento de "cebado" del eje
  [verificado: fork:klippy/extras/homing.py:995-1024] [supuesto: revisar distancias con la geometría de la Hi
  antes de mover].
- `G28 Z` exige el modelo del escáner (`_is_probe_model_ready`) y `NOZZLE_CLEAN`
  [verificado: fork:klippy/extras/homing.py:1128-1152]: no sirve para la Hi hasta la fase 3.
- En la fase 2 la config bloquea `G28 Z` con un `[homing_override]` que solo deja pasar X e Y. Sin Z en homing,
  Kalico rechaza los movimientos de Z, igual que en la fase 1.

## 6. Diseño (D8 y D9)

Decisión D8: el módulo de la Hi es una **copia aparte**, `klippy/extras/motor_control_hi.py`, recortada.
`motor_control.py` de la K2 no se toca.

| En `motor_control_hi.py` | Valor en la Hi | En la K2 era |
| - | - | - |
| Ejes | solo `x`, `y` | `x, y, z, z1` + `e` fijo |
| Transporte | solo `serial_485` | más el túnel `transparent` de la boquilla |
| `motor_x_stall`, `motor_y_stall` (config) | `PA8`, `PA6` | `STALL_PIN_LAYOUT` fijo |
| Direcciones y niveles DIR/STEP | X = 0x81, Y = 0x82 | x = 0x82, y = 0x81 |
| `startup_writes` (config) | `none` al principio | secuencia fija de arranque |
| Calibración de corte y `MOTOR_CALIBRATE` | no se registran | comandos de la K2 |

El objeto se registra también como `motor_control` para que `homing.py` (que hace
`lookup_object("motor_control")` e importa constantes de `.motor_control`
[verificado: fork:klippy/extras/homing.py:10, 590]) funcione sin cambios.

Niveles de `startup_writes`:

| Nivel | Qué hace | Riesgo |
| - | - | - |
| `none` | Asigna direcciones y solo lee: `READ_ADDR`, `PROTECTION 0B`, `GET` | El mismo broadcast que hace el stock |
| `stall` | Añade `STALL_MODE 02` y borrado de fallos si los hay | Escribe estado volátil que el stock también escribe |
| `params` | Añade `apply_overrides` | Escribe `SYS_PARAM` en RAM: **necesita aprobación expresa** |

Además: `klippy/extras/io_remap.py` (port del de stock) y `config/hi/motor_control.cfg` sin claves de
parámetros. `MOTOR_FLASH_PARAM` y `MOTOR_CALIBRATE` quedan sin registrar en la Hi mientras no se aprueben.

Hecho en el fork el 2026-11-10: `klippy/extras/motor_control_hi.py`, `klippy/extras/motor_map_hi.json` (ids de
la K2, valores leídos en la Hi, solo de referencia), `klippy/extras/io_remap.py`, `config/hi/phase2.cfg` y
`test/test_hi_motor_control.py` (40 tests: puerta de escritura, pasos de arranque por nivel, bus simulado y
config en batch). La puerta de escritura clasifica cada trama antes de enviarla: una trama desconocida, de flash
o de calibración no sale nunca, sea cual sea el nivel [verificado: fork:klippy/extras/motor_control_hi.py,
`frame_write_level`; fork:test/test_hi_motor_control.py, `test_frames_never_sent`].

## 7. Qué se puede hacer sin impresora

| Trabajo | Depende de resultados de la Hi |
| - | - |
| `motor_control_hi.py` con tests | No |
| Port de `io_remap.py` y test en batch con los diccionarios reales | No |
| Simulador del bus RS-485 para tests (responde `READ_ADDR`, `PROTECTION`, `GET`, `SYS_PARAM 02`) | No |
| `config/hi/` de la fase 2 validada en batch | No (los valores salen de la captura) |
| Script de solo lectura para el paso 2.1 (ampliar `tools/hi_probe.py`) | No |
| Distancias de cebado y homing real con el bus | **Sí** [supuesto] |

## 8. Plan en la impresora (después de la fase 1)

Todo empieza en solo lectura. Ninguna escritura de parámetros sin aprobación expresa.

| Paso | Acción | Escribe | Criterio |
| - | - | - | - |
| 2.1 | En stock: `QUERY_ENDSTOPS` con el cabezal lejos y pegado a cada final de carrera (motores desactivados, a mano); `MOTOR_READ_ALL_PIN_IO` | No | X e Y cambian de estado; se sabe qué pin es cada uno. **Hecho 2026-11-10 [P]:** Y se lee directo; X solo con `SET_IOREMAP S=1` y comparte línea con Z |
| 2.2 | En stock: leer `param_stall_mode` y `PROTECTION` antes y después de un `G28 X Y` | No (el homing es el de stock) | Se documenta el efecto del modo 1. **Hecho 2026-11-10 [P]:** `PROTECTION` a cero en X (0x81) e Y (0x82) antes y después de `G28 X Y`; el homing deja `homed_axes` = xyz y posición X=-9,0 Y=4,0 Z=10,1. El efecto del modo 1 **no se pudo observar**: solo dura el homing y el macro lo devuelve a 2. `MOTOR_GET DATA=12` de stock no es `param_stall_mode` (devolvió 0, y 0/1 tras mover; esa variable vale 2) |
| 2.3 | Kalico con `startup_writes: none`: `MOTOR_STATUS` | Solo direcciones | 0x81 y 0x82 responden, sin fallos. **Hecho 2026-11-10 [P]:** Kalico `ready` con `phase2.cfg` y `startup_writes: none`; arranque de `motor_control_hi` completo al primer intento; `MOTOR_QUERY_FAULTS`: error, aviso y estado a cero en X e Y; `MOTOR_READ_PARAM x/y_param_stall_mode`: 2 en RAM y en flash. El broadcast `READ_ADDR` a 0xFF agotó el tiempo (1 intento) y el arranque siguió: los dos drivers respondieron después por su dirección [I: ya tenían dirección del stock] |
| 2.4 | `SET_IOREMAP S=1`, `QUERY_ENDSTOPS` y `SET_IOREMAP S=0` en Kalico | Solo el reenvío de pines | Igual que 2.1. **Hecho 2026-11-10 [P]:** con `SET_IOREMAP S=1` y X pulsado, `query_endstops` da `x=1` (y=0, z=0, z1=0); con `S=0` vuelve a 0 y `io_remap.enabled` a `false`. A diferencia del stock, `z` no se activa en Kalico (la config de la fase 2 no usa `PC7` para Z) [I] |
| 2.5 | `startup_writes: stall`; mover X/Y unos mm con `FORCE_MOVE` a baja velocidad | Modo de stall | Movimiento suave, sin fallos. **Hecho 2026-11-10 [P]:** `startup_writes: stall` (5 pasos, sin errores); `FORCE_MOVE` sin fallos de driver. X: +X se aleja del origen; a 5 mm/s suena grave y áspero, y desde 10 mm/s sube a ruido normal de impresión (10, 20 y 40 mm/s probados). Y: a 20 mm/s suena bien. El final de carrera de Y está en Y− [usuario, corregido]; `FORCE_MOVE` con distancia negativa acerca la cama a él y con positiva la aleja [P], el mismo sentido que el homing de stock (`position_endstop: -6`). No hay que invertir `dir_pin`. Drivers: 102 de 103 parámetros leídos coinciden con `motor_control.cfg` del usuario |
| 2.6 | Levantar Z 5 mm; `G28 Y`, `G28 X` con la mano en el interruptor | Modo de stall | Homing correcto y repetible. **Hecho 2026-11-10 [P]:** con Z a altura segura (puente hacia el centro del recorrido) y sin tocarlo, `G28 Y` y `G28 X` (desde una posición alejada) terminan con `homed_axes` = xy, X=-19,0, Y=4,0 (X sin retirada, `homing_retract_dist: 0`); paran suaves, doble disparo en Y (delta 0,0375 mm, el mismo en dos tandas), ruido igual al del stock, sentido correcto (el usuario vigilaba). Sin fallos en los drivers; `param_stall_mode` vuelve a 2 y `io_remap` a `false` tras cada homing. Cebado de 0,1 mm a 20 mm/s, una vez por reinicio. **`G28 X Y` con X ya en el tope: solo se movió Y** [P, usuario]; X no se movió porque ya estaba pulsado el final de carrera [I]. El `_HOME_X` de stock se aparta 10 mm antes si X < 10 y `phase2.cfg` no lo hace; `G28 X Y` desde una posición alejada **sin probar** |
| 2.7 | Comparar parámetros leídos con la captura (solo informe) | No | 51/51 por eje. **Hecho 2026-11-10 [P]:** 102 de 103 parámetros leídos en vivo coinciden con `motor_control.cfg` del usuario; sin lectura `x_cmd_int_param_char_cmd_support` |

## 9. Decisiones (todas cerradas)

1. **Cómo adaptar `motor_control.py`**: decidida el 2026-11-10, copia aparte (D8 en
   [decisions.md](decisions.md)).
2. **Escrituras en el arranque**: decidida el 2026-11-10, niveles `none` → `stall` → `params` (D9).
3. **Homing en la fase 2**: decidida el 2026-11-10, solo X/Y con Z bloqueado (D10).
4. **Dato tuyo**: respondido el 2026-11-10. Hay sensores físicos en X e Y; el orden no es obligatorio; hay que
   levantar Z antes (§4 y §5).

## 10. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | La lectura de §4 sobre `PC7`/`PB13` es errónea | Paso 2.1 antes de escribir config definitiva |
| R2 | El broadcast de direcciones deja un driver sin dirección | El stock lo hace en cada arranque; reiniciar en stock lo restaura [supuesto] |
| R3 | Una clave de parámetro en la config provoca una escritura | `startup_writes: none` ignora las claves; test que lo comprueba |
| R4 | Kalico y el Klipper de stock a la vez en `/dev/ttyS5` | `hi_kalico.sh` ya para el stock antes de arrancar [verificado: scripts/hi_kalico.sh:104] |
| R5 | Movimiento de cebado contra un tope | Revisar distancias; primera prueba con `G28` de un solo eje y velocidad baja |
