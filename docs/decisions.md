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

## D7 — Interfaz en fase 1: consola SSH y después Fluidd (2026-11-10)

**Contexto.** `master-server`, `display-server` y `app-server` de Creality hablan con Klipper directamente por
`/tmp/klippy_uds` ([phase1-plan.md](phase1-plan.md) §5.3). Opciones: consola SSH y después Fluidd, solo consola,
o dejar todos los servicios de stock encendidos contra Kalico.

**Decisión.** Primer arranque con socket propio (`/tmp/kalico_uds`) y consola por SSH (`hi_kalico.sh gcode`);
cuando el arranque básico esté comprobado, el Moonraker de stock apuntando a Kalico (`hi_kalico.sh start --ui`).
Los servicios de Creality (pantalla, nube) se paran durante la sesión.

**Motivos.** Con socket propio los servicios de Creality no envían a Kalico peticiones propietarias, y Fluidd se
añade cuando ya se sabe que el núcleo funciona.

**Consecuencias.**

- La pantalla queda sin servicio mientras dura una sesión de Kalico.
- Falta comprobar que el Moonraker de stock funciona contra Kalico (backlog B10).

## D8 — `motor_control` de la Hi como copia aparte (2026-11-10)

**Contexto.** `motor_control.py` del fork no arranca en la Hi ([phase2-plan.md](phase2-plan.md) §3). Opciones:
opciones nuevas en el módulo compartido (la recomendada por el modelo), un módulo de la Hi que herede del de la
K2, o una copia aparte recortada.

**Decisión.** Copia aparte: `klippy/extras/motor_control_hi.py` en el fork, recortada para la Hi (solo X/Y, sin
motor E, sin túnel `transparent`, sin calibración de corte). `motor_control.py` de la K2 no se toca.

**Motivos.** Elección del usuario. Cero conflictos al sincronizar con upstream y un módulo más pequeño y
auditable para un hardware donde no se pueden probar los caminos de la K2.

**Consecuencias.**

- Los arreglos de upstream en `motor_control.py` no llegan solos a la Hi: revisar el diff en cada sincronización.
- `homing.py` busca el objeto `motor_control` e importa constantes de `.motor_control`: el módulo de la Hi se
  registra también con ese nombre para no tocar `homing.py`.
- Sustituye a la regla del `CLAUDE.md` del fork ("preferir opciones nuevas") solo para este módulo.

## D9 — Escrituras a los drivers X/Y por niveles (2026-11-10)

**Contexto.** El arranque de `motor_control` de la K2 escribe en los drivers: modo de stall, borrado de fallos
y, si la config trae parámetros, `SYS_PARAM` ([phase2-plan.md](phase2-plan.md) §2). Opciones: niveles empezando
en lectura, el arranque de la K2 sin claves de parámetros, o solo lectura siempre.

**Decisión.** Opción `startup_writes` en `[motor_control_hi]` con tres niveles: `none` (asigna direcciones y solo
lee; valor por defecto), `stall` (añade el modo de stall y el borrado de fallos; necesario para el homing) y
`params` (añade `SYS_PARAM` en RAM; solo con aprobación expresa del usuario). Las tramas de flash y de
calibración no se envían en ningún nivel.

**Motivos.** Cumple la regla de empezar en solo lectura y deja un camino hasta el homing sin tocar código.

**Consecuencias.**

- Con `none` no hay homing de X/Y: `G28 X` responde con un error que pide `startup_writes: stall`.
- Asignar direcciones (broadcast `READ_ADDR 01`) ocurre en todos los niveles; se asume que el stock hace lo
  mismo en cada arranque (por confirmar en el paso 2.1).
- Subir a `params` es una decisión aparte, con los ids ya verificados para `mot2_002_071`.

## D10 — Homing de la fase 2: solo X e Y (2026-11-10)

**Contexto.** El `homing.py` del fork exige el escáner de la K2 para `G28 Z` ([phase2-plan.md](phase2-plan.md)
§5). Opciones: solo X/Y con Z bloqueado, o adelantar el homing de Z (sonda y `z_align`) a la fase 2.

**Decisión.** Solo X e Y. `G28` y `G28 Z` dan error en `config/hi/phase2.cfg`; Z se levanta con
`SET_KINEMATIC_POSITION`, como en la fase 1. El homing de Z llega con la sonda en la fase 3.

**Motivos.** No juntar en las mismas pruebas el riesgo de los motores con el de choque contra la cama.

**Consecuencias.** En la fase 2 no hay posición de Z real: antes de mover X/Y hay que levantar Z a mano.

## D11 — Sonda: `prtouch.py` de la K2 tal cual (2026-11-10)

**Contexto.** El `prtouch.py` del fork habla con las MCU de la Hi sin cambios ([phase3-plan.md](phase3-plan.md)
§2). Opciones: usarlo tal cual, solo con config, o una copia aparte recortada como en D8.

**Decisión.** Tal cual. La Hi solo aporta `config/hi/phase3.cfg`.

**Motivos.** A diferencia de `motor_control`, el módulo ya funciona con la Hi y no escribe nada persistente; los
arreglos de upstream llegan al sincronizar.

