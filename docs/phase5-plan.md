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

No tengo recomendación firme hasta leer la lógica (B32 y B31b): depende de cuánto de `box.py` es geometría de la K2.
Con lo visto, **D** es la candidata: es la única coreografía probada en una Hi. La alternativa es A para el
pin y el sentido del corte. La decisión depende de cuánto cuesta cambiar el transporte de D.

## 5. Plan en la impresora

| Paso | Qué | Escribe o mueve |
| - | - | - |
| 5.1 | Con stock: leer `nozzle_mcu:PB1` con la cuchilla suelta y empujada a mano; anotar la posición X real del corte | No |
| 5.2 | Con Kalico y `[box]` sin cargar: lecturas del CFS con `box_protocol` (estado, RFID, longitud restante, versión) desde una herramienta de solo lectura | No [supuesto: confirmar en B31 qué tramas son de solo lectura] |
| 5.3 | Auto-dirección del CFS (A0/A1/A2/0B) y convivencia con los drivers en el mismo bus | Asigna direcciones volátiles [supuesto: comprobar en B31 que no se guarda nada en el CFS] |
| 5.4 | Corte sin filamento, a baja aceleración, con `cut_pos_x` 2 mm antes del valor medido | Mueve X |
| 5.5 | Carga y descarga de una ranura, sin imprimir | Mueve, calienta, extruye |
| 5.6 | Cambio de color con purga | Todo |

## 6. Decisiones que necesito

1. **Cómo adaptar el CFS** (§4): A, B, C o D. Se decide después de B32 y B31b.
2. **Purga en la Hi**: repetir la de stock (purga en la papelera de X=-18,5 y limpieza en el teflón trasero) o usar solo torre de purga.
   Recomendada: la de stock, con sus valores.
3. **Rack externo (`filament_rack`)**: dejarlo fuera de la primera versión (recomendada) o incluirlo.

## 7. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | Corte en el sentido equivocado o más allá del tope: golpe contra el lateral | Paso 5.4 con margen y baja aceleración; test en batch de los límites |
| R2 | El pin del sensor de corte de la K2 es un ventilador en la Hi | No cargar `box.py` sin la opción de pin; test que lo impide |
| R3 | App del CFS más antigua: respuestas distintas | Decodificador estricto; paso 5.2 antes de cualquier orden |
| R4 | Tramas del CFS y de los drivers mezcladas en el bus | Paso 5.3; `startup_writes: none` en los drivers durante las pruebas del CFS |
| R5 | Purga sobre la cama si la geometría de la K2 queda activa | Validación de coordenadas contra los límites de la Hi en la config |
