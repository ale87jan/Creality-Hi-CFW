# Viabilidad: portar el CFW de la K2 Plus a la Creality Hi

Análisis del 2026-11-09: estático, más pruebas de solo lectura en la impresora (sección siguiente).

Comparado: [Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware) y su fork
[Jacob10383/kalico](https://github.com/Jacob10383/kalico) (commit `089cf65`, 2026-11-06), frente al firmware
V1.1.0.60 de la Hi y la config de `Creality-Hi-Custom-Klipper` (rama `dev-cfw`).

## Conclusión

Viable si se hace como **Kalico sobre el Linux de stock de la Hi**, reutilizando los módulos abiertos de la K2 y
los módulos Python legibles de la Hi. **No** es viable copiar tal cual el kernel/rootfs de la K2.

Estimación: **80–85 %** de llegar a una Hi que imprima con Kalico, motores X/Y, sonda y CFS básico (era 70–80 %
antes de las pruebas en la impresora).

## Pruebas en la impresora (2026-11-09, `tools/hi_probe.py`, solo lectura)

Ejecutado en la Hi con V1.1.0.60 y Klipper de stock parado. Resultados en
`data/captures/2026-11-09_hi-v1.1.0.60/` (`bed_mcu.json` y `motors.json`).

**Motores X/Y: identificadores de parámetro confirmados.**

| Dirección | Motor | R / L / Ke leídos | Coincidencia con `motor_control.cfg` |
| - | - | - | - |
| 0x81 | X de la Hi (pines PB9/PB10) | 0.6 / 0.001 / 0.1018592 | 51 de 51 |
| 0x82 | Y de la Hi (pines PB7/PB8) | 0.78 / 0.0014 / 0.098676 | 51 de 51 |

- Los 77 parámetros del mapa de la K2 (`mot2_002_081`) se leen sin errores en el firmware `071`, con el mismo
  tipo de dato. El id 227 (`prt_continuous_clear_time_s`) también existe en 071 (vale 0.5).
- `param_flash_param_version`: 583 en la Hi frente a 587 en el mapa de la K2.
- Los parámetros de solo lectura coinciden con la K2, salvo los derivados del motor (`leso_param_b0`, `phi_e`).
- La única clave de la config de la Hi que no está en el mapa es `x_cmd_int_param_char_cmd_support`.
- Direcciones: en stock, X = 0x81 e Y = 0x82. El código de la K2 asigna x = 0x82 e y = 0x81. Funcionaría igual
  porque reasigna las direcciones en cada arranque, pero conviene parchearlo para mantener las de stock.

**Bed MCU (`ttyS4`).** `gd32e230x8` a 72 MHz, Klipper `54872883-dirty` (2024-06-05), 63 comandos y 27
respuestas. Núcleo estándar completo, más `fancheck`, `ioRemap`, `z_align` (sin `safeDist`), `lis2dw` con
`sensor_bulk`, `neopixel`, `thermocouple` y `tmcuart`. Compatible con Kalico igual que las otras dos MCU.

Con esto quedan resueltas las dos incógnitas principales. Estimación revisada: **80–85 %**.

## Hardware común

| Pieza | K2 Plus | Hi | Estado |
| - | - | - | - |
| SoC | Allwinner T113-S | Allwinner T113 (`t113_i`) | Igual |
| UART2/3/5 | PC0/1, PB6/7, PB4/5 | Igual | Misma placa base |
| MCU principal | Firmware stock, no se reflashea | `gd32f303xe`, 120 MHz, Klipper 2022 (`cf1eac2d`) | Compatible |
| MCU boquilla | Firmware stock | `gd32f303xb`, Klipper `92bf775a` | Compatible |
| Bus RS-485 | `/dev/ttyS5`, 230400, `F7…crc8(0x07)` | Igual | Igual |
| Motores lazo cerrado | X, Y, Z, Z1, E (`mot2_002_081`) | Solo X, Y (`mot2_002_071`) | Misma familia |
| Sonda | CS1237 en boquilla, pines `!PC7`, `PA15`, `PB13/PB14` | Igual (`prtouch_v3`) | Igual |
| CFS | Misma trama, auto-dirección A0/A1/A2/0B | Igual, app `cfs0_000_113` | Muy probablemente la misma unidad |

## Por componente

| Componente | Qué reutilizar | Esfuerzo | Notas |
| - | - | - | - |
| Núcleo Kalico ↔ MCU | Kalico sin cambios | Bajo | 43 comandos usados por el núcleo coinciden. PWM solo por software |
| `lis2dw`, `duplicate_pin_override` | Kalico | Bajo | Drop-in |
| `io_remap`, `bl24c16f`, `tmc_line_check`, `timer_read` | Python de la Hi (GPL) | Bajo | Portables tal cual |
| `z_align` | Python de la Hi | Bajo | El de la K2 pide `safeDist` y `z_align_force_stop`, que la MCU de la Hi no tiene |
| `serial_485`, auto-dirección CFS | K2 | Bajo | Trama idéntica. pyserial ya está en la Hi |
| Sonda (`prtouch`) | K2 `prtouch.py` | Medio | 8 de 8 comandos con la misma firma. Falta verificar acks, formato de trama y Z cartesiano (z+z1). Riesgo de choque con la cama |
| Motores X/Y (`motor_control`) | K2 `motor_control.py` | Medio | Ids de parámetro verificados en la impresora (51/51 por eje). Hay que parchear los pines de stall (fijos `PB12/PB11`, la Hi usa `PA8/PA6`), las direcciones, quitar el eje E y adaptar el homing |
| Protocolo CFS | K2 `box_protocol.py` | Medio | Sin chequeo de versión; decodificador estricto (falla de forma segura). Probar en solo lectura |
| Cambio de color, corte, purga | K2 `box.py`, `box_change.py` | Alto | La Hi corta en +X (la K2 en -X), no tiene papelera trasera, y el pin del sensor de corte de la K2 (`nozzle_mcu:PB9`) es un ventilador en la Hi |
| Rack externo | K2 `external_rfid_reader.py` | Medio | Dirección y pin de la Hi por descubrir |
| `nozzle_clear` | Python de la Hi | Medio | Atado a la sonda |
| Parches del núcleo Creality | — | Medio | `SET_LIMITS`, `FORCE_MOVE_E`, `CXSAVE_CONFIG`, `Tnn`… hay que reimplementar o quitar de las macros |
| `bed_mcu` (`ttyS4`) | Sección `[mcu]` estándar | Bajo | `gd32e230x8`; diccionario leído en la impresora, compatible con Kalico |
| Kernel/rootfs de la K2 | No | Alto | Linux 6.18 mainline. Su DTB no tiene `uart4` (bed_mcu), LCD, táctil ni WiFi AIC8800 de la Hi |
| Kalico en Tina (Python 3.9) | — | Medio | Sintaxis compatible. Hay que compilar `c_helper.so` de forma cruzada (no hay gcc). Librerías más antiguas que las que fija Kalico |
| Pantalla | HelixScreen | Medio | Pendiente. Al principio, Fluidd |

## Riesgos

1. **Parámetros de motor con `value_id` desplazado.** El código de la K2 escribe en RAM los parámetros del cfg
   que difieren, sin comprobar la versión. Con ids distintos escribiría otro parámetro. Empezar sin overrides.
2. **No usar** `MOTOR_FLASH_PARAM ... COMMIT=1` ni `MOTOR_CALIBRATE` hasta verificar ids: graban en el driver.
3. **Sonda:** probar con la boquilla lejos de la cama.
4. **Dos procesos en `/dev/ttyS5`:** el Klipper de stock y Kalico no pueden usar el bus a la vez.

## Plan de pruebas (de menos a más riesgo)

1. En la impresora, con Klipper de stock parado: leer el diccionario del `bed_mcu` y comprobar las direcciones
   0x81/0x82 con un script propio que solo lee (`READ_ADDR`, `GET`).
2. Leer `motor_param_R/L/Ke` (ids 41–43) y otros ids en cada motor y comparar con `motor_control.cfg`. Si
   coinciden, los ids de 071 son los de 081.
3. Leer el estado del CFS (A2, 0x0A, 0x05, 0x08, 0x0E) con `box_protocol.py`.
4. Kalico en la partición libre (A/B) con config mínima: MCU, steppers, temperaturas. Sin CFS ni sonda.
5. Añadir motores X/Y sin overrides, después la sonda y por último el CFS.

## Comparación con el firmware de stock de la K2 (V1.1.8.3, 2026-10-28)

Imagen `CR0CN200400C10_R_202610280949_ota_img_V1.1.8.3.img` frente a la Hi V1.1.0.74.

**Mismo sistema.** Tina 5.0 / OpenWrt 21.02, `t113_i`, kernel 5.4.61 con el mismo compilador, U-Boot 2018.07,
glibc 2.29, Python 3.9.12, Moonraker `dde9bcc` y Fluidd 1.30.0. Mismo `sw-description` (A/B por
`/dev/by-name/`, sin comprobación de modelo) y mismos servicios en `/etc/init.d`. 9155 de 10663 ficheros de la
K2 son idénticos en la Hi.

| Pieza | K2 stock | Hi | Implicación |
| - | - | - | - |
| Kernel | Panel ST7701 MIPI-DSI 480x800, Ethernet, RTL8189FS | Panel GC9307 SPI 240x320, sin Ethernet, solo AIC8800 | Los kernels no son intercambiables; los UART son iguales |
| Klipper de Creality | `c5df4f4` (mismo fork) | `b3d1923` | Los `.py` de la K2 sirven de referencia; `toolhead`, `z_align`, `homing`, `bed_mesh` difieren mucho |
| `serial_485_wrapper`, `prtouch_v2_wrapper` | — | — | Idénticos byte a byte |
| `motor_control_wrapper` | Añade UUID, telemetría, corte en 2 ejes | Versión propia | No intercambiable |
| MCU principal / boquilla | `gd32f303xe` / `gd32f303xb` (K2 Plus) | Igual | Mismo chip; cada uno tiene comandos propios |
| Comandos solo K2 | `transparent_*` (túnel), `finetuning`, `z_align ... safeDist` | — | El túnel solo hace falta para el motor E de lazo cerrado, que la Hi no tiene |
| Comandos solo Hi | — | `ioRemap`, `neopixel`, `z_align_up`, `query_z_align2` | Usar los módulos de la Hi |
| Firmware de motor | `mot2_002_081` (RISC-V) | `mot2_002_071` (RISC-V) | Mismos nombres de parámetros en el binario |
| Config de motor de la K2 | Cabecera `FW: mot2_..._071` (8 cfg) y `_072` (1), con la K2 llevando ya 081 | — | Creality usa la misma config para 071 y 081; confirmado después en la impresora (ids estables) |
| CFS | Boot `cfs0_050_G30/G32`, app 150 / 153 | Mismo boot, app 113 (.60) / 142 (.74) | Mismo hardware; la K2 lleva una app más nueva |
| Bed MCU | Solo el de la K1 (`gd32e230x8`) | Sin binario en la OTA | Sigue pendiente leerlo en la impresora |

Modelos en la OTA de la K2: F008 = K2 Plus, F012 = K2 Pro, F021 = K2, F025 = M300.

Consecuencia: la vía "Kalico sobre el Linux de stock de la Hi" queda reforzada. La K2 de stock corre el mismo
sistema, y el CFW de Jacob10383 solo cambia kernel y rootfs por decisión propia, no porque haga falta.

## Hallazgos detallados

- Diccionarios de MCU extraídos: `mcu0_020_000` (80 comandos) y `noz0_019_000` (76). Comandos Creality propios:
  `fancheck`, `ioRemap`, `z_align` (+ `z_align_up`/`query_z_align2` solo en la principal), `prtouch_step/pres/apax`,
  `query_gpio_status`.
- Direcciones de motor: la K2 las fija por los pines dir/step (`0x81 + DIR + 2·STEP`). En la Hi, X (PB9/PB10) e Y
  (PB7/PB8) quedarían en 0x82 y 0x81. Hay que confirmarlo con `READ_ADDR`.
- Valores de motor: el Y de la Hi tiene los mismos R/L/Ke que los X/Y de la K2. El X de la Hi es otro motor
  (R=0.6, Ke=0.1019). Varios PID y protecciones difieren: usar siempre los valores de la Hi.
- Licencias: el código de la K2 y Kalico son GPLv3.
