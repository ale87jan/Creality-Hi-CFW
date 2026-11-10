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
- [x] Repos creados (2026-11-09), públicos y GPLv3:
      [Creality-Hi-CFW](https://github.com/ale87jan/Creality-Hi-CFW) y
      [Creality-Hi-Kalico](https://github.com/ale87jan/Creality-Hi-Kalico) (fork de Jacob10383/kalico;
      `main` refleja el upstream, el trabajo va en `dev`). Sin submódulo por ahora.
- [x] Compilar `c_helper.so` de Kalico para ARMv7 hard-float, glibc 2.29 (la Hi no tiene gcc):
      `scripts/build_chelper.sh`. Falta probar la carga en la impresora ([phase1-plan.md](phase1-plan.md) §4).
- [x] Revisar dependencias Python frente a las de la Hi (cffi 1.14.6, greenlet 1.0.0, numpy 1.20.1,
      Jinja2 3.0.3): Kalico funciona con ellas en PC; no hacen falta ruedas ([phase1-plan.md](phase1-plan.md) §2).
- [ ] Instalación y forma de volver a stock. Scripts de sesión hechos y probados en simulación
      (`scripts/hi_install.sh`, `hi_kalico.sh`, `hi_restore.sh`); sin probar en la impresora. El slot A/B libre se
      aplaza: el overlay es común a los dos slots ([phase1-plan.md](phase1-plan.md) §5 y §9).
- [ ] Config mínima: tres MCU, steppers Z/Z1/E, temperaturas, ventiladores. Sin motores X/Y, CFS ni sonda.
      Escrita y validada en modo batch (`config/hi/printer.cfg` del fork); sin probar en la impresora.

Plan, análisis y pruebas pendientes: [phase1-plan.md](phase1-plan.md). Estado: [ESTADO.md](ESTADO.md). Tareas:
[backlog.md](backlog.md).
      Base: config actual de la impresora en `data/captures/2026-11-09_hi-v1.1.0.60/printer-config/`.

## Fase 2 — Motores X/Y de lazo cerrado

Plan y análisis: [phase2-plan.md](phase2-plan.md). Portar `motor_control.py` de la K2:

- [ ] Pines de stall: `STALL_PIN_LAYOUT` fijo (`PB12/PB11`) → `PA8/PA6`, o leerlos de la config.
- [ ] Direcciones: mantener las de stock (X=0x81, Y=0x82) en `PIN_DIR_SEQUENCE`.
- [ ] Quitar los ejes E, Z y Z1 del descubrimiento y del arranque.
- [ ] Homing por stall: el `homing.py` de Kalico de Jacob llama a `set_homing_stall_mode`.
      Revisado: la Hi usa `endstop_pin` `!PC7` y `^PB13`, no los pines de stall, y necesita `io_remap.py`
      ([phase2-plan.md](phase2-plan.md) §4).
- [ ] Primeras pruebas sin overrides de parámetros. Nunca `MOTOR_FLASH_PARAM ... COMMIT=1` ni `MOTOR_CALIBRATE`.

## Fase 3 — Sonda

Plan y análisis: [phase3-plan.md](phase3-plan.md).

- [ ] Portar `prtouch.py` de la K2: cinemática cartesiana con z + z1 (la K2 es corexy).
- [ ] Verificar marcadores de ack y formato de trama en la impresora, con la boquilla lejos de la cama.
- [ ] `register_as_probe: True` (la K2 usa Cartographer).

## Fase 4 — Módulos legibles de la Hi

Plan y análisis: [phase4-plan.md](phase4-plan.md).

- [x] `io_remap.py` (hecho en la fase 2).
- [ ] `z_align.py` (el de la K2 no es compatible; el de la Hi depende de parches de Creality).
- [ ] `nozzle_clear.py` (reescritura sobre el `prtouch.py` del fork).
- [ ] `bl24c16f.py` y `tmc_line_check.py`: sin fecha. `timer_read.py`: no se porta (propuesta).

## Fase 5 — CFS

Plan y análisis: [phase5-plan.md](phase5-plan.md).

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
