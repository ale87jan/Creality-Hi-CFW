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

### B15 — Fase 2: preparar el port de `motor_control` · M

- **Objetivo:** dividir en tareas de este tamaño los puntos de la fase 2 de [roadmap.md](roadmap.md)
  (`STALL_PIN_LAYOUT`, `PIN_DIR_SEQUENCE`, quitar E/Z/Z1 del descubrimiento, homing por stall).
- **Ficheros:** Creality-Hi-Kalico `klippy/extras/motor_control.py`, `klippy/extras/homing.py`;
  `docs/protocols/rs485.md`.
- **Hecho cuando:** hay tareas B con objetivo, ficheros, criterio y riesgos, y tests en modo batch previstos.
- **Riesgos:** las reglas de seguridad de motores de `CLAUDE.md` (nunca escribir parámetros sin aprobación).
