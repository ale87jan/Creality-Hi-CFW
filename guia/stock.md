# Volver a stock

En la fase 1 no se cambia nada persistente fuera de `/mnt/UDISK/kalico-hi`, así que volver a stock es parar
Kalico y arrancar los servicios de Creality [verificado: scripts/hi_restore.sh:1-10].

## Opciones, de menos a más drástica

| Opción | Orden (en la impresora) | Efecto |
| - | - | - |
| Parar la sesión | `hi_kalico.sh stop` | Apaga calentadores, ventiladores y motores (`TURN_OFF_HEATERS`, `M107`, `M84`), para Kalico y reinicia los servicios de stock |
| Comprobar y volver | `sh hi_restore.sh` (`--dry-run` antes) | Lo anterior más comprobación de los servicios |
| Borrar la instalación | `sh hi_restore.sh --purge` | Además borra `/mnt/UDISK/kalico-hi` |
| Reiniciar | apagar y encender | Kalico se arranca a mano, así que arranca stock [verificado: scripts/hi_kalico.sh:1-5] |

`hi_restore.sh` solo lee las variables de U-Boot y las particiones [verificado: scripts/hi_restore.sh:8-10].

## Si Kalico no responde

1. `hi_kalico.sh status`; después `hi_kalico.sh stop`.
2. Si falla, reiniciar la impresora. Los calentadores se cortan solos si el host muere: las salidas llevan
   `max_duration` [verificado: [phase1-plan.md §5.3](../docs/phase1-plan.md)]. Los ventiladores no.
3. Si una MCU no vuelve a `ready` tras un `FIRMWARE_RESTART`: reiniciar [supuesto, riesgo R3].

## Más adelante: slot A/B

Cambio de slot con `fw_setenv boot_partition` y `root_partition`: **documentado, no ejecutado**
([phase1-plan.md §9](../docs/phase1-plan.md)). Requiere acceso a la consola serie `ttyS0` como recuperación
[verificado: docs/hardware.md]. Este procedimiento deberá probarse antes de darse por válido (objetivo del
proyecto).
