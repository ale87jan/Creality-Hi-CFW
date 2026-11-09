# Diferencias entre firmwares OTA Creality Hi (CR4NU200360C20)

Versiones analizadas: V1.1.0.50, V1.1.0.60 (instalada), V1.1.0.65, V1.1.0.73 y V1.1.0.74. Análisis del 2026-11-09.

Formato: paquete SWUpdate (CPIO newc) con `sw-description`, `uboot`, `kernel` y `rootfs` (SquashFS, zlib).
Base: OpenWrt 21.02 / Tina 5.0, `arm_cortex-a7_neon`.

## Resumen

| Salto | Ficheros cambiados | Qué importa |
| - | - | - |
| .50 → .60 | 383 | Casi todo recompilación. Klipper sin cambios funcionales. Config: `fanp0` y macro `SET_PIN` |
| .60 → .65 | 462 | El salto grande: errores pasan a avisos, PAUSE en vez de cancelar, módulo `[steer]`, cambios del CFS, `track_max_err` 0.3 |
| .65 → .73 | 25 | Firmware CFS 113 → 142, chequeo RFID "scrap", subida de logs activada |
| .73 → .74 | 10 | Recompilación: U-Boot, binarios Creality y `lvgl_klipper`. Klipper y config sin cambios |

## Componentes por versión

| Componente | .50 | .60 | .65 | .73 |
| - | - | - | - | - |
| Fecha de build | 2025-08-06 | 2025-11-26 | 2026-01-23 | 2026-06-23 |
| Kernel (md5) | ed382f1c | ecd3334d | 748c9987 | = .65 |
| U-Boot (md5) | edf52f00 | e3548005 | a2459957 | 03ae912a |
| klipper (git) | ec5fa7da9 | 69e79e4 | a1a394b | b3d1923 |
| lvgl_klipper | 0a877abc | d15240d | e830bcc | 030e617 |
| libhv | v1.3.0 | v1.3.0 | v1.3.3 | v1.3.3 |
| libcxcloud | 5568d74d | 5568d74d | 33924bb | 33924bb |
| minizip | — | — | 4.0.10-2 (nuevo) | 4.0.10-2 |
| Firmware CFS (app) | cfs0_000_113 | 113 | 113 | **142** |
| Firmware CCL | — | — | ccl0_000_001 (nuevo) | igual |
| Moonraker | dde9bcc | igual | igual | igual |
| Fluidd | 1.30.0 (paquete; `.version` dice v1.27.0) | igual | igual | igual |

Los binarios propietarios (`app-server`, `display-server`, `master-server`, `web-server`, `log_main`) cambian en
cada salto.

## .50 → .60

- Klipper: ningún `.py` ni `.so` de `extras` cambia. Solo `.o` de chelper recompilados.
- `printer.cfg`: `[output_pin fanp0]` pasa de `!nozzle_mcu:PB6` a `nozzle_mcu:PB6` con `value: 0`.
- `gcode_macro.cfg`: macro nueva `SET_PIN` (`rename_existing: SET_PIN_BASE`) que conmuta `fanp0` con `PIN=fan0`.
- Sistema: 4 módulos de kernel (WiFi aic8800, táctiles gt9xx/tlsc6x) y librerías recompiladas.

## .60 → .65

### Klipper

- **Errores → avisos**: nuevas `CommandWarning` y `ModuleCommandError`. Los avisos salen con prefijo `##` y no
  abortan la macro. Afecta a parámetros fuera de rango (`get_int`/`get_float`), macros recursivas, `Z_TILT_ADJUST`
  con error creciente, fallo al abrir fichero y `RESUME` sin pausa. Si el texto contiene `!` sigue siendo error.
- **Extrusión en frío** y **movimiento fuera de rango** durante la impresión: hacen `PAUSE` en vez de cancelar.
- **Vigilancia ADC**: timer de 3 s en `mcu` y `nozzle_mcu`; lecturas <0 o >500 ejecutan `TURN_OFF_HEATERS`.
- `reactor.py`: excepciones en timers se registran en log en vez de tumbar Klipper.
- `CXSAVE_CONFIG` hace `firmware_restart` (reinicia también los MCU).
- Se eliminan los envíos de errores a la nube desde `gcode.py`, `pause_resume.py` y `virtual_sdcard.py`.
- **Módulo nuevo `steer`** (`steer.py`, `steer_wrapper`): cliente RS-485 sobre el bus del CFS (dir. 0x41) para
  un módulo de cámara. Comandos `STEER_*`. Lo usa el timelapse.
