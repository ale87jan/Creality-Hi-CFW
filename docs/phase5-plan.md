# Fase 5 — CFS

Análisis del 2026-11-10, hecho sin impresora y **ligero**: cubre qué partes del código de CFS del fork valen
para la Hi y cuáles no, a partir de las opciones, los pines y la rutina de corte. No he leído la lógica de carga,
descarga, purga ni cambio de color (`box.py` y `box_change.py`, casi 5000 líneas); eso es la tarea B32.

Notación como en [phase2-plan.md](phase2-plan.md): `fork:`, `stock:`, `captura:`; cada afirmación lleva
`[verificado: ...]` o `[supuesto: ...]`.

**Depende de las fases 1 a 4**, ninguna probada aún en la Hi. El cambio de filamento mueve X/Y, calienta, corta
y extruye: es la última pieza.

## 1. Conclusiones

0. Notación adicional: `ref:` es `gitstonelabs/creality-cfs-klipper` en el commit `16309d8`.
1. En stock, `box`, `auto_addr` y `filament_rack` son `.so` cerrados
   [verificado: stock:klippy/extras/box.py:1, auto_addr.py:1, filament_rack.py:1]. No hay código de la Hi que
   leer; la referencia es su config y el código abierto de la K2.
2. Las capas de bus y protocolo del fork (`serial_485.py`, `box_addr.py`, `box_protocol.py`) no tienen nada
   propio de la K2 a la vista y la trama es la misma [verificado: docs/analysis/k2-port-feasibility.md:54, 64,
   67]. Se pueden probar en solo lectura (§5).
3. `box.py` **no vale tal cual**. Tiene fijos el pin del sensor de corte, el sentido del corte y la geometría de
   la zona trasera de la K2 (§3).
4. El CFS comparte el bus RS-485 con los drivers de X/Y. `motor_control_hi` y `box` usan el mismo objeto
   `serial_485 serial485` [verificado: fork:klippy/extras/box.py:690; fork:config/hi/phase2.cfg].
5. La app del CFS de la Hi es más antigua (`cfs0_000_113`) que la de la K2 (150/153)
   [verificado: docs/hardware.md, sección CFS]. `box_protocol.py` no comprueba versión y su decodificador es
   estricto: si una respuesta cambia, falla sin actuar [verificado: docs/analysis/k2-port-feasibility.md:67].

### Referencia externa: `gitstonelabs/creality-cfs-klipper`

El usuario la señala (2026-11-10) como referencia para implementar el CFS. Primera lectura hecha el mismo día
sobre el commit `16309d8` (2026-07-30), clonado solo para leer; no he leído la lógica de `creality_cfs.py`
(3839 líneas), solo cabecera, constantes, opciones y documentación [verificado: ref:README.md,
ref:src/creality_cfs.py:1-700, 969-1023, ref:configs/printer.cfg.example].

- **Licencia GPLv3** (`ref:LICENSE`), como Kalico: se puede reutilizar código citando el origen.
- **La Hi (F018) es su hardware de referencia**. El protocolo sale de capturas del bus con CRC verificado; la
  coreografía (carga, descarga, corte, purga) se validó en una Hi real con CFS hasta el 2026-07-01
  (`ref:README.md`, sección Status; `ref:src/creality_cfs.py`, nota v1.4.0).
- **Mismos códigos de función que el fork**: `0x02`, `0x03`, `0x04`, `0x05`, `0x08`, `0x0A`, `0x0D`, `0x0E`,
  `0x10`, `0x11`, `0xA0`-`0xA2` y `0x0B` aparecen en los dos, con nombres distintos en algunos (`0x04`
  `SET_BOX_MODE` frente a `CMD_TRACKING`; `0x08` `GET_HARDWARE_STATUS` frente a `CMD_SLOT_MASK`)
  [verificado: ref:src/creality_cfs.py:353-394; fork:klippy/extras/box_protocol.py:24-38]. Falta comparar
  cargas útiles y respuestas (B31b). La referencia añade `0x0F` (motor de conexión), `0x14` y `0xF0` (versión).
