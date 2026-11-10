# Comandos y macros

Todo [supuesto] en la impresora: ninguna macro se ha ejecutado en la Hi. Ejecutar un comando en una sesión:
`hi_kalico.sh gcode "COMANDO"` ([instalar.md](instalar.md)).

## Homing y Z

| Comando | Definido en | Qué hace |
| - | - | - |
| `G28` | `phase4.cfg` (`_HI_HOME`, `_HI_ALIGN`) | Sube un poco el pórtico si Z es desconocido, referencia X/Y, alinea el pórtico en los sensores superiores (`ZDOWN`) y referencia Z con la sonda |
| `G28 ALIGN=1` | `phase4.cfg` | Fuerza la alineación aunque Z esté referenciado |
| `ZDOWN_SWITCH ENABLE=0` | `z_align_hi.py` (config en `zalign.cfg`) | Omite la alineación en los siguientes homings de Z |
| `Z_TILT_ADJUST` | Kalico (`[z_tilt]`) | Nivelado fino; hay que repetirlo tras cada alineación (se pierde) |

En la Hi `ZDOWN` **sube** el puente hasta los sensores ópticos (cama móvil solo en Y); el nombre es herencia de la
K2 [verificado: usuario, 2026-11-10; [phase4-plan.md](../docs/phase4-plan.md)].

## Limpieza de boquilla (`clean.cfg`, D14)

`NOZZLE_CLEAN` (completa la primera vez, rápida después), `NOZZLE_WIPE`, `NOZZLE_QUICK_WIPE` y
`NOZZLE_CLEAN_RESET` (libera la guarda tras un fallo). Parámetro `SEAL_TEMP=` (por defecto 160 en el port).
Si se interrumpe, la guarda bloquea las siguientes: ejecutar `NOZZLE_CLEAN_RESET`.

## Impresión (`heat.cfg`, `mesh.cfg`, `print.cfg`)

| Comando | Qué hace |
| - | - |
| `M140`, `M190` | Calentado de cama inteligente, asíncrono y bloqueante |
| `G29` | Malla de cama por temperatura (9x9) |
| `START_PRINT`, `END_PRINT` | Inicio y fin de impresión (base: macros del usuario) |
| `PAUSE`, `RESUME`, `CANCEL_PRINT` | Control de la impresión |
| `NOZZLE_CLEAN`, ... | Ver arriba |

## Comandos de Creality y su equivalente

Tabla completa: [phase6-plan.md §3](../docs/phase6-plan.md). Resumen: `CXSAVE_CONFIG` → `SAVE_CONFIG RESTART=0`;
`EXCLUDE_OBJECT_RESET` → `EXCLUDE_OBJECT_DEFINE RESET=1`; `SET_QMODE_FLAG`/`SET_RMODE_FLAG` se quitan; `BOX_*`
sustituidos por los comandos del CFS ([cfs.md](cfs.md)).

## Pendiente

- Parámetros de `START_PRINT` y plantilla del G-code inicial para el laminador.
