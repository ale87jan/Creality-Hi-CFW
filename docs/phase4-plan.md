# Fase 4 — Módulos legibles de la Hi

Análisis del 2026-11-10, hecho sin impresora. Alcance: los cinco módulos Python de Creality que la Hi trae en
claro y que el fork no tiene: `z_align.py`, `nozzle_clear.py`, `bl24c16f.py`, `tmc_line_check.py` y
`timer_read.py`. `io_remap.py` ya se portó en la fase 2. He leído entero el esquema de los cinco (opciones,
comandos, mensajes de MCU, dependencias) y entera la lógica de `z_align.py`; de los otros cuatro solo las
partes citadas.

Notación como en [phase2-plan.md](phase2-plan.md): `fork:`, `stock:`, `captura:`; cada afirmación lleva
`[verificado: ...]` o `[supuesto: ...]`. Los `.py` de stock se han leído, nunca ejecutado.

**Depende de las fases 1 a 3**, ninguna probada aún en la Hi.

## 1. Conclusiones

1. Solo `z_align` es necesario para imprimir bien: es parte del `G28 Z` de stock (§2). Los otros cuatro son
   limpieza de boquilla, recuperación tras corte de luz y diagnóstico de fábrica (§4 a §7).
2. El `z_align.py` de la K2 no vale: pide `safeDist` y `z_align_force_stop`, que la MCU de la Hi no tiene (§3).
3. El `z_align.py` de la Hi tampoco se puede copiar tal cual: depende de cuatro parches de Creality al núcleo
   de Klipper que Kalico no tiene (§3).
4. El `homing.py` del fork espera de `z_align` una interfaz de ocho métodos que el módulo de la Hi no tiene
   (§3). Hay que decidir si el módulo de la Hi imita esa interfaz o se orquesta con macros (§10, decisión 1).
5. `nozzle_clear.py` depende de internos de `prtouch_v3` y de un comando `ZHOME` que el `prtouch.py` del fork
   no tiene: es una reescritura, no una copia (§4).
6. Recomiendo no portar `timer_read` y dejar `bl24c16f` y `tmc_line_check` para cuando hagan falta (§10).

## 2. Qué hace el stock en `G28 Z`

Secuencia de stock cuando existe `[z_align]` [verificado: stock:klippy/extras/homing.py:415-426, 444-462]:

| Paso | Qué hace | Referencia |
| - | - | - |
| 1 | `BED_MESH_CLEAR` | stock:homing.py:420 |
| 2 | Va al centro de la cama a 50 mm/s | stock:homing.py:445 |
| 3 | Lee los dos sensores ópticos de Z; si los dos están activos, error `key357` | stock:homing.py:450-458 |
| 4 | `ZDOWN`: la MCU sube el puente de X con los dos motores hasta los sensores ópticos de arriba y los iguala | stock:z_align.py:194-256 |
| 5 | Fija Z al `zmax` real guardado, sube 10 mm y llama a `ADJUST_STEPPERS` | stock:z_align.py:258-273 |
| 6 | Homing normal de Z con la sonda (el puente baja hasta que la boquilla toca la cama) | stock:homing.py:423 |
| 7 | Guarda el `zmax` real medido (`z_move + out_z_all`) en un fichero JSON | stock:homing.py:426, 436-442 |

Mecánica [usuario, 2026-11-10]: la Hi es cartesiana de cama móvil. La cama solo se mueve en Y; Z mueve el
puente del eje X con dos husillos. Los sensores ópticos de Z están **arriba del todo**. `ZDOWN` hereda el nombre
de la K2 (CoreXY, donde la cama baja): en la Hi **sube el puente** hasta esos sensores, lejos de la cama. Por eso
el stock fija después Z al `zmax` real, y el homing con la sonda baja desde ahí.

Datos de la Hi:

- Sensores ópticos de Z en `PB15` (Z) y `PB14` (Z1), `zes_untrig: 0`, `zd_up: 0`
  [verificado: stock:config/F018_CR4NU200360C20/printer.cfg:364-378].
- Los mismos pines están declarados como `filament_switch_sensor filament_sensor_4` (`PB14`) y
  `filament_sensor_5` (`PB15`); así lee el host su estado [verificado: stock:printer.cfg:397-402;
  stock:z_align.py:94-97].