- **Confirma la geometría de corte de la Hi**: `cut_switch_pin: !toolhead_mcu:PB1`, `pre_cut_pos_x: 240`,
  `pre_cut_pos_y: 130`, `cut_pos_x: 283.5`, `cut_pos_x_max: 285` (`ref:configs/printer.cfg.example:99-107`).
  Coincide con el stock (§2) y resuelve el supuesto de que `switch_pin` es el sensor de la cuchilla.
- **Problema para usarlo tal cual en la Hi con Kalico**: el módulo abre él mismo el puerto serie y no comparte
  `serial_485` (`ref:src/creality_cfs.py:101-107`). En la Hi ese puerto es el bus de los drivers de X/Y, que
  `motor_control_hi` usa a través de `serial_485`. Dos módulos sobre el mismo puerto no pueden convivir. El
  autor menciona una variante para la Hi sobre `serial_485` (`ref:src/creality_cfs.py:37-39`), que no está en
  el repositorio [verificado: listado de ficheros].
- **Envía una trama a la dirección de un driver**: su lectura de diagnóstico `0x0C` va a `0x81` con carga
  `0B` (`ref:src/creality_cfs.py:2345-2358`). Para nosotros esa trama es `PROTECTION` consultar errores del
  driver de X, de solo lectura [verificado: docs/protocols/rs485.md:48]. Su captura `f7 81 04 00 0c 0b`
  coincide con nuestra descripción de la trama. No es peligrosa, pero no es del CFS.

### Comparación trama a trama con la referencia (B31b y B31, 2026-11-10)

Fuentes: `ref:docs/protocol.md:234-620` (capturas del bus de una Hi con CRC verificado, según el autor) y
`fork:klippy/extras/box_protocol.py:24-38, 392-764`. La columna "Hi" es lo que la referencia dice haber visto
en el bus; no lo he comprobado en la impresora [supuesto: paso 5.2].

| Func. | Fork (K2) | Hi según la referencia | ¿Coincide? | Clase |
| - | - | - | - | - |
| `0xA1`, `0xA2`, `0xA0`, `0x0B` | Descubrir, consultar, asignar dirección, pasar a app (`:741-764`) | Mismas cargas (`ref:protocol.md:238-244`); la Hi añade `0xA3` | Sí | `A1`/`A2` lectura; `A0` y `0B` cambian estado |
| `0x02` | `[máscara]`; respuesta ASCII `A:...;B:...;` (`:521-554`) | Igual; con `0x0F` puede tardar ~11 s | Sí | Lectura |
| `0x03` | `[máscara]`; 4 bytes (`:556-568`) | Igual; `0xFF` = ranura no pedida | Sí | Lectura |
| `0x04` | `(0, 1)` sin ranura, `(ranura, 0)` con ranura (`:637-644`) | `[00][01]` modo alimentación, `[ranura][00]` modo impresión | Sí | Escribe estado |
| `0x05` | Sin carga; 1 byte (`:672`) | Igual: 0 medio, 1 lleno, 2 vacío | Sí | Lectura |
| `0x08` | `(0)` máscara de ranuras, `(1)` máscara del hub; rechaza bits altos (`:660-670`) | `[canal]` 0 material, 1 conexiones; visto `0x00`, `0x01`, `0x07` | Sí en forma; nombres distintos | Lectura |
| `0x0A` | Sin carga; **exige 6 bytes** (o 4 con estado `0x30`) y un estado entre 0 y 5 (`:475-510`) | Sin carga; **4 bytes** `[b0][b1][b2][b3]` con estado `0x00`; `b3 = 0x02` cargado | **No**: el decodificador del fork rechazaría la respuesta normal de la Hi ("payload has the wrong shape") | Lectura |
| `0x0D` | `(0, 0/1)` lectura de RFID al insertar; `(máscara, 2)` lectura forzada, 190 s por ranura (`:705-728`) | `[0F][00]` armar precarga, `[0F][01]` desarmar, `[ranura][02]` rearmar (bloquea ~38 s) | **Parcial**: mismo código, otra máscara y otro significado | Escribe estado; la fase 2 mueve |
| `0x0E` | `(1)`; float big-endian (`:679-693`) | Igual | Sí | Lectura |
| `0x0F` | **No existe** en el fork | Motor de conexión: `[01]` acoplar, `[00]` soltar; envuelve cada carga | **No** | Mueve |
| `0x10` | `(ranura, etapa, arg)`, etapas 0, 4, 5, 6 y 7 con `arg = 3` en la 7 (`:612-621`) | `[ranura][etapa][arg]`: `00 00`, `04 00`, `05 00`, `06 00`, `07 03` | Sí en la petición; longitudes de respuesta sin comparar | Mueve |
| `0x11` | Fase 0 `(0, 0)`, fase 1 `(ranura, 1)` (`:627-635`) | `[ranura][00]` inicio, `[ranura][01]` fin (retenido ~9,6 s) | **No** en el primer byte de la fase 0 | Mueve |
| `0x14`, `0xF0` | No existen | Versión y número de serie | — | Lectura |

