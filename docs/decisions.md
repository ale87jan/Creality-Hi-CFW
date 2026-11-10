# Decisiones

Registro de decisiones de diseño. Cada entrada: contexto, decisión y consecuencias.

## D1 — Base del host: Kalico de Jacob10383 (2026-11-09)

**Contexto.** Opciones: Klipper oficial, Kalico (KalicoCrew) o el fork de Kalico de
[Jacob10383/kalico](https://github.com/Jacob10383/kalico) que usa el CFW de la K2 Plus.

**Decisión.** Partir del fork de Jacob10383.

**Motivos.**

- Ya funciona sobre hardware hermano (mismo SoC, MCU, bus RS-485, motores, sonda y CFS).
- Lleva cambios de núcleo que necesitan los módulos de Creality: `homing.py` llama a `motor_control` para el modo
  de stall; `lis2dw.py` tiene compatibilidad con el protocolo antiguo de las MCU de Creality; `fan_feedback.py` y
  `power_loss_recovery.py` dependen de esos módulos.
- La compatibilidad con las MCU de la Hi se verificó contra este fork ([protocols/mcu.md](protocols/mcu.md)).
- Kalico exige Python ≥ 3.9 y la Hi trae 3.9.12. Aporta además MPC, perfiles de PID, `home_current`,
  `min_home_dist`, `gcode_shell_command`, funciones matemáticas en macros y carpeta `plugins/`.

**Consecuencias.**

- Los módulos propios de la Hi se escriben como plugins o extras independientes, para poder pasar a Klipper
  oficial más adelante portando solo los cambios de núcleo.
- Hay que seguir los cambios del fork de Jacob (y de KalicoCrew por debajo) y volver a comprobar la
  compatibilidad con las MCU de la Hi al actualizar.
- Código GPLv3.

## D2 — El código vive en un fork propio del Kalico de Jacob10383 (2026-11-09)

**Contexto.** Opciones: plugins en este repo instalados sobre el Kalico de Jacob, un fork propio de ese Kalico,
o ambos.

**Decisión.** Fork propio del Kalico de Jacob10383.

**Motivos.**

- Los cambios de núcleo que necesite la Hi (homing, `z_align`, compatibilidad con MCU) se hacen en el mismo
  árbol que los módulos, con historial completo.
- Se pueden traer cambios del fork de Jacob y de KalicoCrew con `git merge`/`rebase` desde remotos `upstream`.

**Consecuencias.**

- Los módulos de la Hi siguen separados dentro del fork (ficheros propios en `klippy/extras/` o `plugins/`)
  para limitar conflictos al actualizar.
- Hay que mantener el fork al día y volver a comprobar las MCU de la Hi tras cada actualización.

## D3 — Dos repositorios, como el CFW de la K2 (2026-11-09)

**Contexto.** Jacob10383 separa el código ([kalico](https://github.com/Jacob10383/kalico)) del repo de
publicación ([k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware)), que contiene
imágenes, instalador (`install.py`, `bootstrap`, `swap`), índice de la release con SHA-256, una copia de los
módulos (`extras/` + `manifest.json`) y la web de documentación (MkDocs + GitHub Pages).

**Decisión.** Dos repositorios:

| Repo | Contenido |
| - | - |
| `Creality-Hi-CFW` (este) | Investigación, documentación, herramientas, datos, instalador y releases |
| Fork propio del Kalico de Jacob10383 | Código del host: núcleo de Kalico y módulos de la Hi |

**Consecuencias.**

- El instalador de este repo clonará el fork en la impresora, como el `bootstrap` de la K2.
- No hacen falta kernel ni rootfs propios: se usa el Tina de stock (ver
  [analysis/k2-port-feasibility.md](analysis/k2-port-feasibility.md)).
- Pendiente al crear los repos: nombre y ubicación local del fork, y si se enlaza aquí como submódulo para el
  desarrollo.

## D4 — Ramas, commits e integración (2026-11-09)

**Decisión.**

| Repo | Ramas |
| - | - |
| `Creality-Hi-CFW` | `main` estable (releases) y `dev` de integración |
| `Creality-Hi-Kalico` | `main` espejo de Jacob10383/kalico; `dev` de integración (rama por defecto); `main-hi` estable, la que usará el instalador |

- Cada tarea en una rama que sale de `dev` (`feat/...`, `fix/...`, `docs/...`) y entra en `dev` por **pull
  request**. `dev` pasa a la rama estable (`main` o `main-hi`) por pull request cuando funciona; en el fork, eso
  significa probado en la impresora.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/) en inglés: `type(scope): descripción`
  y cuerpo libre opcional. Sustituye al formato `CHANGES BY FILE`/`IMPROVEMENTS` de los primeros commits.
- En el fork solo se ejecutan los checks de los pull request; los workflows de publicación heredados de Kalico
  se desactivan.

**Motivos.** Los pull request dejan historial revisable, lanzan el CI de Kalico y encajan con los hilos del
proyecto de claude.ai. `main` espejo en el fork hace que actualizar desde Jacob sea un avance directo.

## D5 — Fase 1 escalonada, sin escribir en flash (2026-11-10)

**Contexto.** El rootfs es SquashFS de solo lectura y el overlay (`rootfs_data`) es un único volumen para los
slots A y B, así que el slot libre no aísla cambios de ficheros ([phase1-plan.md](phase1-plan.md) §5.2).
Opciones: instalación escalonada sin flash, slot A/B libre desde el principio, o servicio persistente en el
overlay.

**Decisión.** Escalonada: Kalico vive en `/mnt/UDISK/kalico-hi` y se lanza a mano parando el Klipper de stock.

**Motivos.**

- Nada persistente fuera de `/mnt/UDISK/kalico-hi`: un reinicio devuelve a stock y la impresora no puede quedar
  sin arrancar.
- No se conoce todavía si U-Boot vuelve solo al otro slot cuando uno no arranca.

**Consecuencias.**

- En fase 1 no se tocan flash, overlay ni variables de U-Boot. Scripts: `scripts/hi_install.sh`,
  `hi_kalico.sh`, `hi_restore.sh`.
- Kalico no arranca solo al encender; el servicio persistente (backlog B13) y el slot A/B (B14, objetivo final
  del proyecto) se diseñan cuando la fase 1 funcione.

## D6 — `c_helper.so` como artefacto del paquete de instalación (2026-11-10)

**Contexto.** El `c_helper.so` que trae el fork (compilado por Jacob10383 para la K2) pide `GLIBC_2.34` y no
carga con la glibc 2.29 de la Hi ([phase1-plan.md](phase1-plan.md) §4). Opciones: compilarlo al crear el paquete
de instalación, o sustituir el binario en la rama `dev` del fork.

**Decisión.** Artefacto del paquete: `scripts/build_chelper.sh` lo compila y `scripts/make_bundle.sh` lo mete en
el `.tar.gz` con su SHA-256. El fork conserva el binario de Jacob sin tocar.

**Motivos.**

- Sin conflicto binario al sincronizar con upstream.
- Un binario en git queda desfasado sin avisar cuando cambian los fuentes C; el paquete lo recompila siempre y
  registra el commit del que sale.

**Consecuencias.**

- Un clon del fork no funciona en la Hi por sí solo: hay que instalar el paquete.
- `make_bundle.sh` rechaza un `.so` compilado de otro commit.