**Consecuencias.**

- `PRTOUCH_SCRUB`, `PRTOUCH_SCAN_CALIBRATE` y `PRTOUCH_AXIS_TWIST_COMPENSATION` quedan registrados pero no se
  usan; `PRTOUCH_SCRUB` necesita `extended_zone_transform`, que la Hi no carga.
- La limpieza de boquilla es aparte ([phase4-plan.md](phase4-plan.md) §4). Criterio del usuario: `PRTOUCH_SCRUB`
  si funciona en la Hi; si no, `NOZZLE_CLEANUP` o sus macros de `nozzle_cleaning_macros.cfg`.

## D12 — Alineación de Z antes que la sonda (2026-11-10)

**Contexto.** El roadmap ponía la sonda (fase 3) antes que `z_align` (fase 4). El stock siempre alinea los dos
husillos contra los sensores de arriba antes de sondear ([phase4-plan.md](phase4-plan.md) §2).

**Decisión.** En la impresora se prueba primero la alineación (`ZDOWN`) y después la sonda.

**Motivos.** `ZDOWN` mueve el puente hacia arriba, lejos de la cama: es la prueba de Z con menos riesgo, y deja
el primer contacto de la boquilla con la cama con el puente ya nivelado y Z en una posición conocida (`zmax`).

**Consecuencias.**

- `z_align_hi.py` (B26) pasa a ser la siguiente pieza de código, antes de probar `config/hi/phase3.cfg`.
- Los números de fase del roadmap no cambian; cambia el orden de las pruebas: 1, 2, 4 (solo `z_align`), 3.

## D13 — `z_align` portado del módulo de la Hi (2026-11-10)

**Contexto.** Ni el `z_align.py` de la K2 (pide `safeDist` y `z_align_force_stop`) ni el de la Hi (depende de
parches de Creality) valen tal cual ([phase4-plan.md](phase4-plan.md) §3). Opciones: portar el de la Hi con sus
comandos y una macro de `G28`, o derivar el de la K2 integrado en el `homing.py` del fork.

**Decisión.** Portar el de la Hi: `z_align_hi.py` con `ZDOWN`, `UP_SAFE_Z`, `CHECK_ZLIMIT` y `ZDOWN_SWITCH`.

**Motivos.** Es la secuencia que la MCU de la Hi ya ejecuta en stock, el módulo es corto y no depende de
protecciones de MCU que la Hi no tiene.

**Consecuencias.**

- El objeto se llama `z_align_hi`, así que el `homing.py` del fork no lo integra; la secuencia vive en la macro
  `[homing_override]` de `config/hi/phase4.cfg`, en serie como el stock.
- No hay forma de parar la MCU a mitad de una alineación: ante un `timeout` se apagan los motores.
- Se pierde la corrección de `Z_TILT_ADJUST` en cada `ZDOWN` hasta portar un sustituto de `ADJUST_STEPPERS`.

## D14 — Limpieza de boquilla: macros del usuario con guarda y reset (2026-11-10)

**Contexto.** Ninguna limpieza del fork (`PRTOUCH_SCRUB`, `NOZZLE_CLEANUP`) reproduce la de stock; las macros
del usuario sí, solo con G-code ([phase4-plan.md](phase4-plan.md) §4). Su guarda de reentrada se queda puesta
si la limpieza falla a medias.

**Decisión.** `config/hi/clean.cfg` con sus macros portadas. Se mantiene la guarda (`busy`) y se añade
`NOZZLE_CLEAN_RESET` para liberarla a mano.

**Consecuencias.**

- Tras un error de limpieza hay que lanzar `NOZZLE_CLEAN_RESET` (o reiniciar); si no, las siguientes limpiezas
  no hacen nada y no avisan.
- La limpieza no se engancha al `G28 Z`: es siempre una orden explícita.

## D15 — Módulos de la Hi que se portan en la fase 4 (2026-11-10)

**Contexto.** La Hi trae cinco módulos legibles propios: `z_align`, `nozzle_clear`, `tmc_line_check`,
`bl24c16f` y `timer_read` ([phase4-plan.md](phase4-plan.md)).

**Decisión.** Se portan `z_align` (D13), la limpieza de boquilla (D14) y `tmc_line_check`. `bl24c16f` queda sin
fecha y `timer_read` no se porta.

**Consecuencias.**

- `CHECK_ZMOTOR_LINE` permite comprobar los cables de Z y Z1 antes del primer `ZDOWN` (paso 4.2b).
- Sin `bl24c16f` no hay recuperación de impresión tras un corte de luz.

## D16 — CFS: `creality_cfs.py` de gitstonelabs sobre `serial_485` (2026-11-10)

**Contexto.** El `box.py` de la K2 tiene fijos el pin del sensor de corte, el sentido del corte y la geometría
trasera, y su capa de órdenes no coincide con lo capturado en una Hi (`0x0A`, `0x0D`, `0x0F`, `0x11`;
[phase5-plan.md](phase5-plan.md) §1). `gitstonelabs/creality-cfs-klipper` (GPLv3) tiene la Hi como hardware de
referencia, pero abre el puerto serie por su cuenta, y en la Hi ese puerto es el bus de los drivers de X/Y.