Consecuencias:

- La conclusión 2 de arriba se queda corta: valen el transporte (`serial_485.py`) y el sobre de la trama, pero
  **la capa de órdenes del fork no es la de la Hi**. Lo más grave es `0x0A`, que `box.py` consulta de continuo:
  con el firmware `cfs0_000_113` cada consulta acabaría en `ProtocolError`. Encaja con la conclusión 5 (app
  más antigua que la de la K2).
- Para el paso 5.2 (solo lectura) sirven `A2`, `0x05`, `0x08`, `0x0E`, `0x03`, `0x14` y `0xF0`; `0x0A` hay que
  decodificarlo como 4 bytes, no con el decodificador del fork.
- La referencia concentra todo el tráfico en una función, `_send_command`, con 19 llamadas
  [verificado: ref:src/creality_cfs.py:1427; recuento con grep]. Cambiar su transporte a `serial_485` es
  sustituir esa función y la apertura del puerto (`:1357`, `register_fd`), no reescribir la coreografía.

Con esto aparece una cuarta forma de adaptar el CFS (§4, opción D).

## 2. Config de stock de la Hi

[verificado: stock:config/F018_CR4NU200360C20/box.cfg y printer.cfg en las líneas citadas]

| Dato | Valor de stock | Línea |
| - | - | - |
| Bus | `/dev/ttyS5`, 230400 | box.cfg:1-3 |
| Aproximación al corte | `pre_cut_pos_x: 240`, `pre_cut_pos_y: 130`, `cut_pos_y: 130` | box.cfg:14 y siguientes |
| Tope de búsqueda del corte | `check_cut_pos_x_max: 280`; `cut_pos_x: 283.5` comentado | box.cfg:16, 40 |
| Límites de X | `position_min: -19`, `position_max: 285` | printer.cfg:79-80 |
| Punto de purga | `extrude_pos_x: -18.50`, `extrude_pos_y: 130`, `has_extrude_pos: 1` | box.cfg |
| Pasada corta para soltar la purga | `clean_left_pos_x: 0`, `clean_right_pos_x: -5`, Y=130, `clean_velocity: 12000` | box.cfg |
| Limpieza en el teflón trasero | `[nozzle_clear]`: `start_pos: 98, 266`, `clear_start: 148, 266` | printer.cfg:351-360 |
| Rodeo del corte a la purga | `detour_pos_y: 261`, `detour_y: True` | box.cfg |
| Retracción y carga | `Tn_retrude: -20`, `Tn_extrude: 140`, `Tn_extrude_temp: 220`, `buffer_empty_len: 30` | box.cfg |
| Longitudes de limpieza | `box_need_clean_length: 60`, `box_first_clean_length: 70`, `..._max: 80` | box.cfg |
| Pin en `[box]` | `switch_pin: !nozzle_mcu:PB1` | box.cfg:41 |
| Sensor de filamento | `filament_sensor`, `!nozzle_mcu:PB15` | printer.cfg:381-383 |
| Rack externo | `[filament_rack] need_clean_length: 63`, `first_clean_length: 66` | box.cfg:7-9 |

