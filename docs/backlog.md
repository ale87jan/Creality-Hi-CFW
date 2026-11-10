# Backlog

Tareas pequeñas y autocontenidas, pensadas para ejecutarse sin el contexto de la conversación que las creó.
Antes de empezar una: leer [ESTADO.md](ESTADO.md) y la sección citada de [phase1-plan.md](phase1-plan.md).
Al terminar: marcarla aquí, actualizar `ESTADO.md` y, si procede, [roadmap.md](roadmap.md).

Reglas que valen para todas: nada se escribe en la impresora sin aprobación expresa del usuario; las pruebas en
ella las ejecuta el usuario; cada dato nuevo en docs lleva su origen ([P], [F], [I] o `[verificado: …]` /
`[supuesto: …]`).

Tipo: **U** la ejecuta el usuario en su PC o impresora; **M** la puede hacer un modelo en la nube.

## Bloqueantes de la fase 1

### B01 — Subir las ramas y abrir los pull request · U+M

- **Objetivo:** que el trabajo de `claude/project-thread-fnrqje` esté en GitHub y en revisión hacia `dev` en los
  dos repos.
- **Estado:** ramas subidas y PR abiertos el 2026-11-10. Queda la revisión del usuario y el CI.
- **Hecho cuando:** hay un PR abierto por repo y el CI del fork (`ci-build_test`, `ci-lintformat`) termina.
- **Riesgos:** el CI del fork está en rojo por fallos heredados de `dev` (ver B07); no los
  introduce esta rama.

### B02 — Ejecutar el paso 0 y analizar la salida · U, después M

- **Objetivo:** confirmar en la impresora los supuestos del plan.
- **Ficheros:** `scripts/hi_step0.sh`, `scripts/chelper_load.py`, `build/chelper/c_helper.so` (lo genera
  `scripts/build_chelper.sh`); salida en `data/captures/2026-11-09_hi-v1.1.0.60/step0.txt`.
- **Pasos:** los de [phase1-plan.md §8, "Paso 0"](phase1-plan.md). El modelo compara cada sección con la tabla de
  valores esperados y cambia en el plan cada `[supuesto: …]` resuelto por `[P]`.
- **Hecho cuando:** `step0.txt` está en el repo y el plan no tiene supuestos de las secciones 02, 04, 06, 08, 09
  y 13 sin resolver.
- **Riesgos:** ninguno para la impresora (solo lectura). Revisar que el fichero no lleve datos personales.

### B03 — Compilar con prueba de carga en Docker Desktop · U

- **Objetivo:** ejecutar el objetivo `loadtest` del Dockerfile, que en la nube no se pudo.
- **Ficheros:** `scripts/build_chelper.sh`, `scripts/Dockerfile.chelper`.
- **Pasos:** `scripts/build_chelper.sh <ruta a Creality-Hi-Kalico>` (sin `--no-loadtest`), desde WSL o Git Bash.
- **Hecho cuando:** `build/chelper/loadtest.txt` empieza por `OK:` y el SHA-256 de `c_helper.info` coincide con
  el de [phase1-plan.md §4](phase1-plan.md) si los fuentes de `klippy/chelper` no han cambiado.
- **Riesgos:** en Git Bash las rutas de `docker build` pueden necesitar `MSYS_NO_PATHCONV=1`.

### B04 — Registrar las decisiones aprobadas · M

- **Objetivo:** pasar a [decisions.md](decisions.md) las decisiones de [phase1-plan.md §10](phase1-plan.md) según
  responda el usuario (P1, P2, P3 y las cuatro tomadas por defecto), como D5 en adelante.
- **Hecho cuando:** `decisions.md` las recoge con contexto, decisión y consecuencias; §10 del plan apunta a
  ellas; si alguna respuesta no es la recomendada, hay tareas nuevas aquí para el cambio.
- **Riesgos:** no registrar como decisión nada que el usuario no haya aprobado.

