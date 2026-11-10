# Arranque automático de Kalico: diseño (B13)

Estado: **diseño en papel** (2026-11-10, pedido por el usuario). Opción A elegida (D18). Nada de esto está escrito en scripts ni se ha
ejecutado en la impresora. Hoy Kalico solo se arranca a mano con `hi_kalico.sh start` y un reinicio devuelve a
stock ([phase1-plan.md §5.3](phase1-plan.md)). `OTA:` es el rootfs de la imagen V1.1.0.60, solo leído.

## 1. Qué hace stock al arrancar

| Orden | Servicio | Referencia |
| - | - | - |
| S13 | `mcu_update` (actualiza las MCU si hace falta) | [verificado: OTA:etc/init.d/mcu_update:3] |
| S19 | `dropbear` (SSH) | [verificado: OTA:etc/init.d/dropbear:5] |
| S54, S55, S56 | `klipper_mcu`, `klipper`, `moonraker` (procd) | [verificado: OTA:etc/init.d/klipper:3-5, moonraker:3] |
| S80 | `nginx` (Fluidd) | [verificado: OTA:etc/init.d/nginx:4] |
| S95 | `done`: ejecuta `/etc/rc.local`, que en stock está vacío | [verificado: OTA:etc/init.d/done:12-13, OTA:etc/rc.local] |
| S96 | `wipe_data` | [verificado: OTA:etc/init.d/wipe_data:3-8] |
| S99 | `app` (pantalla, nube y demás servidores de Creality), `swupdate_autorun` | [verificado: OTA:etc/init.d/app:3-20] |

- SSH arranca mucho antes que Klipper: si Kalico falla, el acceso por red no depende de él.
- `klipper` de stock, al arrancar, puede reescribir `printer.cfg` del usuario si cambia la versión de la config
  de la ROM [verificado: OTA:etc/init.d/klipper:67-88, 232]. Kalico usa su propia carpeta de config y no le afecta.
- Cualquier fichero escrito en `/etc` va al overlay `rootfs_data`, común a los dos slots A/B
  ([phase1-plan.md §5.2](phase1-plan.md)): el arranque automático no queda aislado por cambiar de slot.

## 2. Opciones

| | Opción | Qué se escribe en el sistema | Vuelta a stock | Valoración |
| - | - | - | - | - |
| A | Servicio propio que conmuta al final del arranque | `/etc/init.d/kalico_hi` y su enlace en `/etc/rc.d` (2 entradas nuevas en el overlay; ningún fichero de stock cambia) | Borrar la bandera en `/mnt/UDISK`, o borrar las 2 entradas | **Recomendada** |
| B | Línea en `/etc/rc.local` | Una copia modificada de un fichero de stock en el overlay | Borrar la copia del overlay | Corre en S95, antes de `app` (S99): habría que esperar en segundo plano a que `app` arranque para pararlo |
| C | Deshabilitar `klipper` y `app` de stock y poner Kalico en su sitio | Borra enlaces de stock en `/etc/rc.d` (marcas de borrado en el overlay) | Rehabilitar los servicios a mano; si falla, stock tampoco arranca | Descartada: toca el arranque de stock, contra B13 |

La opción A repite en el arranque exactamente la conmutación manual de la fase 1 (stock arranca entero y
después se cambia a Kalico), que es el camino que ya se habrá probado a mano. Cuesta unos segundos más de
arranque [supuesto: medirlo en la Hi].

## 3. Diseño de la opción A

`/etc/init.d/kalico_hi`, con un nombre de enlace que ordene después de `S99app` [supuesto: comprobar el orden
real con `ls /etc/rc.d` en la Hi]. No usa procd para lanzar Kalico: solo llama a `hi_boot.sh` del paquete, en
`/mnt/UDISK/kalico-hi`. Si el paquete o la bandera no existen, el servicio no hace nada.

`hi_boot.sh` (nuevo, por escribir) decide en este orden:

1. Sin `/mnt/UDISK/kalico-hi/autostart`: salir. Arranca stock.
2. Con `/mnt/UDISK/kalico-hi/stock-once`: borrarlo y salir. Arranca stock **una** vez.
3. Con `/mnt/UDISK/kalico-hi/boot-pending` (el arranque anterior de Kalico no llegó a `ready`): borrar
   `autostart`, dejar aviso en el log y salir. Evita un bucle de arranques fallidos.
4. Crear `boot-pending` y ejecutar `hi_kalico.sh start --ui`, con sus comprobaciones de siempre (Kalico
   instalado, no arrancado ya y stock sin impresión en curso) [verificado: scripts/hi_kalico.sh:88-94].
5. Esperar a que Kalico responda `ready` en su socket. Si llega, borrar `boot-pending`. Si no llega en el
   plazo, `hi_kalico.sh stop` (apaga calentadores, ventiladores y motores y relanza stock [verificado:
   scripts/hi_kalico.sh:147, cabecera 17-18]) y dejar `boot-pending` para el paso 3.

Órdenes para el usuario, todas en `hi_kalico.sh`: `autostart on|off|status` (crea o borra la bandera) y
`stock-once`. La instalación del servicio la haría `hi_install.sh --autostart`, y `hi_restore.sh` lo quitaría.

## 4. Vuelta a stock

| Situación | Cómo |
| - | - |
| Una sesión en stock | `hi_kalico.sh stock-once` y reiniciar |
| Dejar de arrancar Kalico | `hi_kalico.sh autostart off` (borra un fichero en `/mnt/UDISK`) |
| Quitarlo del sistema | `hi_restore.sh`: borra `/etc/init.d/kalico_hi` y su enlace; `--purge` borra también el paquete |
| Kalico no arranca | Automático: pasos 3 y 5 de §3; SSH sigue disponible (S19) |
| Sin red ni SSH | Restablecimiento de fábrica: formatea `rootfs_data` y con ello borra el servicio [supuesto: paso 0, `parts_clean`; phase1-plan.md §5.2] |

## 5. Lo que hay que comprobar antes de escribirlo

Solo lectura, en la Hi:

- `ls /etc/rc.d` y `ls -la /overlay/upper/etc` para ver el orden real y qué hay ya en el overlay.
- Si una actualización OTA de Creality conserva el overlay [supuesto: no se sabe; decide si el servicio sobrevive
  a una actualización].
- Tiempo desde el encendido hasta que `app` está arriba, para fijar el plazo del paso 5.
- Que la conmutación manual (`hi_kalico.sh start --ui` y `stop`) funciona varias veces seguidas: es la fase 1
  completa y es requisito de este diseño.

## 6. Riesgos

- La pantalla de Creality queda sin servicio con Kalico ([phase1-plan.md §5.3](phase1-plan.md)); su sustituto se
  estudia en `docs/screen-plan.md`.
- Stock arranca primero y habla con las MCU y los drivers antes de la conmutación. Es lo mismo que en la
  conmutación manual, pero aquí pasa sin nadie delante.
- Un corte de luz durante una impresión con Kalico: al volver arrancaría stock y después Kalico; la recuperación
  de impresión no está portada (`power_loss_recovery`, pendiente).
- Escribir en `/etc` es la primera escritura en el overlay de todo el proyecto: necesita aprobación expresa del
  usuario en su momento (B13).