- **CFS (`box_wrapper.so`)**: comandos nuevos `BOX_ENABLE_HEART_PROCESS`, `BOX_DISABLE_HEART_PROCESS`,
  `BOX_GET_GCODE_USED_TNN`. La velocidad de purga se escala con el diámetro de boquilla. Al reanudar sin filamento
  en el extrusor se repite el último `Tn`.
- `motor_control_wrapper.so`: error nuevo `key856 "no cutter"` y comprobación de `pre_cut_pos`.
- `metadata.py`: lee `filament_used_g`, `default_filament_colour` y `default_filament_type`.
- `nozzle_clear.py`: utilidades de fábrica `NOZ_CLEAR_TEST` y `BOX_TEST_COUNT`. No usar en uso normal.
- Aparecen los fuentes C de chelper (`filament_change.c`: matriz de purga por color en HSV; `msgblock_485.c`:
  trama RS-485 con CRC-8 0x07).

### Config de stock F018

- `printer.cfg`: se añade `[steer]` al final.
- `motor_control.cfg`: `x_/y_protection_param_prt_track_max_err` pasa de 0.1 a 0.3.
- `gcode_macro.cfg`: se comentan los `RESPONSE_INFO` de `SET_PIN` y `M106` (sin cambio funcional).

### Sistema

- `error_code_map.json`: añade fault_code 2571 → error 12.
- Certificados nuevos en `etc/sysConfig/defData/cert` y `usr/share/cert` (CA privada; `server.crt` caducó el
  2026-08-29; la clave privada va dentro del firmware).
- `alchemistp/config.json` (cliente de nube/logs): se reorganiza y se quitan URLs de servidores de prueba.
- Nuevos: `libhvnew.so`, `kongda_detect`, `pa_compute`, `strain_gauge_collect_data`.

## .65 → .73

- **Firmware CFS 113 → 142** (G30 y G32). Se flashea en el CFS al actualizar.
- `box_wrapper.so`: chequeo de ranuras RFID "scrap" en precarga (error `key890 "rfid slot"`) y lectura de longitud
  restante de filamento en el latido.
- `serialhdl.py`: un fallo de `bed_mcu` emite `key345`.
- Script nuevo `usr/share/klipper/klipper_auto_deploy.sh` (de desarrollo: sube un `.py` por scp, renombra el `.so`
  a `.sobak` y reinicia Klipper; lleva las credenciales root por defecto).
- `alchemistp/config.json`: **`UploadFileFlag` pasa a `"1"`**: sube `klippy.log`, `master-server.log`,
  `display-server.log` y `messages` a Creality.
- Config de stock F018: idéntica a .65.

## .73 → .74

- Fecha de build 2026-07-24. Kernel idéntico a .65/.73; U-Boot cambia.
- `lvgl_klipper` 030e617 → 40ffe78; `display-server` cambia (12 bytes menos); `app-server` y `master-server`
  recompilados con el mismo tamaño.
- Klipper: mismo commit (`b3d1923`), ningún `.py` ni `.so` cambia; solo los `.o` de chelper recompilados.
- Firmware CFS 142, config de stock y `alchemistp/config.json` (subida de logs activada) iguales que en .73.

## Impacto en la config del usuario (`Creality-Hi-Custom-Klipper`)

`config/F018_CR4NU200360C20/original/` coincide con la stock de **V1.1.0.60**.

Si se actualiza a .65, .73 o .74 (la .74 se comporta como la .73):

1. Portar `track_max_err: 0.3` en `motor_control.cfg` (líneas 103 y 181). Hoy está en 0.1.
2. Añadir `[steer]` en `printer.cfg` (junto a `[timer_read]`). **No añadir con .60**: el módulo no existe y Klipper
   no arranca.
3. Revisar macros que dependan de que un error aborte el script (ahora es aviso `##`).
4. Macros CFS que fuercen RFID en precarga pueden recibir `key890` con .73.
5. No añadir `[output_pin fanp0]`: PB6 ya es `enable_pin` del `[fan]` en `toolhead.cfg`.
6. Con .73, valorar desactivar la subida de logs (`UploadFileFlag`).