La Hi corta en +X (derecha), purga fuera de la cama por la izquierda (X=-18,5), **donde está la papelera**, y
limpia en una pieza de teflón **trasera**, en la posición de `[nozzle_clear]` [usuario, 2026-11-10]. Los
valores `clean_left_pos_x`/`clean_right_pos_x` de `[box]` (X entre -5 y 0, Y=130) son otra pasada, corta, junto a
la papelera, para soltar el material purgado [usuario, 2026-11-10].

`switch_pin` es el sensor de la cuchilla [verificado: ref:configs/printer.cfg.example:99-102, que lo llama
`cut_switch_pin`]. El paso 5.1 lo comprueba en la impresora.

## 3. Qué tiene fijo `box.py` de la K2

| Punto | En el fork | En la Hi |
| - | - | - |
| Sensor de corte | `nozzle_mcu:PB9`, fijo en el código (`box.py:576-580`) | `PB9` es `fan2_pin`, el ventilador de modelo (stock:printer_params.cfg:20). El sensor sería `nozzle_mcu:PB1` |
| Sentido del corte | Hacia -X: amplía `position_min` hasta `cut_pos_x - 5` (`box.py:2395, 2472-2477`); por defecto `pre_cut_pos_x: 10`, `check_cut_pos_x_max: -5.5` (`box.py:521, 532-533`) | Hacia +X: habría que ampliar `position_max` |
| Papelera | `wastebin_pos_x/y` y aproximación, con validación que exige la papelera detrás y a la izquierda (`box.py:482-494`) | Papelera a la izquierda, fuera de la cama: purga en X=-18,5, Y=130 |
| Almohadilla | `clean_pad_left_x: 154`, `clean_pad_front_y: 367` (`box.py:496-498`); `NOZZLE_CLEAN` la usa (`box.py:634`) | Teflón trasero en la posición de `[nozzle_clear]` (Y=266) |
| Zona de servicio | Movimientos por `extended_zone_transform` (`box.py:2227-2230`) y `motion_limits` (`box.py:23`) | La Hi no tiene zona trasera extendida |
| Macro | `HOME_IF_NEEDED AXIS=XY` (`box.py:2394`), definida en `config/k2/macros.cfg:21` | Hay que definirla |
| Calibración del corte | `CALIBRATE_CUT_POS` estaba en `motor_control.py` | Quitada en `motor_control_hi.py` (D8); `cut_pos_x` se fija a mano |
| Rack externo | `external_rfid_reader.py` | `filament_rack` de stock es un `.so`; no analizado |

[verificado: fork:klippy/extras/box.py en las líneas citadas]

Lo que sí coincide: el nombre del sensor de filamento (`filament_switch_sensor filament_sensor`,
`fork:box.py:1107-1109`) y el nombre del bus.

## 4. Cómo adaptarlo

- **A. Opciones nuevas en `box.py`**: `cut_sensor_pin`, sentido del corte deducido de `cut_pos_x` frente a
  `pre_cut_pos_x`, y la papelera a la izquierda en vez de detrás. Es lo que pide la regla del repositorio (opciones antes que
  editar valores fijos) y permite proponer los cambios a upstream. Toca un módulo compartido de 3382 líneas.
