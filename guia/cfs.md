# CFS (Creality Filament System)

Módulo `creality_cfs.py` de [gitstonelabs/creality-cfs-klipper](https://github.com/gitstonelabs/creality-cfs-klipper)
(GPLv3) sobre el bus RS-485 compartido `serial_485` (D16). Plan y comparación de tramas:
[phase5-plan.md](../docs/phase5-plan.md); protocolo: [rs485.md](../docs/protocols/rs485.md).

> **Sin probar en hardware.** El propio módulo de referencia declara que no se ha ejercitado aún en hardware
> [verificado: phase5-plan.md, límites y pendientes 1].

## Seguridad

- `auto_init: False`: al arrancar no se envía nada al CFS. `CFS_INIT` asigna direcciones y es manual [verificado:
  test `test_phase5_config_loads_and_sends_nothing_at_startup`].
- `CFS_EXTRUDE`, `CFS_RETRUDE`, `CFS_CUT` y `CFS_FLUSH` calientan la boquilla y mueven filamento; `CFS_CUT`
  golpea la cuchilla en el extremo derecho de X.
- Primero las pruebas de solo lectura (paso 5 del plan), con el CFS vacío.

## Geometría de la Hi

- La cuchilla corta en **+X** (la K2 corta en -X).
- La papelera está a la izquierda, fuera de la cama (purga en X=-18,5), colgada del pórtico: la purga no depende
  de Y (se hace en Y=261) [verificado: usuario, 2026-11-10].
- La limpieza va en el teflón trasero (Y=266), con la placa metálica de sellado a su lado.

## Comandos

| Comando | Qué hace |
| - | - |
| `CFS_INIT` | Autodireccionamiento del bus |
| `CFS_STATUS` | Estado, temperatura y humedad de la caja (bytes `b0`/`b1` de `0x0A`) [verificado: test; comprobar contra la pantalla del CFS] |
| `CFS_EXTRUDE`, `CFS_RETRUDE` | Carga y descarga |
| `CFS_CUT` | Corte del filamento |
| `CFS_FLUSH` | Purga donde esté la boquilla |
| `CFS_PURGE` | Va a la papelera y ejecuta `CFS_FLUSH` con los mismos parámetros |
| `T0` a `T3` | Cambio de filamento: sube Z, corta, purga, descarga, carga y vuelve |

Tras un reinicio el módulo no sabe qué filamento hay cargado: indicarlo con `PREV=` [verificado: phase5-plan.md,
pendiente 5].

## Pendiente

- Tramas no solicitadas (avisos de inserción, fallos) se pierden; guardar el filamento cargado entre
  reinicios; alias `BOX_*`; rack externo (fuera de la primera versión).
- Cortar con `cut_velocity` de 3000 hasta validar; stock usa 15000.
