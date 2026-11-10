# Fase 1 — Kalico arrancando en la Hi: análisis y plan

Fecha: 2026-11-09. Alcance: las tres MCU, steppers Z/Z1/E, temperaturas y ventiladores, sobre el Tina de stock
V1.1.0.60. Fuera: motores X/Y, sonda, CFS, bus RS-485.

Cada afirmación lleva su origen:

- **[verificado: fichero:línea]** leído en ese fichero o comprobado ejecutando lo que se indica.
- **[supuesto: cómo comprobarlo]** sin comprobar todavía.

Abreviaturas de origen: `K:` = repo Creality-Hi-Kalico (commit `a0b3a40`); `OTA:` = rootfs de la imagen
`CR4NU200360C20_ota_img_V1.1.0.60.img` (SHA-256 en [firmware/README.md](../firmware/README.md)), extraída con
`cpio` + `unsquashfs` y solo leída; sin prefijo = este repo. Estado y siguiente acción: [ESTADO.md](ESTADO.md).

## 1. Conclusiones

1. **Kalico corre con el Python de stock de la Hi sin instalar nada.** Con Python 3.9 y las versiones exactas de la
   Hi (cffi 1.14.6, greenlet 1.0.0, numpy 1.20.1, Jinja2 3.0.3, MarkupSafe 2.1.0, pyserial 3.4) pasan 133 de 134
   tests que no necesitan diccionarios de MCU y la config mínima en modo batch. El test que falla es ajeno a las
   versiones (§3.2). Hecho en x86-64; falta repetirlo en ARM en la impresora.
2. **El `c_helper.so` que trae el fork no sirve para la Hi**: pide `GLIBC_2.34` y la Hi tiene 2.29. Hay que
   compilar uno propio; ya hay script reproducible y carga en ARM emulado (§4).
3. **El slot A/B libre no aísla cambios de ficheros**: el overlay es un único volumen `rootfs_data` para los dos
   slots. Por eso la fase 1 se plantea sin escribir en flash: Kalico vive en `/mnt/UDISK/kalico-hi` y se lanza a
   mano; un reinicio devuelve a stock (§5). El uso del slot libre queda diseñado pero aplazado (§9).
4. **La Hi no tiene `git`, `gcc`, `wget`, `curl`, `nohup`, `setsid` ni herramientas UBI.** El instalador no puede
   clonar el fork (contra lo previsto en D3): se instala un `.tar.gz` verificado con SHA-256 (§6).
5. **Los servicios de Creality hablan con Klipper por `/tmp/klippy_uds`**. Kalico usa otro socket y esos
   servicios se paran durante la sesión de prueba (§5.3).

## 2. Qué asume Kalico del sistema

| Aspecto | Qué pide Kalico | Qué hay en la Hi | Resultado |
| - | - | - | - |
| Python | `>=3.9` [verificado: K:pyproject.toml:4] | 3.9.12 [verificado: docs/hardware.md:12] | Cumple. Sintaxis: los 98 módulos importados por `klippy/` se analizan con la gramática de 3.9 sin errores [verificado: análisis `ast` con `feature_version=(3,9)` sobre K:klippy] |
| cffi | `==1.15.1` [verificado: K:pyproject.toml:7] | 1.14.6 [verificado: OTA:usr/lib/python3.9/site-packages/cffi-1.14.6-py3.9.egg-info] | Funciona en pruebas (§3.2) |
| greenlet | `==2.0.2` [verificado: K:pyproject.toml:11] | 1.0.0 | Funciona en pruebas |
| Jinja2 | `>=3.1.6` [verificado: K:pyproject.toml:12] | 3.0.3 | Funciona en pruebas. La 3.1.6 corrige fallos de seguridad del sandbox; las macros aquí son locales |
| MarkupSafe | `==2.1.5` [verificado: K:pyproject.toml:13] | 2.1.0 | Funciona en pruebas |
| numpy | `~=2.0` [verificado: K:pyproject.toml:14] | 1.20.1 | Se importa al arrancar [verificado: K:klippy/webhooks.py:16]. Funciona en pruebas. Los módulos que lo usan a fondo (input shaper, `z_tilt_ng`, `load_cell`) quedan fuera de la fase 1 |
| pyserial | `==3.4` [verificado: K:pyproject.toml:17] | 3.4 | Igual. Usa `exclusive=True` [verificado: K:klippy/serialhdl.py:311], disponible en 3.4 |
| python-can | `~=4.6` [verificado: K:pyproject.toml:18] | No está | No hace falta: solo se importa al usar CAN [verificado: K:klippy/serialhdl.py:144,221] |
| Biblioteca estándar | zlib, ctypes, multiprocessing, json… | Presentes; `zlib` va dentro de `libpython3.9.so` [verificado: OTA: `strings usr/lib/libpython3.9.so.1.0` contiene `PyInit_zlib`; resto en `usr/lib/python3.9/lib-dynload`] | Cumple [supuesto: sección 08 de `scripts/hi_step0.sh`] |
| Módulo C | Compila `c_helper.so` con `gcc` al arrancar si falta o es más antiguo que los fuentes; sin `gcc` reutiliza el existente con un aviso [verificado: K:klippy/chelper/__init__.py:347-360] | Sin `gcc` [verificado: OTA: no existe `usr/bin/gcc`] | Hay que llevar el `.so` hecho (§4) |
| `git` | Lo usa para la versión; si falla lee `klippy/.version` [verificado: K:klippy/util.py:136,212-253] | Sin `git` [verificado: OTA: no existe en `bin`, `usr/bin`] | El paquete escribe `klippy/.version` [verificado: scripts/make_bundle.sh:54] |
| `HOME` escribible | Caché de plantillas en `~/.cache/klippy/` [verificado: K:klippy/extras/gcode_macro.py:103-106] | Stock arranca Klipper con `HOME=/mnt/UDISK` [verificado: OTA:etc/init.d/klipper:276] | Se lanza con `HOME=/mnt/UDISK/kalico-hi` [verificado: scripts/hi_kalico.sh] |
| Arranque de procesos | `multiprocessing` en modo `fork` [verificado: K:klippy/printer.py:669] | Linux 5.4 | Cumple |
| Init | Ninguno propio: un proceso `python klippy.py cfg -l log -a socket` [verificado: K:klippy/printer.py:526-596] | procd; el servicio de stock usa esa misma forma [verificado: OTA:etc/init.d/klipper:277] | En fase 1 no se registra servicio (§5) |