- **B. Copia aparte `box_hi.py`**, como D8. Aísla la Hi, pero duplica 5000 líneas que upstream cambia a menudo.
- **C. Solo capas bajas**: usar `serial_485`, `box_addr` y `box_protocol` y escribir un `box_hi.py` pequeño con
  la secuencia de la Hi (corte en +X, purga en la papelera de X=-18,5, limpieza en el teflón trasero), guiado por las macros de stock
  (`BOX_LOAD_MATERIAL_WITH_MATERIAL` y siguientes, `stock:box.cfg`). Menos funciones al principio (sin mapa de
  colores del laminador ni recuperación), pero cada movimiento es de la Hi.

- **D. `creality_cfs.py` de gitstonelabs con el transporte cambiado a `serial_485`**: la coreografía ya está
  hecha y validada sobre una Hi, con la geometría de stock. Hay que sustituir su capa serie (reactor propio)
  por el bus compartido y quitar la lectura `0x0C` a `0x81`. Es otro juego de comandos (`CFS_INIT`,
  `CFS_STATUS`, `CFS_EXTRUDE`, `CFS_RETRUDE`, `CFS_CUT`, `CFS_FLUSH`), distinto del de la K2 (`BOX_LOAD`...) y
  del de stock (`BOX_*`).

Recomendación tras B31b (2026-11-10): **D**. Es la única coreografía probada en una Hi, y las opciones A a C
heredan una capa de órdenes que no coincide con la Hi en `0x0A`, `0x0D`, `0x0F` y `0x11` (§1), así que además
de la geometría habría que rehacer el protocolo. La alternativa es A para el
pin y el sentido del corte. La decisión depende de cuánto cuesta cambiar el transporte de D.

## 5. Plan en la impresora

| Paso | Qué | Escribe o mueve |
| - | - | - |
| 5.1 | Con stock: leer `nozzle_mcu:PB1` con la cuchilla suelta y empujada a mano; anotar la posición X real del corte | No |
| 5.2 | Con Kalico y `phase5.cfg`: arrancar y comprobar en el log que no sale ninguna trama del CFS (`auto_init` apagado) y que X/Y siguen respondiendo (`MOTOR_STATUS`) | No |
| 5.3 | `CFS_INIT` (descubre y asigna dirección, como hace el stock en cada arranque) y después `CFS_STATUS`, `CFS_VERSION`, `CFS_FW_VERSION`, `CFS_ADDR_TABLE`. Comprobar que `0x0A` devuelve 4 bytes y que los drivers de X/Y siguen respondiendo | Asigna dirección al CFS [supuesto: volátil; el stock la reasigna al arrancar] |
| 5.4 | Corte sin filamento, a baja aceleración, con `cut_pos_x` 2 mm antes del valor medido | Mueve X |
| 5.5 | Carga y descarga de una ranura, sin imprimir | Mueve, calienta, extruye |
| 5.6 | Cambio de color con purga | Todo |

### Hecho el 2026-11-10 (D16, B34 primera parte)

`klippy/extras/creality_cfs.py` en el fork: el módulo de la referencia (commit `16309d8`, GPLv3, con su
cabecera y autoría) más una opción nueva `serial`. Si nombra una sección `[serial_485]`, el módulo no abre el
puerto y cada intercambio pasa por ese transporte; sin la opción se comporta como el original. El cambio es
aditivo (48 líneas añadidas, 1 cambiada) para poder proponerlo al autor. `config/hi/cfs.cfg` y `phase5.cfg`;
9 tests (`test/test_hi_cfs.py`). Nada probado en la impresora.

- La trama que llega al bus es byte a byte la que construye el módulo: `serial_485` recibe la trama sin
  cabecera ni CRC y los añade con el mismo algoritmo [verificado: test
  `test_shared_bus_puts_the_same_frame_on_the_wire`; fork:serial_485.py:516-530].
- `serial_485` empareja la respuesta por dirección y función, y por función sola en difusión, igual que el
  original [verificado: fork:serial_485.py:545-556; fork:creality_cfs.py `_dispatch_rx`].