- Parámetros de stock: `quick_speed: 20`, `slow_speed: 5`, `rising_dist: 5`, `safe_rising_dist: 15`,
  `filter_cnt: 10`, `timeout: 30`, `retries: 7`, `retry_tolerance: 10` pasos (0,025 mm), `diff_z_offset: 0.5`
  [verificado: stock:printer.cfg:364-378].
- `ZDOWN_SWITCH ENABLE=0` salta la alineación en el siguiente `G28 Z` [verificado: stock:homing.py:416-419;
  stock:gcode_macro.cfg:795-802].
- `UP_SAFE_Z` usa un segundo objeto de MCU (`config_z_align_up`, `query_z_align_up`) para subir
  `safe_rising_dist` antes del homing; lo llama la macro `_IF_HOME_Z` [verificado: stock:z_align.py:141-192;
  stock:sensorless.cfg:36, 45].

Sin `z_align`, el `G28 Z` del fork baja el puente con la sonda desde donde esté
[verificado: fork:klippy/extras/homing.py:1183-1190]. Funciona, pero los dos husillos no se igualan arriba
y no hay medida del `zmax` real.

## 3. `z_align`: tres piezas que no encajan

### MCU

| Mensaje | Hi (`test/hi/mcu.dict`) | K2 (`fork:z_align.py`) |
| - | - | - |
| `config_z_align`, `config_z_align_add` | Sí, misma firma | Líneas 131-152 |
| `query_z_align ... filterCnt=%c` | Sí, **sin** `safeDist` | Pide `safeDist=%u` (168-171) |
| `z_align_force_stop oid=%c` | **No existe** | Lo usa para abortar (173-174, 410-414) |
| `config_z_align_up(_add)`, `query_z_align_up` | Sí | No los usa |
| `query_z_align2` | Sí; ningún `.py` de stock lo usa | No lo usa |
| `z_align_status oid flag deltaError1` | Sí | Sí |

[verificado: fork:test/hi/mcu.dict, búsqueda de `align`; fork:klippy/extras/z_align.py en las líneas citadas]

Consecuencia: en la Hi no hay forma de parar la MCU a mitad de una alineación. Si el host agota el `timeout`,
los motores siguen hasta que la MCU termine por su cuenta [supuesto: no se conoce el firmware; comprobarlo en
el paso 4.3 con el puente cerca del tope superior].

### Parches de Creality de los que depende el módulo de la Hi

| Dependencia | Dónde | En Kalico |
| - | - | - |
| `mcu._serial.z_align_status` (caché en `serialhdl.py`) | stock:z_align.py:226-229; stock:serialhdl.py:36, 316-317 | No existe. El módulo de la K2 lo resuelve con un gancho propio (`fork:z_align.py:277-293`) |
| `toolhead.G29_flag` | stock:z_align.py:258 | No existe |
| `ADJUST_STEPPERS` y `z_tilt.real_zmax_path` | stock:z_align.py:271, 293-296; stock:z_tilt.py:167, 187 | No existen en `z_tilt.py` ni `z_tilt_ng.py` [verificado: búsqueda en fork:klippy] |
| `gcode._respond_error` con JSON `key351`/`key352`/`key357` | stock:z_align.py:225, 242, 111 | No existe; se sustituye por `gcmd.error` |
| `import mcu` de nivel superior | stock:z_align.py:1 | Hay que usar import relativo |

### Interfaz que espera el `homing.py` del fork

`needs_prep`, `start_prepare`, `wait_prepare_complete`, `perform_blocking_rise`, `perform_unmonitored_rise`,
`is_active`, `abort_internal`, `invalidate_homing_state`
[verificado: fork:klippy/extras/homing.py:757-779, 829-835, 1136-1144, 1183-1201]. El módulo de la K2 baja y
alinea **en paralelo** con el homing de X/Y y después sube `rise_distance` antes de la sonda
[verificado: fork:z_align.py:561-600, 663-776]. El de la Hi lo hace en serie, con X/Y ya en el centro.

Si el objeto `z_align` no existe, `homing.py` no llama a nada de esto (todas las llamadas comprueban `None`).

### Dos formas de portarlo

