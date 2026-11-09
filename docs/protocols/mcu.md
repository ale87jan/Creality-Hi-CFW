# Protocolo de las MCU de Klipper

Las tres MCU de la Hi llevan Klipper de Creality (2024-2025) con el protocolo estándar: mensajes con VLQ,
CRC-16 CCITT, sincronización `0x7E` y diccionario de datos comprimido con zlib. Kalico (host moderno) habla con
ellas sin reflashear, como hace el CFW de la K2. Los diccionarios completos están en
`data/derived/mcu-dictionaries/`.

## Resumen

| MCU | Chip | Versión | Comandos / respuestas |
| - | - | - | - |
| Hi principal | `gd32f303xe` 120 MHz | `cf1eac2d-dirty` 2025-02-10 | 80 / 33 |
| Hi boquilla | `gd32f303xb` 120 MHz | `92bf775a` | 76 / 33 |
| Hi cama | `gd32e230x8` 72 MHz | `54872883-dirty` 2024-06-05 (leído en la impresora) | 63 / 27 |
| K2 Plus principal (`F008 mcu0_022`) | `gd32f303xe` 120 MHz | `1.1.0.48-293-g493f9a0f` 2024-12-20 | 75 / 32 |
| K2 Plus boquilla (`F008 noz0_021`) | `gd32f303xb` 120 MHz | igual | 75 / 32 |

## Comandos propios de Creality

| Familia | Comandos | Hi principal | Hi boquilla | Hi cama | K2 Plus |
| - | - | - | - | - | - |
| Ventiladores | `config_fancheck`, `query_fancheck` → `fan_status` | sí | sí | sí | sí |
| Remapeo de pines | `config_ioRemap`, `operation_ioRemap` → `query_ioRemap` | sí | sí | sí | **no** |
| Alineación Z | `config_z_align`, `config_z_align_add`, `query_z_align` → `z_align_status` | sí | sí | sí | sí (firma distinta) |
| Alineación Z extra | `config_z_align_up`, `config_z_align_up_add`, `query_z_align_up`, `query_z_align2` | sí | no | no | no |
| Parada Z | `z_align_force_stop` | no | no | no | sí |
| Sonda (prtouch) | `config_/start_/stop_/read_prtouch_step`, `cont_prtouch_step`, `config_/start_/stop_/read_prtouch_pres`, `config_/start_/stop_prtouch_apax`, `ack_prtouch`, `resault_prtouch_*` | sí | sí | no | sí (mismas firmas) |
| GPIO | `query_gpio_status` → `gpio_status` | sí | sí | no | sí |
| Ajuste fino | `query_finetuning` → `finetuning_status` | no | no | no | sí |
| Túnel serie | `config_transparent`, `transparent_send` → `transparent_response` | no | no | no | sí |

## Diferencias que afectan al port

- `query_z_align`: en la K2 lleva un argumento más (`safeDist=%u`). El `z_align.py` del CFW de la K2 no conecta
  con la Hi; hay que usar el `z_align.py` de la Hi.
- El túnel `transparent` de la K2 sirve para el motor E de lazo cerrado vía la MCU de la boquilla. La Hi no lo
  tiene ni lo necesita (su extrusor usa TMC2208).
- La sonda de la K2 (`prtouch.py`) usa 8 comandos que existen con la misma firma en la boquilla de la Hi.
- Sin `config_pwm_out`/`queue_pwm_out`: PWM solo por software (`digital_out`). Sin I2C en las MCU.
- SPI por software con la firma antigua `spi_set_software_bus ... rate`; Kalico tiene fallback.
- `STEPPER_BOTH_EDGE=1` sin `STEPPER_OPTIMIZED_UNSTEP`: Kalico lo trata como MCU antigua y funciona.
- No hay clave `app` en el diccionario: Kalico no avisa de reflashear.

## Compatibilidad con Kalico

Un análisis estático de las 98 cadenas de comando que pide Kalico (`lookup_command`, `try_lookup_command`…)
encontró 43 presentes con la misma firma en las MCU principal y de boquilla. Las 55 restantes son de sensores
y buses que la Hi no usa (ldc1612, load_cell, hx71x, i2c, canbus, pca9685…) o tienen fallback. El diccionario
de la cama, leído después, tiene el mismo núcleo estándar.
