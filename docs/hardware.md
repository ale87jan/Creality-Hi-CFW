# Hardware de la Creality Hi (F018)

Nivel de confianza: **[P]** verificado en la impresora, **[F]** leído en el firmware o la config de stock,
**[I]** inferido. Ver [RESEARCH.md](../RESEARCH.md).

## Placa base y sistema

| Elemento | Valor | Fuente |
| - | - | - |
| SoC | Allwinner T113-i (`sun8iw20`, Cortex-A7, ARMv7 hard-float) | [F] DTB |
| Sistema | Tina 5.0 / OpenWrt 21.02, kernel 5.4.61 (Linaro GCC 5.3), U-Boot 2018.07 | [F] |
| Userland | glibc 2.29, Python 3.9.12 (con pyserial 3.4, numpy 1.20.1, cffi 1.14.6, greenlet 1.0.0, Jinja2 3.0.3) | [F] |
| Almacenamiento | eMMC `mmcblk0` con GPT; particiones A/B por `/dev/by-name/`: `rootfsA` p6, `rootfsB` p7, `rootfs_data` p10, `UDISK` p11 (el `bootcmd` aún nombra `setargs_nand`) | [P] paso 0 y lectura B40, 2026-11-10 |
| Placa (variante) | `get_sn_mac.sh board` devuelve `CR4NU200360C21` en la unidad del usuario | [P] paso 0, 2026-11-10 |
| Pantalla | GC9307, SPI 9 bit, 240x320 (kernel sin driver ST7701 de la K2) | [F] DTB, kernel config |
| WiFi | AIC8800 (sin Ethernet en el kernel) | [F] |
| Firmware instalado | V1.1.0.60 (`fw_printenv version`, `DISTRIB_INFO=...20251126`) | [P] |

## Puertos serie

| Puerto | UART / pines | Uso | Velocidad |
| - | - | - | - |
| `ttyS0` | uart0 PB0/PB1 | Consola | 115200 |
| `ttyS2` | uart2 PC0/PC1 | MCU principal (`mcu`) | 230400 |
| `ttyS3` | uart3 PB6/PB7 | MCU de la boquilla (`nozzle_mcu`) | 230400 |
| `ttyS4` | uart4 PB2/PB3 | MCU de la cama (`bed_mcu`) | 230400 |
| `ttyS5` | uart5 PB4/PB5 | Bus RS-485: motores X/Y y CFS | 230400 |

Fuente: [F] DTB y config de stock. `ttyS4` y `ttyS5` respondieron en la prueba del 2026-11-09 [P].

## MCU

| MCU | Chip | Reloj | Firmware | Fuente |
| - | - | - | - | - |
| Principal | `gd32f303xe` | 120 MHz | `mcu0_110_G32-mcu0_020_000`, Klipper `cf1eac2d-dirty` (2025-02-10) | [F] |
| Boquilla | `gd32f303xb` | 120 MHz | `noz0_110_G30-noz0_019_000`, Klipper `92bf775a` | [F] |
| Cama | `gd32e230x8` | 72 MHz | Klipper `54872883-dirty` (2024-06-05); no viene en la OTA | [P] |

Las tres hablan el protocolo estándar de Klipper más comandos propios de Creality: ver
[protocols/mcu.md](protocols/mcu.md).

## Motores de lazo cerrado

Solo X e Y son de lazo cerrado. Z, Z1 y el extrusor usan TMC2208 por UART [F].

| Eje | Dirección RS-485 | Pines step / dir | Pin de stall | R / L / Ke | Fuente |
| - | - | - | - | - | - |
| X | 0x81 | PB10 / !PB9 | PA8 | 0.6 Ω / 0.001 H / 0.1018592 | [P] dirección y valores; [F] pines |
| Y | 0x82 | PB8 / PB7 | PA6 | 0.78 Ω / 0.0014 H / 0.098676 | [P] dirección y valores; [F] pines |

- Firmware de los drivers: `mot2_002_071` (RISC-V; `fw/F018/motor/`) [F].
- Los 77 parámetros del mapa de la K2 (`mot2_002_081`) se leen con los mismos ids y tipos [P].
  Detalle en [protocols/rs485.md](protocols/rs485.md).
- El motor Y es el mismo que los X/Y de la K2; el X de la Hi es otro motor [P]/[F].

## Sonda y sensores

| Elemento | Detalle | Fuente |
| - | - | - |
| Sonda de presión (`prtouch_v3`) | CS1237 en la boquilla. `step_swap_pin: !PC7`, `pres_swap_pin: nozzle_mcu:PA15`, `pres_cs0_pin: nozzle_mcu:PB13, nozzle_mcu:PB14` | [F] |
| Cinemática | Cartesiana de cama móvil: la cama se mueve en Y; Z mueve el puente de X con dos husillos (Z y Z1). Sensores ópticos de Z (`PB15`, `PB14`) arriba del todo; `ZDOWN` sube el puente hasta ellos | [usuario]; pines [F] |
| Final de carrera X | Sensor físico [usuario]. `stepper_x` `endstop_pin: !PC7`; llega desde `nozzle_mcu:PB0` reenviado a `nozzle_mcu:PA15` por `[io_remap]`, activo solo durante el homing de X. Línea compartida con la sonda | [F]; cableado [I] |
| Final de carrera Y | Sensor físico [usuario]. `stepper_y` `endstop_pin: ^PB13` en la MCU principal | [F] |
| Pines de stall X / Y | `PA8` / `PA6`: vigilancia de fallos, no se usan como final de carrera | [F] |
| Acelerómetros | `lis2dw` por SPI software en la boquilla y en la cama | [F] |
| EEPROM | `bl24c16f` (24C16) por I2C del host (`[mcu rpi]`, `i2c.1`) | [F] |

## CFS

- Corte de filamento hacia +X (derecha); papelera a la izquierda, fuera de la cama (purga en X=-18,5, Y=130);
  pieza de teflón para limpiar la boquilla detrás, en la posición de `[nozzle_clear]` (Y=266), con una placa
  metálica al lado para sellar la boquilla tras limpiar y que no gotee [usuario].

- Unidad CFS v1 en el bus RS-485, direcciones 0x01-0x04 [F].
- Bootloader `cfs0_050_G30` / `cfs0_050_G32`; app `cfs0_000_113` en V1.1.0.60 y `142` desde V1.1.0.73 [F].
- Mismo hardware que el CFS de la K2 (que lleva app 150/153) [F].