- **A. `z_align_hi.py` derivado del módulo de la K2**, como se hizo con `motor_control_hi.py` (D8): se cambia el
  mensaje a la firma de la Hi, se quita `force_stop` y `safeDist`, y se registra como `z_align` para que
  `homing.py` lo use. Mantiene la preparación en paralelo, el aborto del lado del host y la subida vigilada.
  Pierde las dos protecciones de MCU de la K2, así que hay que revisar qué hace cada camino de aborto sin ellas.
  El módulo de la K2 tiene 817 líneas y lógica propia (`TILT_BIAS_FILE`, `rise_distance: 340` para una Z de
  350 mm) que hay que adaptar a los 310 mm de la Hi [verificado: fork:z_align.py:48, 86, 92;
  fork:config/hi/printer.cfg:97].
- **B. `z_align_hi.py` portado del módulo de la Hi**, con otro nombre de objeto para que `homing.py` no lo
  integre: comandos `ZDOWN`, `UP_SAFE_Z`, `CHECK_ZLIMIT` y `ZDOWN_SWITCH`, y una macro que hace
  `ZDOWN` y luego `G28 Z`. Unas 300 líneas, mismo comportamiento que el stock ya probado en este hardware. Hay
  que reescribir las cuatro dependencias de la tabla anterior; la más delicada es sustituir `ADJUST_STEPPERS`
  (reaplicar la última corrección de `Z_TILT_ADJUST`) por un `Z_TILT_ADJUST` nuevo tras cada homing o por una
  corrección guardada en `save_variables`.

Recomiendo **B**: es el comportamiento que la MCU de la Hi tiene verificado en fábrica, el módulo es corto y
auditable, y no depende de protecciones que la MCU no ofrece. El coste es que el homing de Z tarda más (en
serie) y que la macro de `G28` hay que mantenerla.

## 4. `nozzle_clear`

- Comandos: `NOZ_CLEAR` y `FORECEZ` [verificado: stock:nozzle_clear.py:47-48].
- Config de stock: `clear_temp: 170`, `enable_clear: true`, `start_pos: 98, 266`, `touch_cnt: 3`,
  `clear_start: 148, 266`, `probe_pos_diff: 0, 0`, `clear_lenght: 14, 2`, `upraise: 0.2`, `clear_cnt: 10`
  [verificado: stock:printer.cfg:351-360]. La zona de limpieza es una pieza de teflón en la
  parte trasera (Y=266 de 274) [usuario, 2026-11-10].
- Dependencias que el fork no tiene:
  - `prtouch_v3.pres.tri_hold`, que modifica en caliente para subir el umbral de disparo
    [verificado: stock:nozzle_clear.py:75-77].
  - `ZHOME` [verificado: stock:nozzle_clear.py:91]; el `prtouch.py` del fork no lo registra
    [verificado: búsqueda de `ZHOME` en fork:klippy/extras/prtouch.py, sin resultados].
  - `[box] extrude_pos_x` cuando `extr_enable` [verificado: stock:nozzle_clear.py:46].
  - `SET_PIN PIN=fan0` [verificado: stock:nozzle_clear.py:104].
- El `homing.py` del fork llama a `NOZZLE_CLEAN` (otro nombre) antes de tocar la cama si `[prtouch]` tiene
  `register_as_probe` [verificado: fork:homing.py:1131-1135]. Ese comando lo registra `box.py` y usa la
  almohadilla trasera de la K2 [verificado: fork:klippy/extras/box.py:634]; sin `[box]` hay que definirlo como
  macro.

El fork trae otras dos limpiezas, ninguna pensada para la Hi:

| Comando | Módulo | Config | Encaje en la Hi |
| - | - | - | - |
| `PRTOUCH_SCRUB` | `fork:prtouch.py:148-168, 253` | `[prtouch] scrub_x_start: 173`, `scrub_x_end: 223`, `scrub_y_min: 353`, `scrub_y_max: 356` | Los valores por defecto caen fuera de la cama (Y máx. 274) y busca la lengüeta flexible trasera de la K2. No he comprobado si sirve cambiando solo las coordenadas |
| `NOZZLE_CLEANUP` | `fork:nozzle_cleanup.py` (178 líneas, genérico de Kalico) | Sección propia: `pattern_x: 10`, `pattern_y: 4`, `pattern_stepover`, `samples: 3` | Toques con la sonda en un patrón sobre la cama. Solo he leído el esquema (líneas 29-57, 103-173) |

### Lectura de `PRTOUCH_SCRUB` (2026-11-10)

[verificado: fork:klippy/extras/prtouch.py:940-1087]

