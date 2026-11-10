# Solución de problemas

Formato: síntoma, causa probable, qué hacer. Las causas son [supuesto] salvo indicación.

| Síntoma | Causa probable | Qué hacer |
| - | - | - |
| `hi_install.sh` rechaza el modelo o el firmware | Solo se ha contrastado F018 con 1.1.0.60 | No forzar sin leer el [plan](../docs/phase1-plan.md); `--any-version` bajo tu responsabilidad |
| El `c_helper.so` pide `GLIBC_2.34` | El del fork se compiló para otra glibc; la Hi tiene 2.29 [verificado: phase1-plan.md] | Usar el que genera `scripts/build_chelper.sh` |
| Falla el paso 0, sección 13 | `.so` no carga con la glibc o cffi reales | Parar y guardar el error (riesgo R1) |
| `hi_kalico.sh start` no llega a `ready` | MCU no responde o config no cargada | Mirar `/mnt/UDISK/kalico-hi/logs/klippy.log` (`Loaded MCU` ×3, sin `Traceback`) |
| Tras un `FIRMWARE_RESTART` no vuelve a `ready` | La MCU puede quedarse en el cargador (riesgo R3) | Reiniciar la impresora |
| La pantalla no responde | Servicios de Creality parados durante la sesión [verificado] | `hi_kalico.sh stop` |
| Los Z suben desiguales | Pórtico sin alinear | `G28` (alineación) y `Z_TILT_ADJUST` |
| Las limpiezas dejan de ejecutarse | Guarda `busy` tras un fallo | `NOZZLE_CLEAN_RESET` |
| Fluidd no conecta | El Moonraker de stock con Kalico no está probado (R7) | Volver al escalón 2 y usar la consola |
| El CFS no responde | Direcciones sin asignar o bus ocupado por los motores | `CFS_INIT` con Kalico en reposo; revisar [rs485.md](../docs/protocols/rs485.md) |

Sección a ampliar con los resultados reales de las pruebas en la Hi.
