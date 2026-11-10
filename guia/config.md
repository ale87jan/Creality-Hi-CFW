# Configuración

La config vive en `/mnt/UDISK/kalico-hi/config/` y se conserva entre instalaciones [verificado:
scripts/hi_install.sh:12-16]. Los ficheros salen de `config/hi/` del repo
[Creality-Hi-Kalico](https://github.com/ale87jan/Creality-Hi-Kalico).

## Ficheros por fase

Cada fase incluye la anterior [verificado: config/hi/phase*.cfg, líneas `[include]`].

| Fichero | Añade | Plan |
| - | - | - |
| `printer.cfg` | Fase 1: tres MCU, Z/Z1/E, calentadores, ventiladores (`base.cfg`). Sin homing | [fase 1](../docs/phase1-plan.md) |
| `phase2.cfg` | Motores X/Y de lazo cerrado (`motors.cfg`), homing de X/Y | [fase 2](../docs/phase2-plan.md) |
| `phase3.cfg` | Sonda de presión (`prtouch.py`), homing de Z | [fase 3](../docs/phase3-plan.md) |
| `phase4.cfg` | Alineación del pórtico (`zalign.cfg`), limpieza de boquilla (`clean.cfg`), `Z_TILT_ADJUST` | [fase 4](../docs/phase4-plan.md) |
| `phase5.cfg` | CFS (`cfs.cfg`) | [fase 5](../docs/phase5-plan.md) |
| `phase6.cfg` | Calentado de cama (`heat.cfg`), malla (`mesh.cfg`), inicio y fin de impresión (`print.cfg`) | [fase 6](../docs/phase6-plan.md) |

`align.cfg` sirve para probar la alineación de Z antes que la sonda (D12).

## Elegir cuál arranca

`HI_CONFIG=phase2.cfg hi_kalico.sh start` [verificado: scripts/hi_kalico.sh, variable `HI_CONFIG`]. Por defecto
arranca `printer.cfg`.

## Niveles de escritura a los drivers (D9)

`startup_writes`: `none`, `stall` o `params` [verificado: [decisions.md D9](../docs/decisions.md)]. `params`
escribe parámetros de los motores y solo se usa con aprobación expresa.

## Qué ajustar

- Temperaturas y límites de seguridad: en fase 1 no pasar de 60 °C de cama (lectura sin la corrección de
  Creality, riesgo R6); `[adc_temperature hi_bed]` la corrige desde la fase 4 [verificado: ESTADO.md].
- Macros de limpieza, CFS y malla: variables `_HI_*` al principio de cada `.cfg`.
- Guardar valores: `SAVE_CONFIG`; `CXSAVE_CONFIG` de Creality equivale a `SAVE_CONFIG RESTART=0`
  [verificado: [phase6-plan.md §3](../docs/phase6-plan.md)].

## Pendiente

- Estructura definitiva de uso diario (un fichero por subsistema) y valores recomendados.