**Decisión.** Usar `creality_cfs.py` con una opción `serial` añadida que lo hace hablar por `serial_485`.
Comandos `CFS_*`; los alias `BOX_*` de stock se dejan para la fase 6.

**Consecuencias.**

- El cambio sobre el fichero original es aditivo, para proponerlo a su autor desde un fork (B34b).
- El módulo no se ha ejercitado en hardware según su propio `NOTICES.md`: las pruebas en la Hi empiezan por
  lectura (pasos 5.2 y 5.3) y `auto_init` queda apagado.
- No se usa `box.py` ni `box_protocol.py` de la K2 en la Hi.

## D17 — `G28 Z` no repite la alineación del pórtico (2026-11-10)

**Contexto.** En stock cada `G28 Z` hace `ZDOWN` y la preparación de una impresión lo llama dos veces.
`nachorepara/creality-hi-klipper-tweaks` (parche 01) mide 57-61 s frente a 17-23 s sin la segunda alineación.

**Decisión.** En `phase4.cfg`, `ZDOWN` solo si Z no está referenciado al empezar el `G28`. `G28 ALIGN=1` la
fuerza. `ZDOWN_SWITCH ENABLE=0` sigue desactivándola siempre.

**Consecuencias.** La corrección de `Z_TILT_ADJUST` se conserva entre `G28 Z` de la misma sesión (reduce B26b
a un ahorro tras el primer `G28`). Tras `M84`, un error o un reinicio se vuelve a alinear.

## D18 — Arranque automático con un servicio propio que conmuta (2026-11-10)

**Contexto.** [autostart-plan.md](autostart-plan.md) compara tres formas de arrancar Kalico sin intervención:
servicio propio al final del arranque (A), línea en `/etc/rc.local` (B) y deshabilitar los servicios de stock (C).

**Decisión.** Opción A, "por ahora" [usuario]: `/etc/init.d/kalico_hi` repite la conmutación manual de la fase 1,
gobernado por ficheros bandera en `/mnt/UDISK/kalico-hi`. No se modifica ningún fichero de stock.

**Consecuencias.** Los scripts se escriben cuando la conmutación manual esté probada en la Hi (fase 1), que es
requisito del diseño. Instalarlo es la primera escritura en el overlay y necesita aprobación expresa.

## D19 — Protección de ramas con rulesets de GitHub (2026-11-10)

**Contexto.** D4 define el flujo de ramas, pero nada lo imponía. Los dos repos son públicos, así que los
rulesets están disponibles en el plan Free.

**Decisión.** Rulesets activos [P, `gh api repos/.../rulesets`], todos sin push forzado ni borrado:

| Repo | Rama | Reglas |
| - | - | - |
| Creality-Hi-Kalico | `main` (espejo) | Historial lineal; sin PR, para poder avanzar por fast-forward desde `Jacob10383/kalico` |
| Creality-Hi-Kalico | `main-hi` | Solo por PR, 1 aprobación |
| Creality-Hi-Kalico | `dev` | Solo por PR, sin aprobación obligatoria |
| Creality-Hi-CFW | `main` | Igual que `main-hi` |
| Creality-Hi-CFW | `dev` | Igual que `dev` de Kalico |

`creality-cfs-klipper` no se toca. Además, `delete_branch_on_merge` está activo en los dos repos y se borran
las ramas muertas en local tras cada fusión.

**Consecuencias.** Un único colaborador no puede aprobar su propio PR, así que `main-hi` y `main` de CFW llevan un
bypass del rol de administrador **solo en modo `pull_request`** [usuario]: se fusiona por PR sin aprobación, pero
no hay push directo. Los rulesets no pueden limitar la rama origen: "`main-hi` solo desde `dev`" sigue siendo una
convención. Todo cambio, también de docs, va por rama y PR.

## D20 — Apartar X del tope antes del homing y aparcarla en X0 después (2026-11-10)

**Contexto.** En la prueba de la fase 2, `G28 X Y` con X ya en el tope solo movió Y [P]: el stock se aparta 10 mm
antes (`_HOME_X`) y la config de la fase 2 no. Además, el homing deja X en `-19`, pulsando el interruptor de la
papelera de purgas, lo que no es bueno [usuario].

**Decisión.** La macro `_HI_HOME_XY` (fork, `config/hi/motors.cfg`) aparta X 10 mm si está homeada a menos de
10 del tope y, tras el homing de X, la aparca en X0. Las usan los `homing_override` de `phase2.cfg` y `phase4.cfg`.

**Consecuencias.** El `G28` de la Hi termina con X=0. **Probado en la Hi el 2026-11-10 [P]** (copiando `motors.cfg` y
`phase2.cfg` de [Creality-Hi-Kalico#3](https://github.com/ale87jan/Creality-Hi-Kalico/pull/3)): desde el centro, `G28 X Y`
terminó con X=0, Y=4; repetido con X en X0, X se apartó, `G28 Y`, `G28 X` y X0, sin fallos en los drivers.