### B05 — Instalar y arrancar Kalico en una sesión · U, después M

- **Objetivo:** recorrer los pasos 1 a 13 de [phase1-plan.md §8](phase1-plan.md).
- **Depende de:** B02 sin incidencias y aprobación expresa del usuario para cada bloque (1-2, 3-7, 8-11, 12-13).
- **Ficheros:** `build/kalico-hi-<commit>.tar.gz` y `.sha256` (de `scripts/make_bundle.sh`),
  `scripts/hi_install.sh`; resultados en `data/captures/<fecha>_kalico-fase1/` (`klippy.log`, salidas pegadas).
- **Hecho cuando:** cada paso tiene resultado anotado en el plan y `roadmap.md` marca la fase 1 según lo obtenido.
- **Riesgos:** los de la tabla de riesgos del plan (R1 a R8). Ante cualquier duda: `hi_kalico.sh stop` o reiniciar.

## Mejoras de lo ya hecho

### B06 — CI de este repo · M

- **Objetivo:** un workflow de GitHub Actions en pull request que ejecute `scripts/selftest.sh`,
  `python -m unittest discover -s tools/tests`, `shellcheck -s sh scripts/hi_*.sh` y
  `ruff format --check --line-length 79 scripts/*.py`.
- **Ficheros:** `.github/workflows/ci.yaml` (nuevo).
- **Hecho cuando:** el workflow pasa en un PR. `selftest.sh` necesita `gcc`, `python3` y `busybox`.
- **Riesgos:** ninguno.

### B07 — El CI del fork está en rojo en `dev` · M