- Es un frotado **en frío y mecánico**: toca tres veces en el centro del tramo con dos umbrales para detectar
  la lengüeta, toca en los dos extremos y arrastra la boquilla ida y vuelta entre ellos a `scrub_speed`,
  hundida `scrub_tab_depth` (0,15 mm) o `scrub_no_tab_depth` (0,05 mm) por debajo de la altura de contacto.
  Repite hasta tres veces, hasta que la boquilla "acorta" menos de 0,01 mm. No calienta ni retrae.
- Dependencias: el objeto `extended_zone_transform` para todos los movimientos (línea 940-942) y la macro
  `HOME_IF_NEEDED AXIS=XYZ` (línea 1003). La Hi no tiene zona extendida; habría que cargar ese módulo solo para
  esto [supuesto: no he comprobado si admite una zona vacía].
- En la Hi, con coordenadas dentro de la cama, arrastraría la boquilla fría y hundida 0,05 mm sobre la
  superficie que haya en ese punto. Es un comportamiento distinto del de stock, que funde y sella.

### La limpieza del usuario

`nozzle_cleaning_macros.cfg` del usuario redefine `NOZ_CLEAR` con dos macros, `NOZZLE_WIPE` y
`NOZZLE_QUICK_WIPE`, que reproducen la secuencia de stock **solo con G-code**: `M104`/`M109`, `G28 Z`, `PROBE`
con `PROBE_SPEED` y `SAMPLE_RETRACT_DIST`, `G0`, `SET_KINEMATIC_POSITION Z=0` y `M106`
[verificado: captura:printer-config/nozzle_cleaning_macros.cfg]. No tocan `tri_hold` (está comentado) ni usan
`ZHOME`. Solo dependen del stock para leer valores: `printer.configfile.settings['nozzle_clear']`, `['box']` y
la macro `PRINTER_PARAM`.

Es la vía más corta: pasar esos valores a variables de una macro y dejar el resto igual. Funciona con el
`prtouch.py` de la K2 sin cambios, porque solo usa `PROBE`
[supuesto: comprobar en batch que `PROBE PROBE_SPEED=... SAMPLE_RETRACT_DIST=...` se acepta].

Criterio del usuario (2026-11-10): si `PRTOUCH_SCRUB` funciona en la Hi, se mantiene el de la K2; si no, una
limpieza propia de la Hi con `NOZZLE_CLEANUP` o con sus macros. Con lo leído, `PRTOUCH_SCRUB` no es
equivalente y no se puede dar por bueno sin impresora; la opción con menos riesgo son sus macros.

## 5. `bl24c16f`

- EEPROM I2C en la MCU Linux del host: `i2c_mcu: rpi`, `i2c_bus: i2c.1`, y `[mcu rpi]` en
  `/tmp/klipper_host_mcu` [verificado: stock:printer.cfg:39-45]. Abre ocho direcciones I2C
  [verificado: stock:bl24c16f.py:203-218].
- Solo lo usa el `virtual_sdcard.py` parcheado de Creality para la recuperación tras corte de luz
  [verificado: stock:virtual_sdcard.py:499-502, 679-684, 1047-1137]. Kalico no tiene ese parche.
- El módulo en sí solo depende de `bus` y es copiable con cambios mínimos. Sus comandos `EEPROM_WRITE_*` y
  `EEPROM_DEBUG_WRITE_*` escriben en una memoria que también usa el firmware de stock
  [verificado: stock:bl24c16f.py:101-196].
- El fork tiene `power_loss_recovery.py` [verificado: fork:klippy/extras/]; no lo he leído ni sé si usa EEPROM
  [supuesto: leerlo en la fase 6 antes de decidir].

No aporta nada hasta que se quiera la recuperación tras corte de luz. Si se porta antes, solo los comandos de
lectura.

## 6. `tmc_line_check`

- Comandos `READ_REG_TMC`, `CHECK_MOTOR_LINE` y `CHECK_ZMOTOR_LINE`: mueve 0,5 mm con `FORCE_MOVE` y lee un
  registro del TMC2208 para detectar un cable de motor suelto [verificado: stock:tmc_line_check.py:16-18,
  39-95].
- En la Hi solo Z, Z1 y el extrusor tienen TMC2208 [verificado: stock:printer.cfg:112, 127, 201]; X/Y son de
  lazo cerrado.