## 3. Kalico frente a Klipper: lo que afecta a la Hi

### 3.1 Diferencias que tocan esta fase

| Diferencia | Detalle | Consecuencia |
| - | - | - |
| Paquete Python `klippy` | Kalico es un paquete (`python -m klippy`); `klippy/klippy.py` queda como lanzador [verificado: K:klippy/klippy.py:3-9] | Se lanza por ruta, como hace stock |
| Plugins | Carga `klippy/plugins/` además de `extras/` [verificado: K:klippy/printer.py:195] | Sitio para los módulos propios de la Hi (D1) |
| `[danger_options]` | Sección nueva; por defecto las opciones de config desconocidas son error [verificado: K:klippy/printer.py:341] | La config de stock no carga tal cual: lleva opciones de Creality (§7.2) |
| Ventiladores | `off_below` está obsoleto [verificado: K:klippy/extras/fan.py:25]. `min_power` no es equivalente: reescala la petición entre `min_power` y `max_power` [verificado: K:klippy/extras/fan.py:100-103] | Con `min_power: 0.2` y `max_power: 0.5`, `M106 S128` da 0,35 de ciclo; en stock da 0,25. Los perfiles de ventilador habrá que reajustarlos |
| Aceleración | `max_accel_to_decel` se sustituye por `minimum_cruise_ratio` [verificado: K:klippy/toolhead.py:259] | Omitido en fase 1 (valor por defecto 0.5) |
| TMC con enable compartido | Usa "virtual enable" por UART cuando el pin de enable no es exclusivo [verificado: log del modo batch: `Enabling TMC virtual enable for 'stepper_z'`] | Z y Z1 comparten `!PA11` con X/Y; es el comportamiento estándar |
| Temperatura de MCU | El fork de Jacob añade los `gd32f303xe/xb` y `gd32e230x8` [verificado: K:klippy/extras/temperature_mcu.py:110-112] | `[temperature_sensor mcu_temp]` funciona sin parches |
| Reinicio de MCU | `restart_method: command` envía `reset` igual que stock [verificado: K:klippy/mcu.py:926-945 frente a OTA:usr/share/klipper/klippy/mcu.py:936-954]; las tres MCU tienen `reset` [verificado: K:test/hi/*.dict] | Sin cambio respecto a stock (riesgo R3) |
| Versiones de MCU | Kalico registra `app` y versión; los diccionarios de la Hi no traen `app` [verificado: docs/protocols/mcu.md:42] | Sin aviso de reflasheo |

### 3.2 Pruebas hechas en PC

Entorno: contenedor `python:3.9-slim-buster` (Python 3.9.17, glibc 2.28) con las versiones de pip de la Hi.

| Prueba | Resultado |
| - | - |
| `pytest test --ignore=test/klippy` | 133 pasan, 1 falla: `test_import_extra`, porque `extras/cartographer.py` importa el paquete externo `cartographer` de la K2 [verificado: K:klippy/extras/cartographer.py:2]. No depende de las versiones |
| `pytest test/test_hi_config.py` | 6 pasan (§7.3) |
| Tests `test/klippy/*.test` | No ejecutados: necesitan diccionarios que solo están en la imagen de CI de Kalico, inaccesible desde la nube. Los ejecuta el CI del pull request |
| Paquete real, `klippy.py` con socket de API, sin MCU | Arranca, `hi_gcode.py info` responde `state: startup` y la versión de `klippy/.version` |

Sin validar en PC: tiempo real en el Cortex-A7 (carga de CPU, retransmisiones serie), las UART reales y los
TMC2208. Solo se resuelven en la impresora (§8).

## 4. `c_helper.so`

- El binario del fork es ARM hard-float pero está enlazado contra glibc ≥ 2.34 [verificado: `readelf -V
  K:klippy/chelper/c_helper.so` lista `GLIBC_2.34`; `nm -D` muestra `pthread_create@GLIBC_2.34`]. Al cargarlo con
  glibc 2.28 falla con `version 'GLIBC_2.34' not found` [verificado: `qemu-arm` + `scripts/chelper_load.py`].
- `scripts/build_chelper.sh <ruta a Creality-Hi-Kalico>` lo compila en Docker con el compilador cruzado de
  Ubuntu 18.04 (gcc 7.5.0, glibc 2.27), imagen fijada por digest [verificado: scripts/Dockerfile.chelper:9].
- La lista de fuentes y los flags base se leen de `chelper/__init__.py` del propio fork, así siguen a upstream
  [verificado: scripts/chelper_build.py:35-52].
- CPU/FPU: `-mcpu=cortex-a7 -mfpu=neon -mfloat-abi=hard`, lo mismo que declaran los binarios de stock
  (VFPv3 + NEON) [verificado: `readelf -A OTA:usr/bin/python3.9` y `OTA:usr/share/klipper/klippy/chelper/c_helper.so`].
- Comprobaciones automáticas del script: ELF ARM hard-float, atributos esperados, símbolo de glibc más alto ≤ 2.29
  y bibliotecas `NEEDED` permitidas [verificado: scripts/chelper_build.py:85-119]. Resultado actual: glibc máxima
  2.17.
- Reproducible: dos compilaciones desde caché vacía dan
  `80db43303b1fac7dd5070fcff846bca81488a233b0532668b2d6ea26017a9ad0` para el commit `5b944e9`
  [verificado: ejecutado dos veces el 2026-11-09].
- Todos los símbolos que importa existen con esa versión en las bibliotecas de stock de la Hi
  [verificado: `nm -D` del `.so` contra `OTA:lib/libc.so.6`, `libm.so.6`, `libpthread.so.0`].
- Carga y ejecuta en ARMv7 emulado con Python 3.9 y glibc 2.28 [verificado: `qemu-arm` + `chelper_load.py`:
  `OK: c_helper.so loads on armv7l, python 3.9.17, libc glibc-2.28`].
- El objetivo `loadtest` del Dockerfile (contenedor ARM emulado) no se ha ejecutado tal cual: el contenedor de la
  nube no tiene `binfmt`. La misma prueba se hizo con `qemu-arm` a mano [supuesto: ejecutar
  `scripts/build_chelper.sh` sin `--no-loadtest` en Docker Desktop].
- Pendiente: carga con el cffi real de la Hi [supuesto: sección 13 de `hi_step0.sh` y la prueba de `hi_install.sh`].

## 5. Arranque sobre Tina

### 5.1 Cómo arranca el Klipper de stock

| Orden | Servicio | Qué hace |
| - | - | - |
| S13 | `mcu_update` | Saluda a cada MCU por su UART, compara versión con `/usr/share/klipper/fw/F018`, reflashea si difiere y si no envía "startup app" (`mcu_util -s`) [verificado: OTA:etc/init.d/mcu_update:384-401]. Actualiza también los dispositivos RS-485 |
| S54 | `klipper_mcu` | MCU Linux del host (`klipper_mcu -r`) para el I2C de la EEPROM [verificado: OTA:etc/init.d/klipper_mcu:12] |
| S55 | `klipper` | Copia o actualiza la config desde `/usr/share/klipper/config/F018_CR4NU200360C20` según la cabecera `Version` y lanza `klippy.py` con `-a /tmp/klippy_uds` [verificado: OTA:etc/init.d/klipper:192-236,277] |
| S56 | `moonraker` | Moonraker con `/usr/share/moonraker/moonraker.conf` [verificado: OTA:etc/init.d/moonraker:17] |
| S80 | `nginx` | Fluidd en el puerto 4408 [verificado: OTA:etc/nginx/nginx.conf:16,32] |
| S99 | `app` | `master-server`, `display-server`, `app-server`, `web-server`, `upgrade-server`, `Monitor`… [verificado: OTA:etc/init.d/app:9-20] |

Consecuencias:

- `mcu_update` sigue ejecutándose en cada arranque y deja las MCU con su aplicación en marcha. Kalico no lo
  sustituye ni lo necesita cambiar.
- El servicio `klipper` de stock reescribe `printer.cfg` de `/mnt/UDISK/printer_data/config` cuando cambia la
  versión de la cabecera. Kalico usa su propia carpeta de config para no interferir.
- No hay `klipper_mcu` en la config de fase 1, así que la MCU Linux de stock sigue corriendo sin uso.

### 5.2 Sistema de ficheros y slots

- Dos slots: `bootA/rootfsA` y `bootB/rootfsB`, elegidos por las variables de U-Boot `boot_partition` y
  `root_partition` [verificado: OTA:sw-description:9-53].
- El rootfs es SquashFS de solo lectura [verificado: firmware/README.md:42].
- `/overlay` se monta desde `/dev/by-name/rootfs_data`, un único volumen sin variante por slot, y los datos de
  usuario desde `/dev/by-name/UDISK` en `/mnt/UDISK` [verificado: OTA:etc/config/fstab:21-31].
- Que `/` sea un overlayfs con `rootfs_data` encima del SquashFS lo hace el binario `mount_root`
  [supuesto: sección 04 de `hi_step0.sh`, línea `overlayfs:/overlay on / type overlay`].
- Existe un borrado de particiones por variable de U-Boot: `parts_clean` formatea `rootfs_data` y/o `UDISK` en el
  siguiente arranque [verificado: OTA:lib/preinit/79_format_partition:124-143]. **No usar**: borra también la
  config y los gcodes.
- No se conoce mecanismo de vuelta automática si un slot no arranca [supuesto: sección 02 de `hi_step0.sh`,
  variables `bootcmd`, `bootlimit`, `bootcount`].

Implicación: lo que se escriba en `/etc` o `/usr` con el sistema en marcha va al overlay y vale para los dos
slots. Cambiar de slot solo cambia kernel y SquashFS.

### 5.3 Diseño de la fase 1 (decisión D5)

Tres escalones, cada uno reversible antes de pasar al siguiente:

| Escalón | Qué cambia en la impresora | Vuelta a stock |
| - | - | - |
| 1. Ficheros | `hi_install.sh` copia el paquete a `/mnt/UDISK/kalico-hi`. Nada se ejecuta | `hi_restore.sh --purge` o borrar la carpeta |
| 2. Sesión | `hi_kalico.sh start` para `app` y `klipper` de stock y lanza Kalico con socket `/tmp/kalico_uds`. Nada persistente | `hi_kalico.sh stop`, `hi_restore.sh` o reiniciar |
| 3. Fluidd | `hi_kalico.sh start --ui` relanza el Moonraker de stock con una copia de su config que apunta a `/tmp/kalico_uds` | Igual que el escalón 2 |

No se toca flash, overlay, variables de U-Boot ni parámetros de motores en ninguno de los tres. Qué hace cada
script: [verificado: scripts/hi_install.sh:1-17, scripts/hi_kalico.sh:1-20, scripts/hi_restore.sh:1-10].

Por qué se paran los servicios de Creality: `master-server`, `display-server` y `app-server` contienen la ruta
`/tmp/klippy_uds` [verificado: `strings OTA:usr/bin/master-server`, `display-server`, `app-server`]. Con Kalico en
ese socket recibirían respuestas a peticiones propietarias que Kalico no implementa. Con socket propio y `app`
parado, la pantalla queda sin servicio durante la sesión.

Seguridad al parar: `hi_kalico.sh stop` envía `TURN_OFF_HEATERS`, `M107` y `M84` antes de matar el proceso
[verificado: scripts/hi_kalico.sh, función `do_stop`; scripts/selftest.sh lo comprueba]. Si Kalico muere sin
avisar, las MCU cortan los calentadores solas: sus salidas llevan `max_duration` [verificado: salida del modo
batch, `config_digital_out ... pin=PC8 ... max_duration=360000000` y `pin=PB8`]. Los ventiladores no llevan
límite y se quedan como estaban.

## 6. Paquete e instalación

- `scripts/make_bundle.sh <ruta a Creality-Hi-Kalico>` genera `build/kalico-hi-<commit>.tar.gz` y su `.sha256`:
  árbol `klippy/` del commit (`git archive`), el `c_helper.so` cruzado, los `.cfg` de `config/hi/`, las herramientas
  `hi_*` y un `SHA256SUMS` por fichero [verificado: scripts/make_bundle.sh:51-66].
- Es determinista: mismo par de commits, mismo SHA-256 [verificado: ejecutado dos veces]. Pesa unos 0,8 MB.
- Se rechaza si hay cambios sin commit en `klippy/` o `config/hi`, o si el `.so` es de otro commit
  [verificado: scripts/make_bundle.sh:28-31,44].
- `hi_install.sh` comprueba antes de escribir: modelo F018, firmware 1.1.0.60, slot activo (lo anota), punto de
  montaje, SHA-256 del paquete, rutas del `.tar.gz`, espacio libre, Python 3.9 con sus módulos y que Kalico no
  esté corriendo. Después verifica cada fichero extraído, carga el `.so` y prueba el enlace cffi; si algo falla,
  borra lo extraído y no cambia la instalación anterior [verificado: scripts/hi_install.sh:47-162].
- Los tres scripts de la impresora se prueban con `scripts/selftest.sh` contra una impresora simulada: 31
  comprobaciones, entre ellas que `--dry-run` no escribe nada, que se rechaza otro modelo, otro firmware o un
  checksum malo, el orden de parada y arranque de servicios y que no se conmuta con una impresión en curso
  [verificado: ejecutado con `busybox ash`, 31 de 31].
- Límite del autotest: usa un Klipper simulado y servicios falsos. No prueba `/etc/init.d` reales
  [supuesto: escalones de §8].

## 7. Config mínima

Ficheros: Creality-Hi-Kalico `config/hi/printer.cfg`, que incluye `base.cfg` (desde el 2026-11-10). Pines y valores copiados de la config que corre en la
impresora [verificado: data/captures/2026-11-09_hi-v1.1.0.60/printer-config/printer.cfg y toolhead.cfg].

### 7.1 Decisiones de la config

- **X e Y se declaran pero no se pueden mover.** La cinemática cartesiana exige `stepper_x` y `stepper_y`. Sin
  `motor_control` no hay homing, y sin homing Kalico rechaza cualquier movimiento de esos ejes. Un
  `[homing_override]` convierte todo `G28` en error [verificado: K:config/hi/printer.cfg, secciones
  `homing_override`, `stepper_x`, `stepper_y`; K:test/test_hi_config.py comprueba que no se emite ningún paso].
- **Z se mueve sin homing** con `SET_KINEMATIC_POSITION Z=<z> SET_HOMED=z`
  [verificado: K:klippy/extras/force_move.py:160-174].
  Z y Z1 reciben la misma secuencia de pasos [verificado: salida del modo batch].
- **Finales de carrera de Z**: se usan `PB15` y `PB14`, los sensores fotoeléctricos de `[z_align]` de stock, solo
  para verlos con `QUERY_ENDSTOPS`. `position_endstop: 0` es un valor de relleno que no se usa.
- **Ventilador auxiliar**: no hay. `[output_pin fan0]` de stock (PB2) es una salida virtual sin ventilador
  conectado [usuario, 2026-11-10]; `[fan_generic aux_fan]` se quitó de `base.cfg`.

### 7.2 Lo que se deja fuera y por qué

| Sección de stock | Motivo |
| - | - |
| `heater_bed`: `temp_offset_flag`, `adc_temp_list`, `actual_temp_list`, `power_calibration_*` | Opciones del Klipper de Creality; no existen en Kalico. La corrección de la tabla se reproduce desde el 2026-11-10 con un sensor `[adc_temperature hi_bed]` en `base.cfg` (error ≤ 0,25 °C); `power_calibration_*` sigue sin portar [verificado: printer-config/printer.cfg, sección `heater_bed`] |
| `motor_control`, `serial_485`, `box`, `auto_addr`, `filament_rack` | Fases 2 y 5 |
| `prtouch_v3`, `nozzle_clear`, `z_align`, `z_tilt`, `bed_mesh` | Fases 3 y 4 |
| `mcu rpi`, `bl24c16f`, `io_remap`, `tmc_line_check`, `timer_read`, `fan_feedback`, `custom_macro` | Módulos de Creality por portar (fase 4) |
| `lis2dw`, `resonance_tester` | No hacen falta para arrancar |
| Macros | Usan comandos del Klipper de Creality (fase 6) |

### 7.3 Validación en PC

`test/test_hi_config.py` lanza Kalico en modo batch contra los diccionarios reales de las tres MCU
(`test/hi/*.dict`) y comprueba [verificado: 6 de 6 con las versiones de Python de la Hi]:

- la config carga y todos los comandos que genera existen en los diccionarios de la Hi;
- con `test/hi/phase1.gcode` solo reciben pasos Z (PB4) y Z1 (PB6);
- `G28`, `G28 Z`, `G1 X10`, `G1 Y10` y un movimiento combinado X+Z se rechazan sin emitir pasos.

No lo valida: valores eléctricos (corrientes, PID), sentido de giro, respuesta de los TMC por UART ni lecturas
de ADC. El modo batch no simula respuestas de la MCU.

## 8. Plan de ejecución en la impresora

Cada paso indica qué pegar de vuelta. Todo lo que no sea el paso 0 necesita tu visto bueno previo.

### Paso 0 — inventario de solo lectura

```sh
# En el PC, desde Creality-Hi-CFW (un fichero por scp, con -O):
scp -O scripts/hi_step0.sh root@<ip>:/tmp/
scp -O scripts/chelper_load.py root@<ip>:/tmp/
scp -O build/chelper/c_helper.so root@<ip>:/tmp/
ssh root@<ip> "sh /tmp/hi_step0.sh /tmp/c_helper.so > /tmp/step0.txt 2>&1"
scp -O root@<ip>:/tmp/step0.txt data/captures/2026-11-09_hi-v1.1.0.60/step0.txt
```

No hace falta parar Klipper. El script enmascara números de serie y MAC y no lee direcciones IP; revisa el
fichero antes de subirlo.

| Sección | Qué se espera | Si no coincide |
| - | - | - |
| 01 | `model=F018`, `fw_version=1.1.0.60` | Parar: los scripts se han contrastado con esa versión |
| 02 | `boot_partition`/`root_partition` con el mismo sufijo (A o B); `swu_mode` vacío | Anotar el slot activo. Las variables de arranque dirán si hay vuelta automática |
| 03 | `bootA`, `bootB`, `rootfsA`, `rootfsB`, `rootfs_data`, `UDISK`, `env`, `env-redund` en `/dev/by-name` | Revisar §5.2 |
| 04 | `/` de tipo `overlay`; `/rom` SquashFS; `/mnt/UDISK` ext4 con más de 25 MB libres | Si `/` no es overlay, el escalón 3 no cambia; sí el diseño A/B de §9 |
| 05 | Ninguna línea `MODIFIED` | Hay scripts de servicio cambiados: revisar antes de usar `hi_kalico.sh` |
| 06 | `Features` con `neon` y `vfpv4`; 2 núcleos (T113-i) | Sin `neon`: recompilar con otra `-mfpu` |
| 08 | Python 3.9.12; `ok` en todo salvo `can` (`FAIL` esperado) | Si falla cffi, greenlet, jinja2, serial o zlib: parar |
| 09 | `git`, `gcc`, `wget`, `curl`, `nohup`, `setsid` con `-`; `tar`, `gzip`, `sha256sum`, `pgrep` presentes | Ajustar scripts |
| 11 | Tres entradas en `/tmp/.mcu_version` con las versiones de docs/hardware.md | Parar |
| 12 | Línea `Stats` del Klipper de stock: referencia de `sysload` y `bytes_retransmit` | Solo referencia |
| 13 | `OK: c_helper.so loads on armv7l, python 3.9.12, libc glibc-2.29` | Parar y pegar el error |

### Pasos siguientes (con la impresora en reposo y fría)

| Paso | Orden | Criterio de éxito | Riesgo |
| - | - | - | - |
| 1 | `sh hi_install.sh --dry-run <paquete>` y después sin `--dry-run` | Todas las líneas `ok`; `OK: cffi binding` | Solo escribe en `/mnt/UDISK/kalico-hi` |
| 2 | `hi_kalico.sh start --dry-run` | Lista de órdenes coherente con §5.3 | Ninguno |
| 3 | `hi_kalico.sh start` | `state: ready`. En `logs/klippy.log`: tres `Loaded MCU`, sin `Traceback` | Pantalla sin servicio hasta `stop` |
| 4 | `hi_kalico.sh temps` | Boquilla, cama y MCU a temperatura ambiente coherente (±5 °C entre sí) | Ninguno |
| 5 | `hi_kalico.sh gcode "DUMP_TMC STEPPER=stepper_z"` y lo mismo con `stepper_z1` y `extruder` | Registros sin error de UART | Ninguno: solo lee |
| 6 | `hi_kalico.sh gcode "QUERY_ENDSTOPS"` | Respuesta para x, y, z | Ninguno: solo lee |
| 7 | `hi_kalico.sh gcode "M106 S128"`, `M107` | Los ventiladores giran y paran | Bajo |
| 8 | `hi_kalico.sh gcode "SET_HEATER_TEMPERATURE HEATER=extruder TARGET=50"`; después cama a 40 | Sube, se estabiliza, arranca el ventilador del hotend a 50 °C; apagar con `TURN_OFF_HEATERS` | Medio: vigilar; `verify_heater` activo |
| 9 | Con la boquilla a más de 30 mm de la cama: `SET_KINEMATIC_POSITION Z=50 SET_HOMED=z`, `G91`, `G1 Z2 F300`, `G1 Z-2 F300` | El puente sube y baja 2 mm nivelado | Medio: Z y Z1 sin alinear ni finales de carrera. Movimientos cortos y hacia arriba primero |
| 10 | Con la boquilla a 200 °C y sin filamento cargado: `M83`, `G1 E5 F120` | El extrusor gira | Bajo |
| 11 | 30 min en reposo; `grep ^Stats logs/klippy.log \| tail -1` | `bytes_retransmit` estable y `sysload` comparable al de stock (paso 0, sección 12) | Ninguno |
| 12 | `hi_kalico.sh stop` | `stock klippy running`; la pantalla vuelve | Ninguno |
| 13 | `hi_kalico.sh start --ui` y abrir Fluidd | Fluidd conecta y muestra temperaturas | Moonraker de stock con Kalico: sin probar |

### Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | El `.so` no carga con el cffi o la glibc reales | Paso 0, sección 13, y prueba de `hi_install.sh` antes de arrancar nada |
| R2 | Carga de CPU o retransmisiones serie mayores que en stock (el núcleo de movimiento de Kalico es más reciente) | Paso 11. Si es mayor, medir antes de añadir X/Y |
| R3 | Al conectar, Kalico ve una config de MCU distinta y envía `reset`; la MCU podría quedarse en el cargador esperando el "startup app" de `mcu_update` | Stock usa el mismo `reset` [verificado: OTA:usr/share/klipper/klippy/mcu.py:936-954], así que un `FIRMWARE_RESTART` de stock ya recorre ese camino [supuesto: comprobar que tras `FIRMWARE_RESTART` en stock Klipper vuelve a `ready`]. Si no vuelve: reiniciar la impresora |
| R4 | `/etc/init.d/klipper start` de stock tras la sesión reescribe `printer.cfg` si la cabecera `Version` no coincide con la del rootfs | Ya ocurre en cada arranque de stock; Kalico no toca esa carpeta |
| R5 | Z y Z1 se mueven sin alineación | Movimientos de 2 mm; no usar la config de fase 1 para imprimir |
| R6 | Lectura de cama sin la corrección de Creality | Límite de 115 °C de stock mantenido; en fase 1 no pasar de 60 °C |
| R7 | Moonraker de stock (`dde9bcc`) frente a la API de Kalico | Escalón 3 separado y opcional |
| R8 | `pgrep -f`, `tar -tzf`, `sha256sum -c` de busybox se comportan distinto que en el autotest | `--dry-run` primero; el paso 0 lista las herramientas |

### 8.1 Resultado del paso 0 (2026-11-10)

Ejecutado por el usuario en la Hi, solo lectura. Datos comunicados por el hilo que guía la fase 1; salida saneada
en `data/captures/2026-11-10_hi-step0/step0.txt` [P salvo donde se indica].

| Sección | Resultado |
| - | - |
| — | `hi_install.sh --dry-run` del paquete: correcto (salida 0), 4,3 GB libres frente a 26 MB necesarios, nada escrito salvo 3 ficheros en `/tmp` (`install-dryrun.txt`) |
| Escalón 1 | Instalado en `/mnt/UDISK/kalico-hi` con aprobación del usuario: 299 ficheros coinciden con `SHA256SUMS`, `c_helper.so` carga (armv7l, Python 3.9.12, glibc 2.29), enlace cffi correcto, 16 `.cfg` copiados (`install.txt`). `hi_kalico.sh start --dry-run` lee `standby` y lista parar `app` y `klipper` y lanzar Kalico (`start-dryrun.txt`) |
| 01 | F018, firmware 1.1.0.60. `board=CR4NU200360C21` (la documentación decía `C20`); stock la trata igual: el arranque compara con el prefijo `CR4NU200360C2` [verificado: OTA:etc/init.d/klipper, `copy_config`, caso `F018`] |
| 02 | Slot activo **B**, libre A. `bootcmd` usa `setargs_nand` (ubiblock), pero la línea de arranque real es `root=/dev/mmcblk0p7`: hay que aclararlo antes de usar §9 |
| 03 | eMMC `mmcblk0` con los nombres esperados en `/dev/by-name` (no SPI NAND, como decía `hardware.md` [F]) |
| 04 | `/` es overlay (capa superior en `mmcblk0p10`, 233 MB libres); `UDISK` con 4,2 GB libres; 500 MB de RAM |
| 05, 06 | Dos núcleos Cortex-A7 con `neon` y `vfpv4`; Python 3.9.12 y bibliotecas en las versiones del plan; solo falla `can` |
| 08 | `c_helper.so` (SHA-256 `80db4330…a9ad0`, igual en PC y Hi) carga con glibc 2.29. Se compiló desde `dev` (`5b944e9`); para el paquete se recompila desde la rama del PR #2 |
| 09 | Faltan además `timeout` y `unsquashfs`; hay `start-stop-daemon`, `flock`, `rsync`, `strace`, `fw_setenv`. Los scripts `hi_*.sh` no usan `timeout` [verificado: búsqueda en scripts/hi_*.sh; solo lo lista hi_step0.sh:98] |
| 11 | `mcu0_110_G32-mcu0_020_000` y `noz0_110_G30-noz0_019_000`, como en `hardware.md`; cama `bed0_110_G21-bed0_017_000` |
| 12 | El `klippy.log` de stock no tiene líneas `Stats`: no hay referencia de `sysload` para el paso 11 del escalón 2. Carga en reposo: `0.23 0.52 0.53` |
| 13 | Sin paquetes marcados `MODIFIED` |
| Escalón 2, arranque | `hi_kalico.sh start` con aprobación del usuario, impresora fría y en `standby`: Kalico `v2026.11.00-57-g61602f77` llega a `ready` con las tres MCU configuradas (`mcu` gd32f303xe 117 órdenes, `nozzle_mcu` gd32f303xb 113, `bed_mcu` gd32e230x8 94). Boquilla 29,3 °C, cama 25,6 °C, `mcu_temp` 35,2 °C, ventiladores a 0. Capturas en `data/captures/2026-11-10_kalico-start/` |
| Escalón 2, pasos 5 y 6 | `DUMP_TMC`: `stepper_z`, `stepper_z1` y `extruder` responden por UART (TMC220x, `IOIN` versión `0x20`), sin avisos de temperatura ni cortos; `GSTAT reset=1` es la marca de encendido. `QUERY_ENDSTOPS` en reposo: todo a 0. Con cartulina: sensor **izquierdo** activa `z` (`PB15`), sensor **derecho** activa `z1` (`PB14`); 1 = tapado, sin cruces |
| Escalón 2, paso 7 | `M106 S128`: `power` 0,35, `speed` 0,25 (reescalado previsto en §3.1); los ventiladores de capa giran y `M107` los para. `hotend_fan` a 0 en frío; `rpm` nulo (sin tacómetro configurado). `aux_fan` respondía en `PB2`, pero la Hi no tiene ese ventilador: quitado de la config |
| Escalón 2, paso 8 | Boquilla a 50 °C: de 29 a 51,7 °C en 10 s, pico 56,0 °C (6 °C de sobrepaso), 52,4 °C a los 42 s; `hotend_fan` se enciende al pasar de 50 °C. Cama a 40 °C: 26,7 a 40,2 °C en 182 s, máximo 40,5 °C, sin `verify_heater`. Lectura de cama sin la corrección de Creality (R6) |
| Escalón 2, paso 9 | `SET_KINEMATIC_POSITION Z=50 SET_HOMED=z` y `G1 Z5 F300` en relativo: los dos lados del puente suben a la vez; `G1 Z-5` los baja a la vez. Sentido de `stepper_z` y `stepper_z1` correcto. Incidencia: se ejecutó un `FORCE_MOVE STEPPER=stepper_z1 DISTANCE=-2` suelto por una impresión visual equivocada; el lado derecho queda 2 mm más bajo hasta deshacerlo con `DISTANCE=2` o hasta la próxima alineación de stock |

Sobrepaso de la boquilla: el PID es el de stock (`26.978 / 2.725 / 66.770`) [verificado: K:config/hi/base.cfg
frente a captura:toolhead.cfg:27-30], ajustado para temperaturas de impresión; con una consigna de 50 °C el
calentador satura toda la subida y la inercia hace el resto. Que stock sobrepase igual es [supuesto: repetir la
misma consigna en stock]. Antes de ir a 200 °C se sube por escalones (120, 200) mirando el pico;
`PID_CALIBRATE` queda como opción si el pico a 200 °C pasa de unos 5 °C.

Primer arranque de Kalico en la Hi [P]: las MCU conservaban la configuración del Klipper de stock, así que Kalico
detecta `CRC mismatch`, reinicia las tres con `restart_method = command` y vuelve a empezar 11 s después. En ese
segundo intento `mcu` tarda en responder y el registro deja dos `Timeout on connect` con su traza (`No
communication with MCU`) antes de identificarse. Es el riesgo R3 previsto y no un fallo: después
`bytes_invalid=0`, `bytes_retransmit=63` constante y `send_seq` igual a `receive_seq`. Pasará en cada conmutación
desde stock [supuesto: confirmarlo con un segundo `start` tras `stop`].

Otros hallazgos:

- El overlay contiene cambios en `moonraker`, `frontend`, `klippy-env` y 31 ficheros en `printer_data/config`.
  En `/usr/share/klipper` solo cambia `klippy/extras/cfs_materials.py` (y su `.pyc`): el `klippy/` que corre es
  el de la OTA leída en [phase6-plan.md §3](phase6-plan.md) salvo ese fichero [P].
- `mcu_update.log` lista los esclavos RS-485 que ve `mcu_util_485`, el binario cerrado que `mcu_update` lanza en
  el arranque (S13, antes de Klipper) tras enviar `F7 EB 03 FF 56 CF` a 230400 baudios por `/dev/ttyS5`
  [verificado: OTA:etc/init.d/mcu_update:9, 223-226] [P]:

  | Dirección | Versión |
  | - | - |
  | `[85]` | `mot2_033_C30-mot2_002_071` |
  | `[86]` | `mot2_023_C30-mot2_002_071` |
  | `[11]` | `rfd0_010_G21-rfd0_000_009` (`dev: rfid`) |
  | `[01]` | `cfs0_050_G32-cfs0_000_113` |

  Los dos drivers tienen hardware distinto (`033` y `023`) y el mismo firmware `002_071`. En Klipper responden
  en `0x81`/`0x82` [P, hardware.md]; que `[85][86]` sean sus direcciones antes de que Klipper las reasigne con
  los pines `DIR`/`STEP` es [supuesto: `READ_ADDR` con `tools/hi_probe.py` justo tras el arranque, con Klipper
  parado]. También registra `Fail to Open /usr/share/klipper/fw/F018/rfid!`: no hay firmware de `rfid` en la
  imagen y la actualización se da por hecha.
- Paquete de la fase 1 generado el 2026-11-10 desde el fork `61602f77b6d0`: `kalico-hi-61602f77b6d0.tar.gz`,
  929113 bytes, SHA-256 `2d8ca01e0c3893a79804c8281a06cdd01402267dd931c2a20cc7a0239282d183`; el `c_helper.so`
  recompilado desde esa rama tiene el mismo SHA-256 que el anterior [P, PC del usuario].

## 9. Slot A/B y vuelta a stock más adelante

No forma parte de la fase 1. Queda como diseño para cuando Kalico imprima:

- Reempaquetar el SquashFS de stock con un servicio `kalico` en lugar de `klipper` y escribirlo con `kernel` en
  el slot inactivo usando el `swupdate` de stock y un `sw-description` propio. El formato solo lleva MD5 por
  fichero [verificado: OTA:cpio_item_md5] y `swupdate` no muestra cadenas de verificación de firma
  [supuesto: probar con una imagen que cambie un único fichero inocuo].
- Cambiar de slot: `fw_setenv boot_partition bootB` y `fw_setenv root_partition rootfsB` (o A), las mismas dos
  variables que escribe una OTA [verificado: OTA:sw-description:36-41]. **Documentado, no ejecutado.**
- Antes de usarlo hay que saber qué hace U-Boot si el slot no arranca (paso 0, sección 02) y tener acceso a la
  consola serie `ttyS0` [verificado: docs/hardware.md:22] como recuperación.
- Como el overlay es común, el SquashFS reempaquetado debe distinguir el slot por contenido propio (su
  `/etc/rc.d`), y el overlay no debe contener copias de esos ficheros.
- No se publican imágenes: el instalador las construiría en el PC del usuario a partir de su OTA.

## 10. Decisiones

Aprobadas el 2026-11-10 y registradas en [decisions.md](decisions.md): instalación escalonada sin escribir en
flash (§5.3, D5), `c_helper.so` como artefacto del paquete de instalación (§6, D6) y consola SSH seguida de
Fluidd como interfaz (§5.3, D7).

Tomadas por defecto, reversibles (se pasarán a [decisions.md](decisions.md) al aprobarse):

- Usar las bibliotecas Python de stock de la Hi en lugar de las versiones de `pyproject.toml` (§2).
- X/Y declarados y bloqueados en la config mínima (§7.1).
- Compilador cruzado de Ubuntu 18.04 (§4).
- El instalador usa un `.tar.gz` y no `git clone`, porque la Hi no tiene `git` (corrige la consecuencia de D3).

Opcional, necesita tu permiso expreso: ejecutar el `python3.9` del rootfs de stock con `qemu-user` en un
contenedor sin red para repetir estas pruebas con los binarios reales de la Hi. Hoy lo impide la regla "nunca
ejecutar firmware extraído" de `CLAUDE.md`. El paso 0 cubre lo mismo en la impresora.