- **Objetivo:** que los checks de pull request (`ruff`, `Test Klippy`) pasen en el fork.
- **Contexto:** comprobado el 2026-11-10 en el pull request Creality-Hi-Kalico #2 y reproducido en `origin/dev`
  sin los cambios de la Hi. Tres causas, todas heredadas del fork de la K2:
  1. `ruff` 0.15.22: 13 errores de `ruff check` y 24 ficheros sin formatear, todos en `klippy/extras/` (módulos
     de la K2: `box*.py`, `motor_control.py`, `homing.py`, `z_align.py`...). `dev` da exactamente lo mismo.
  2. 72 tests `test/klippy/*.test` fallan con `Internal error on command:"G28"`: `klippy/extras/homing.py:590`
     hace `lookup_object("motor_control")` sin condición y cualquier config sin `[motor_control]` cae al hacer
     homing [verificado: batch con una config cartesiana mínima sobre `origin/dev`].
  3. `test/test_imports.py::test_import_extra`: `klippy/extras/cartographer.py` hace
     `from cartographer.extra import *`, un paquete externo.
  Los tests de la Hi (`test/test_hi_config.py`) pasan en el CI.
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/homing.py`, `klippy/extras/cartographer.py`, y el formateo de
  `klippy/extras/`.
- **Propuesta:** (2) hacer opcional `motor_control` en `homing.py` (`lookup_object("motor_control", None)` y
  saltar los pasos de la K2 si no existe); hace falta igualmente para el homing de Z en la Hi antes de portar
  `motor_control` (ver B15). (3) import protegido en `cartographer.py`. (1) `ruff format` + `ruff check --fix` en
  un commit aparte. Comprobar antes si el CI del fork de Jacob falla igual y si acepta los cambios upstream.
- **Decisión del usuario (2026-11-10):** no tocar `cartographer.py`. El fallo de `homing.py` no afecta a la Hi:
  en la fase 1 `[homing_override]` sustituye al `G28` y desde la fase 2 la config tendrá `[motor_control]`; solo
  haría falta para hacer homing de Z antes de portar `motor_control`. El CI se deja en rojo por ahora: el PR #2 se revisa así.
- **Hecho cuando:** `ruff` y `Test Klippy` pasan en un pull request hacia `dev`, sin saltar tests.
- **Riesgos:** (1) toca 24 ficheros compartidos y complica los merges con upstream: decisión del usuario.
  (2) cambia el camino de homing de la K2: probar con `[motor_control]` presente.

### B08 — Ejecutar `test/klippy/*.test` con las versiones de la Hi · M

- **Objetivo:** completar la validación de [phase1-plan.md §3.2](phase1-plan.md).
- **Contexto:** hacen falta los diccionarios `dict/*.dict` de la imagen `ghcr.io/kalicocrew/kalico-ci`
  (`docker run --rm --entrypoint tar <imagen> -C /ci_build -c dict | tar -x`), y un entorno Python 3.9 con
  cffi 1.14.6, greenlet 1.0.0, numpy 1.20.1, Jinja2 3.0.3, MarkupSafe 2.1.0, pyserial 3.4.
- **Hecho cuando:** el resultado (pasan/fallan y por qué) está en §3.2.
- **Riesgos:** ninguno.

### B09 — Corrección de temperatura de la cama · M

- **Objetivo:** decidir cómo reproducir en Kalico la tabla `adc_temp_list` / `actual_temp_list` de stock.
- **Contexto:** [phase1-plan.md §7.2](phase1-plan.md). Leer cómo la aplica el `heaters.py` de stock (rootfs de la
  OTA, `usr/share/klipper/klippy/extras/heaters.py`, opción `temp_offset_flag`).
- **Opciones a valorar:** termistor a medida (`[thermistor]` con tres puntos), o módulo propio en `plugins/`.
- **Hecho cuando:** hay propuesta con opciones y ejemplo para el usuario. No cambiar la config sin su aprobación.
- **Riesgos:** una corrección mal aplicada falsea la temperatura real de la cama.

### B10 — Moonraker de stock con Kalico · M, después U

- **Objetivo:** saber si el Moonraker `dde9bcc` de stock funciona contra Kalico (escalón 3) y qué carpeta de
  config enseña Fluidd.
- **Ficheros:** rootfs de la OTA `usr/share/moonraker/` (leer `klippy_connection.py`, `moonraker.conf`);
  `scripts/hi_kalico.sh` (opción `--ui`).
- **Hecho cuando:** [phase1-plan.md §5.3](phase1-plan.md) indica qué endpoints usa y si hace falta apuntar
  `[file_manager]` a `/mnt/UDISK/kalico-hi/config`; paso 13 probado por el usuario.
- **Riesgos:** Moonraker de stock es un fork de Creality; puede pedir objetos que Kalico no tiene.

### B11 — Comprobar el riesgo R3 en stock · U

- **Objetivo:** confirmar que un `FIRMWARE_RESTART` del Klipper de stock vuelve a `ready` sin reiniciar la
  impresora.
- **Pasos:** en Fluidd de stock, con la impresora en reposo, `FIRMWARE_RESTART`; esperar 30 s.
- **Hecho cuando:** el resultado está anotado en R3 del plan.
- **Riesgos:** bajo; es una orden normal de Klipper.

### B12 — Actualizar los `CLAUDE.md` · M

- **Objetivo:** que la tabla de rutas de `CLAUDE.md` de este repo incluya `scripts/`, `docs/phase1-plan.md`,
  `docs/backlog.md` y `docs/ESTADO.md`, y que el del fork mencione `config/hi/` y `test/test_hi_config.py`.
- **Hecho cuando:** ambos ficheros lo recogen. Proponer el texto al usuario antes de cambiar reglas.
- **Riesgos:** ninguno.

## Después de que la fase 1 funcione

### B13 — Servicio persistente de Kalico · M

- **Depende de:** decisión P1 y B05.
- **Objetivo:** diseñar el arranque automático (script procd propio y selector de arranque) con vuelta a stock
  por fichero-bandera en `/mnt/UDISK`, sin modificar los scripts de stock.
- **Hecho cuando:** hay diseño con opciones en `docs/` y aprobación del usuario antes de escribir nada en el
  overlay.
- **Riesgos:** el overlay es común a los dos slots ([phase1-plan.md §5.2](phase1-plan.md)).

### B14 — Diseño de la instalación en el slot A/B libre · M

- **Depende de:** B02 (variables de U-Boot y tipo de almacenamiento).
- **Objetivo:** convertir [phase1-plan.md §9](phase1-plan.md) en un procedimiento con comprobaciones, incluida la
  recuperación por consola serie.
- **Hecho cuando:** documento con procedimiento, prueba inocua propuesta y plan de vuelta a stock, aprobado por
  el usuario. `fw_setenv` solo documentado.
- **Riesgos:** un slot que no arranca sin vuelta automática deja la impresora sin acceso por red.

### B15 — Fase 2: decisiones de diseño · U

- **Objetivo:** cerrar las cuatro decisiones de [phase2-plan.md §9](phase2-plan.md) y anotarlas en
  [decisions.md](decisions.md).
- **Hecho cuando:** las decisiones están en `decisions.md` y el plan deja de decir "pendiente".
- **Estado:** decisión 1 cerrada (D8, copia aparte) y dato de los finales de carrera recibido. Decisiones 2
  y 3 cerradas (D9 niveles, D10 solo X/Y). Tarea terminada.
- **Riesgos:** B16 a B20 dependen de la decisión 2.

### B16 — Fase 2: `motor_control_hi.py` · M

- **Estado:** hecho el 2026-11-10 (fork, commit `feat(motor): add closed-loop X/Y module for the Hi`), con el
  nivel por defecto `none`. Sin probar en la impresora.

- **Objetivo:** copia recortada de `motor_control.py` para la Hi (D8, [phase2-plan.md §6](phase2-plan.md)):
  solo X/Y, sin motor E ni túnel, pines de stall y `startup_writes` por config, direcciones de stock.
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/motor_control_hi.py`, `test/test_hi_motor_control.py`.
- **Hecho cuando:** `motor_control.py` no cambia; con la config de la Hi no se registra `config_transparent`, los
  pines de stall son `PA8`/`PA6`, las direcciones son 0x81/0x82 y con `startup_writes: none` no sale ninguna
  trama de escritura aunque la config traiga claves de parámetros (test con el bus simulado de B17);
  `homing.py` encuentra el objeto `motor_control`.
- **Riesgos:** los arreglos de upstream no llegan solos; anotar en la cabecera el commit de origen de la copia.

### B17 — Fase 2: bus RS-485 simulado para tests · M

- **Estado:** hecho el 2026-11-10 como `FakeMotorBus` dentro de `test/test_hi_motor_control.py`; prueba las
  clases sin el reactor. Falta un test del arranque completo con temporizadores.

- **Objetivo:** un `serial_485` de prueba que responda `READ_ADDR`, `PROTECTION 0B`, `GET` y `SYS_PARAM 02` con
  los valores de `data/captures/2026-11-09_hi-v1.1.0.60/motors.json` y registre todas las tramas enviadas.
- **Ficheros:** Creality-Hi-Kalico `test/hi/fake_rs485.py`.
- **Hecho cuando:** un test arranca `motor_control` en batch contra el bus simulado y comprueba la lista exacta
  de tramas.
- **Riesgos:** el modo batch de klippy no ejecuta temporizadores igual que en real; puede hacer falta probar las
  clases sin el reactor.

### B18 — Fase 2: portar `io_remap.py` · M

- **Estado:** hecho el 2026-11-10 en el fork (`klippy/extras/io_remap.py`, `test/test_hi_io_remap.py`); falta
  probarlo en la impresora (paso 2.4).
- **Objetivo:** módulo `[io_remap]` de la Hi en Kalico ([phase2-plan.md §4](phase2-plan.md)).
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/io_remap.py`; origen `klippy/extras/io_remap.py` de la OTA
  V1.1.0.60 (GPL).
- **Hecho cuando:** carga en batch con `test/hi/nozzle_mcu.dict` y emite `config_ioRemap` con los valores de la
  captura.
- **Riesgos:** el reenvío se activa solo durante el homing de X (`homing_stepper`), como en stock; falta verlo
  en la impresora (paso 2.4).

### B19 — Fase 2: config de la Hi con X/Y · M

- **Estado:** hecho el 2026-11-10 como `config/hi/phase2.cfg`. En batch no hay bus, así que solo se comprueba
  que carga y que rechaza `G28`, `G28 Z` y los movimientos sin homing; el homing real queda para el paso 2.6.

- **Objetivo:** `config/hi/` con `[serial_485]`, `[motor_control]` sin claves de parámetros, `[io_remap]`,
  endstops de stock y `[homing_override]` que solo deja pasar X e Y.
- **Ficheros:** Creality-Hi-Kalico `config/hi/printer.cfg`, `config/hi/motor_control.cfg`,
  `test/test_hi_config.py`.
- **Hecho cuando:** valida en batch; `G28 Z` se rechaza; `G28 X Y` genera pasos solo en X e Y.
- **Riesgos:** depende de B16 y B18.

### B20 — Fase 2: lecturas previas en la impresora · U, después M

- **Objetivo:** pasos 2.1 y 2.2 de [phase2-plan.md §8](phase2-plan.md): qué pin es cada final de carrera y qué
  hace el modo de stall 1.
- **Ficheros:** `tools/hi_probe.py` (ampliar, solo lectura); salida en `data/captures/`.
- **Hecho cuando:** las dos preguntas están respondidas con [P] en `docs/hardware.md`.
- **Riesgos:** ninguna escritura; el homing del paso 2.2 es el de stock.

### B21 — Fase 3: decisiones de diseño · U

- **Objetivo:** cerrar las tres decisiones de [phase3-plan.md §7](phase3-plan.md) y anotarlas en
  [decisions.md](decisions.md).
- **Hecho cuando:** están en `decisions.md`.
- **Riesgos:** B22 depende de la decisión 1; el orden de B22 y la fase 4, de la 2.

### B22 — Fase 3: config y test en batch de la sonda · M · HECHO 2026-11-10

- **Hecho:** `config/hi/phase3.cfg` (`[prtouch]` con los valores de `[prtouch_v3]` de la impresora,
  `home_xy: 130, 130`, Z y Z1 con `probe:z_virtual_endstop`, `NOZZLE_CLEAN` vacía, `PC7` en
  `[duplicate_pin_override]`) y `test/test_hi_prtouch.py` (5 tests). Para poder quitar los finales de carrera
  provisionales de Z, `config/hi/` se repartió en `base.cfg` (MCU, motores, calentadores, ventiladores) y
  `motors.cfg` (bus y drivers X/Y); `printer.cfg`, `phase2.cfg` y `phase3.cfg` los combinan. La salida
  decodificada hacia las MCU de `printer.cfg` y `phase2.cfg` es idéntica a la de antes.
- **Consecuencia:** el paquete lleva ahora todos los `.cfg` (`make_bundle.sh`), `hi_install.sh` los instala uno
  a uno sin pisar los existentes, y `HI_CONFIG=phase2.cfg hi_kalico.sh start` elige la config.
- **Pendiente:** el usuario no ha confirmado en la tarjeta la decisión 1 (módulo de la K2 tal cual); la config
  asume esa opción.

### B23 — Fase 3: leer entera la lógica de `prtouch.py` · M

- **Objetivo:** revisar armado, disparo, reintentos y limpieza (`_arm`, `_disarm`, `home_start`, `home_wait`,
  `probing_move`) contra lo que se sabe del protocolo, y documentar qué pasa si la sonda no dispara.
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/prtouch.py:401-760`; `docs/phase3-plan.md`.
- **Hecho cuando:** el plan tiene una sección "modos de fallo" con referencias a línea.
- **Riesgos:** ninguno; solo lectura.

### B24 — Fase 3: pruebas en la impresora · U, después M

- **Objetivo:** pasos 3.1 a 3.5 de [phase3-plan.md §6](phase3-plan.md).
- **Hecho cuando:** `G28 Z` y `PROBE` repetibles, con Z=0 comparable al de stock; resultados [P] en
  `docs/hardware.md`.
- **Riesgos:** choque con la cama; seguir el orden y las condiciones del plan.

### B25 — Fase 4: decisiones de diseño · U

- **Objetivo:** cerrar las tres decisiones de [phase4-plan.md §10](phase4-plan.md) y anotarlas en
  [decisions.md](decisions.md).
- **Hecho cuando:** están en `decisions.md`.
- **Riesgos:** B26 depende de la decisión 1; la decisión 3 espera a B27.

### B26 — Fase 4: `z_align_hi.py` con tests · M

- **Objetivo:** módulo de alineación de los dos Z para la MCU de la Hi (`query_z_align` sin `safeDist`, sin
  `z_align_force_stop`), según la decisión 1, sin los parches de Creality de
  [phase4-plan.md §3](phase4-plan.md).
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/z_align_hi.py`, `config/hi/phase4.cfg`,
  `test/test_hi_z_align.py`.
- **Hecho cuando:** en batch emite `config_z_align(_add)` y `config_z_align_up(_add)` con `PB15`/`PB14` y los
  pines de Z y Z1, y `ZDOWN` envía `query_z_align` con los ticks de los valores de stock; un test con MCU
  simulada cubre reintentos y `timeout`.
- **Riesgos:** polaridades `zd_up`/`zes_untrig`; no existe sustituto de `ADJUST_STEPPERS`.

### B27 — Fase 4: leer `NOZZLE_CLEANUP` y `PRTOUCH_SCRUB` · M

- **Objetivo:** saber si alguna de las dos limpiezas del fork se puede configurar para la zona de limpieza de
  la Hi (`start_pos: 98, 266`) o hay que reescribir `nozzle_clear.py`.
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/nozzle_cleanup.py`, `klippy/extras/prtouch.py`
  (`cmd_PRTOUCH_SCRUB`); `docs/phase4-plan.md` §4.
- **Hecho cuando:** el plan tiene la comparación y una recomendación para la decisión 3.
- **Riesgos:** ninguno; solo lectura.

### B28 — Fase 4: limpieza de boquilla · M

- **Objetivo:** `NOZZLE_CLEAN` real según la decisión 3, con la secuencia de stock
  (`nozzle_clear.py:84-167`) como especificación.
- **Hecho cuando:** carga en batch y genera los movimientos esperados dentro de la zona de limpieza.
- **Riesgos:** depende de la fase 3 probada en la Hi; calienta la boquilla y toca la cama.

### B29 — Fase 4: pruebas en la impresora · U, después M

- **Objetivo:** pasos 4.1 a 4.5 de [phase4-plan.md §9](phase4-plan.md).
- **Hecho cuando:** `G28` completo con alineación, con `deltaError1` y `zmax` comparables a los de stock;
  resultados [P] en `docs/hardware.md`.
- **Riesgos:** la MCU no se puede parar durante `ZDOWN`; empezar con la cama cerca del fondo.

### B30 — `bl24c16f` y `tmc_line_check` · M, sin fecha

- **Objetivo:** portarlos solo si hacen falta (recuperación tras corte de luz; diagnóstico de cables de Z).
  `timer_read` no se porta. Pendiente de la decisión 2 de la fase 4.
- **Riesgos:** los comandos `EEPROM_WRITE_*` escriben en una memoria que también usa el stock.

### B31 — Fase 5: clasificar las tramas del CFS · M

- **Objetivo:** tabla de las tramas de `box_protocol.py` y `box_addr.py` (lectura, escritura volátil, escritura
  persistente, movimiento) en `docs/protocols/rs485.md`, y herramienta de solo lectura para el paso 5.2.
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/box_protocol.py`, `box_addr.py`; Creality-Hi-CFW
  `docs/protocols/rs485.md`, `tools/`.
- **Hecho cuando:** cada trama tiene clase y referencia a línea; la herramienta solo envía las de lectura y
  tiene test sin impresora.
- **Riesgos:** ninguno; solo lectura.

### B32 — Fase 5: leer la lógica de `box.py` y `box_change.py` · M

- **Objetivo:** secuencias de carga, descarga, corte, purga y cambio; qué parte es geometría de la K2 y qué
  hace `box.py` al arrancar. Con ello, recomendación para la decisión 1 de [phase5-plan.md §6](phase5-plan.md).
- **Hecho cuando:** el plan tiene las secuencias con referencias a línea y la recomendación.
- **Riesgos:** ninguno; solo lectura. Es larga (unas 5000 líneas).

### B33 — Fase 5: decisiones de diseño · U

- **Objetivo:** cerrar las tres decisiones de [phase5-plan.md §6](phase5-plan.md).
- **Hecho cuando:** están en `decisions.md`.
- **Riesgos:** la 1 depende de B32.

### B34 — Fase 5: CFS para la Hi con tests · M

- **Objetivo:** adaptación según la decisión 1: pin del sensor de corte configurable, corte en +X y purga de la
  Hi; `config/hi/phase5.cfg` con los valores de stock.
- **Hecho cuando:** carga en batch; un test rechaza `PB9` como sensor y otro comprueba que el corte no sale de
  los límites de X de la Hi.
- **Riesgos:** depende de las fases 2 a 4 probadas.

### B35 — Fase 5: pruebas en la impresora · U, después M

- **Objetivo:** pasos 5.1 a 5.6 de [phase5-plan.md §5](phase5-plan.md).
- **Hecho cuando:** cambio de color completo sin intervención; resultados [P] en `docs/hardware.md`.
- **Riesgos:** golpe en el corte; purga fuera de sitio.

### B36 — Fase 6: equivalencias de los comandos de Creality · M

- **Objetivo:** leer en el stock qué hace cada comando de [phase6-plan.md §3](phase6-plan.md) y `[custom_macro]`,
  y fijar su equivalente en Kalico.
- **Ficheros:** stock `klippy/` (solo lectura); `docs/phase6-plan.md` §3.
- **Hecho cuando:** ninguna fila de la tabla queda como supuesto.
- **Riesgos:** algunos comandos pueden estar en `.so` cerrados.

### B37 — Fase 6: `config/hi/` por subsistemas · M

- **Objetivo:** un fichero por subsistema (`printer.cfg`, `motor_control.cfg`, `prtouch.cfg`, `macros.cfg`...),
  como `config/k2/`. Empezado en B22 (`base.cfg`, `motors.cfg`); falta sacar la sonda de `phase3.cfg` a su
  fichero cuando exista la config de uso diario.
- **Hecho cuando:** los tests en batch de las fases 1 y 2 pasan con la nueva estructura.
- **Riesgos:** cambia rutas que usan `hi_kalico.sh` y el plan de la fase 1; actualizar los dos.

### B38 — Fase 6: decisiones y macros de impresión · U, después M

- **Objetivo:** cerrar las decisiones de [phase6-plan.md §6](phase6-plan.md) y escribir las macros de impresión.
- **Hecho cuando:** `tools/cfg_commands.py` sobre `config/hi/` no encuentra comandos ausentes y hay test en
  batch de `START_PRINT` y `END_PRINT`.
- **Riesgos:** depende de las fases 2 a 5.

### B39 — Fase 6: instalador, pantalla y documentación · U

- **Objetivo:** paquete `.tar.gz` con SHA-256, arranque automático (decisión 3), sustituto de la pantalla y web
  de documentación. Sin analizar.
- **Riesgos:** el arranque automático escribe en el sistema; necesita vuelta a stock probada.

