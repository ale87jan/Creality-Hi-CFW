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