- `auto_init: False` en `cfs.cfg`: al arrancar no se envía nada al CFS [verificado: test
  `test_phase5_config_loads_and_sends_nothing_at_startup`]. `CFS_INIT` solo hace el autodireccionamiento; la
  precarga del arranque automático no se ejecuta [verificado: fork:creality_cfs.py, `cmd_CFS_INIT`].
- La lectura de diagnóstico `0x0C` a `0x81`/`0x82` no se envía en el bus compartido (son los drivers de X/Y);
  ningún comando la llamaba [verificado: búsqueda de `read_buffer_block_0x0c(` en el fichero].

Límites y pendientes:

1. `NOTICES.md` de la referencia dice que la coreografía se validó en una Hi con la implementación de la que
   porta, pero que **este módulo no se ha ejercitado aún en hardware** [verificado: ref:NOTICES.md]. Corrige
   lo dicho en §1 y §4: es la mejor base, no una coreografía probada tal cual.
2. Las tramas que la caja envía sin petición (avisos de inserción y fallos por `0x0A`) se pierden:
   `serial_485` descarta lo que no responde a una petición pendiente [verificado: fork:serial_485.py:565-570].
   El estado se sigue viendo al consultar. Pendiente: gancho en `serial_485` para tramas no pedidas.
3. `CFS_FLUSH` extruye donde esté la boquilla; no va a la papelera (X=-18,5)
   [verificado: fork:creality_cfs.py, `cmd_CFS_FLUSH`: solo `M83`, `G1 E` y `G91`/`G90`]. Hecho en `cfs.cfg`: `CFS_PURGE`
   va antes a la papelera y `_HI_CFS_SHAKE` hace la pasada corta tras cada ciclo, enganchada por
   `nozzle_clean_macro` [verificado: test `test_purge_runs_the_flush_over_the_waste_bin`]. El orden de la pasada
   corta (X 0, -5, 0, -18,5) es [supuesto: verlo en la Hi, paso 5.5]. No reproduce el rodeo por Y=261 de stock
   (`detour_pos_y`): no usar `CFS_PURGE` con una pieza en la cama todavía.
4. `cut_velocity: 3000` es el valor del ejemplo de la referencia; el stock usa 15000
   [verificado: captura:box.cfg, `cut_velocity`]. Se mantiene el lento hasta el paso 5.4.
5. Comandos `T0`..`T3` y los `BOX_*` de stock que llaman las macros y el laminador: sin hacer (fase 6).
6. Proponer el cambio al autor desde un fork de su repositorio (tarea del usuario, B34b).

## 6. Decisiones que necesito

1. **Cómo adaptar el CFS** (§4): cerrada el 2026-11-10, opción D (D16).
2. **Purga en la Hi**: cerrada el 2026-11-10. Como stock, en la papelera de X=-18,5 con la pasada corta
   (`CFS_PURGE`), pero **sin ir al teflón trasero en un cambio de filamento**: el teflón está a la altura de la
   cama y habría que bajar el pórtico, que durante una impresión está por encima de la pieza [usuario,
   2026-11-10]. El teflón queda solo para la limpieza previa a la impresión (`NOZZLE_CLEAN`).
3. **Rack externo (`filament_rack`)**: dejarlo fuera de la primera versión (recomendada) o incluirlo.

## 7. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | Corte en el sentido equivocado o más allá del tope: golpe contra el lateral | Paso 5.4 con margen y baja aceleración; test en batch de los límites |
| R2 | El pin del sensor de corte de la K2 es un ventilador en la Hi | No cargar `box.py` sin la opción de pin; test que lo impide |
| R3 | App del CFS más antigua: respuestas distintas | Decodificador estricto; paso 5.2 antes de cualquier orden |
| R4 | Tramas del CFS y de los drivers mezcladas en el bus | Paso 5.3; `startup_writes: none` en los drivers durante las pruebas del CFS |
| R5 | Purga sobre la cama si la geometría de la K2 queda activa | Validación de coordenadas contra los límites de la Hi en la config |
