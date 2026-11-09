# Hoja de ruta

Objetivo: sustituir el Klipper antiguo de Creality por **Kalico** con módulos abiertos, portando el CFW de la
K2 Plus ([Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware)) y
conservando el sistema Tina de stock de la Hi (el kernel de la K2 no tiene la pantalla ni `uart4` de la Hi).

Las MCU **no se reflashean**. Cada fase se prueba en la partición A/B libre: si falla, se vuelve a stock.

## Fase 0 — Investigación (hecha)

- [x] Diferencias entre versiones de la Hi ([analysis/firmware-versions.md](analysis/firmware-versions.md)).
- [x] Viabilidad del port desde la K2 ([analysis/k2-port-feasibility.md](analysis/k2-port-feasibility.md)).
- [x] Diccionarios de las tres MCU (la de la cama, leída en la impresora).
- [x] Ids de parámetros de los motores X/Y verificados en la impresora (51/51 por eje).

## Fase 1 — Kalico arrancando en la Hi

- [x] Base del host: Kalico de Jacob10383 ([decisions.md](decisions.md), D1).
- [x] El código vive en un fork propio del Kalico de Jacob10383 ([decisions.md](decisions.md), D2). Licencia:
      GPLv3.
- [x] Dos repos: este para investigación, docs, herramientas e instalador; el fork para el código (D3).
- [ ] Inicializar este repo y crear el fork (nombre, ubicación local, ¿submódulo aquí?).
- [ ] Compilar `c_helper.so` de Kalico para ARMv7 hard-float, glibc 2.29 (la Hi no tiene gcc).
- [ ] Revisar dependencias Python frente a las de la Hi (cffi 1.14.6, greenlet 1.0.0, numpy 1.20.1,
      Jinja2 3.0.3); empaquetar ruedas si hace falta.
- [ ] Instalación en la partición libre y forma de volver a stock (`fw_setenv root_partition` / `boot_partition`).
- [ ] Config mínima: tres MCU, steppers Z/Z1/E, temperaturas, ventiladores. Sin motores X/Y, CFS ni sonda.

## Fase 2 — Motores X/Y de lazo cerrado

Portar `motor_control.py` de la K2:

- [ ] Pines de stall: `STALL_PIN_LAYOUT` fijo (`PB12/PB11`) → `PA8/PA6`, o leerlos de la config.
- [ ] Direcciones: mantener las de stock (X=0x81, Y=0x82) en `PIN_DIR_SEQUENCE`.
- [ ] Quitar los ejes E, Z y Z1 del descubrimiento y del arranque.
- [ ] Homing por stall: el `homing.py` de Kalico de Jacob llama a `set_homing_stall_mode`.
- [ ] Primeras pruebas sin overrides de parámetros. Nunca `MOTOR_FLASH_PARAM ... COMMIT=1` ni `MOTOR_CALIBRATE`.

## Fase 3 — Sonda

- [ ] Portar `prtouch.py` de la K2: cinemática cartesiana con z + z1 (la K2 es corexy).
- [ ] Verificar marcadores de ack y formato de trama en la impresora, con la boquilla lejos de la cama.
- [ ] `register_as_probe: True` (la K2 usa Cartographer).

## Fase 4 — Módulos legibles de la Hi

- [ ] `z_align.py` (el de la K2 no es compatible), `io_remap.py`, `bl24c16f.py`, `nozzle_clear.py`,
      `tmc_line_check.py`, `timer_read.py`.

## Fase 5 — CFS

- [ ] Prueba de solo lectura con `box_protocol.py` (A2, 0x0A, 0x05, 0x08, 0x0E).
- [ ] Corte: la cuchilla de la Hi está en +X (la K2 corta en -X).
- [ ] Purga y limpieza: la Hi no tiene papelera trasera; el pin del sensor de corte de la K2
      (`nozzle_mcu:PB9`) es un ventilador en la Hi.
- [ ] Rack externo (`filament_rack`).

## Fase 6 — Macros y experiencia de uso

- [ ] Sustituir comandos del Klipper parcheado de Creality: `SET_LIMITS`, `FORCE_MOVE_E`, `CXSAVE_CONFIG`,
      `Tnn`, `BOX_*`.
- [ ] Integrar la config del usuario (`ale87jan/Creality-Hi-Custom-Klipper`).
- [ ] Pantalla: Fluidd al principio; valorar HelixScreen (LVGL) para el panel 240x320.
- [ ] Instalador y actualizaciones en este repo, al estilo de `install.py`/`bootstrap`/`swap` de la K2: el
      instalador clona el fork en la impresora y verifica cada pieza con SHA-256.
- [ ] Web de documentación (MkDocs + GitHub Pages), como la de la K2.