- Usa `mcu_tmc.test_get_register`, un método añadido por Creality [verificado: stock:tmc_line_check.py:43]
  [supuesto: en Kalico se sustituye por `mcu_tmc.get_register(nombre)`; comprobarlo al portar].

Diagnóstico de fábrica. Kalico ya ofrece `DUMP_TMC`. Baja prioridad.

## 7. `timer_read`

Envía por UDP las lecturas de presión (`READ_PRES_PA C=45`) y la temperatura a la IP `prth_dbg_ippt` de
`prtouch_v3` (127.0.0.1 en stock) cada 0,1 s [verificado: stock:timer_read.py:17, 70-74, 97-100;
stock:printer.cfg:157, 408-411]. Es instrumentación de depuración de Creality y depende de `prtouch_v3`. No
tiene uso con el `prtouch.py` del fork.

## 8. Qué se puede hacer sin impresora

1. Cerrar las decisiones del §10.
2. `z_align_hi.py` según la decisión 1, con tests en batch: que emite `config_z_align`, `config_z_align_add`
   (y los `_up`) con `PB15`/`PB14` y los pines de paso y dirección de Z y Z1, y que `ZDOWN` envía
   `query_z_align` con los ticks y pasos que salen de los valores de stock.
3. Un test con MCU simulada para el bucle de reintentos y el `timeout` de `ZDOWN`.
4. `config/hi/phase4.cfg` con `[z_align_hi]` y la macro de `G28`.

Todo ello depende de que la fase 3 funcione en la Hi; se marca como no probado.

## 9. Plan en la impresora (después de la fase 3)

| Paso | Qué | Escribe o mueve |
| - | - | - |
| 4.1 | Con stock: `QUERY_FILAMENT_SENSOR SENSOR=filament_sensor_4` y `_5` con el puente arriba del todo y a media altura. Confirma polaridad y qué sensor es cada husillo | No |
| 4.2 | Con stock: `G28 Z` y copiar del log las líneas `send query_z_align` y `z_align_status`. Da los ticks, los pasos y el `deltaError1` de referencia | Mueve (stock) |
| 4.3 | Con Kalico: `CHECK_ZLIMIT` y después `ZDOWN` con el puente a menos de 30 mm de los sensores de arriba, mano en el interruptor | Mueve Z |
| 4.4 | `ZDOWN` desde media altura; comparar `deltaError1` con el de 4.2 | Mueve Z |
| 4.5 | `G28` completo (X/Y, `ZDOWN`, sonda) y comparar Z=0 y `zmax` con stock | Mueve todo |

## 10. Decisiones que necesito

Orden decidido (D12, 2026-11-10): esta fase se prueba **antes** que la sonda (fase 3).

1. **Cómo portar `z_align`**: B, portar el módulo de la Hi con sus comandos y una macro de `G28`
   (recomendada); o A, derivarlo del módulo de la K2 para integrarlo en el `homing.py` del fork (§3).
2. **Qué módulos se portan**: solo `z_align` y `nozzle_clear` (recomendada); `bl24c16f` y `tmc_line_check`
   quedan en el backlog sin fecha y `timer_read` no se porta. Alternativa: portarlos todos ahora.
3. **Limpieza de boquilla**: reescribir `nozzle_clear` de la Hi sobre el `prtouch.py` del fork, con los
   valores de stock (recomendada por ahora); usar `NOZZLE_CLEANUP` de Kalico; o `PRTOUCH_SCRUB` con coordenadas
   de la Hi. Se decide después de leer las dos alternativas (tarea B27).

## 11. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | La MCU no se puede parar durante `ZDOWN` (no hay `force_stop`) | Paso 4.3 cerca del tope superior; `timeout` de stock; mano en el interruptor |
| R2 | Un sensor óptico roto o tapado hace que un husillo siga subiendo contra el tope superior | `CHECK_ZLIMIT` antes, como el stock (`key357`) |
| R3 | Polaridad de `zd_up`/`zes_untrig` mal copiada mueve el puente hacia la cama en vez de hacia arriba | Valores de stock sin tocar; test en batch que los fija; paso 4.1 |
| R4 | Sin `ADJUST_STEPPERS`, la corrección de inclinación se pierde en cada `ZDOWN` | `Z_TILT_ADJUST` después de cada `G28` hasta tener sustituto |
| R5 | Sin limpieza de boquilla, Z=0 varía con los restos de filamento | Medirlo en 3.5; `NOZZLE_CLEAN` real antes de imprimir |
