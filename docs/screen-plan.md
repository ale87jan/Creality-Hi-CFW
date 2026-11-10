# Pantalla de la Hi con Kalico: opciones

Estado: análisis sin impresora (2026-11-10). Decisiones ya tomadas en el §0; la base de la pantalla táctil
(opción H frente a E) sigue abierta. Mientras
tanto sigue vigente la decisión D7 (consola SSH y luego Fluidd) y la recomendación de
[phase6-plan.md](phase6-plan.md) §8.2: solo Fluidd hasta imprimir bien.

Marcas: **[verificado: fichero:línea]** leído en el repo; **[supuesto: cómo comprobarlo]**. Las citas de
proyectos externos vienen de sus páginas, leídas por un subagente y no contrastadas con el código fuente.

## 0. Decisiones de Alejandro (2026-11-10)

Pendientes de copiar a `docs/decisions.md` cuando se unan las ramas (ese fichero tiene D5-D17 en la rama de
fases y aquí daría conflicto).

| Opción | Decisión |
| - | - |
| 0 Solo Fluidd | **Adoptada como base**: la pantalla queda parada durante Kalico hasta tener sustituto |
| G Panel del CFS en Fluidd | **Planificado** (B45), tras fijar la interfaz del CFS en la fase 5 |
| A UI de stock (A1 y A2) | **Descartada**; B41 deja de hacer falta |
| Pantalla táctil | Preferencia: adaptar ADL-Screen o K1C-CFS-Power-Screen (opción H) o UI propia (E). **Aplazada** hasta leer el panel real (B40) y fijar la interfaz del CFS (fase 5) |

## 1. Qué tiene la Hi

| Elemento | Dato |
| - | - |
| Panel | GC9307 por SPI de 9 bits, **240x320 vertical** [verificado: docs/hardware.md:14; `lcd_driver_name = gc9307_9bit_spi_tjc_240_320`, `lcd_x/lcd_y = 240/320` en data/derived/dtb/hi-v1.1.0.74.txt:1685-1689] |
| Acceso al panel | Framebuffer del kernel, pila `DISP2_SUNXI` con `FB`, `G2D` y `CMA` activos [verificado: data/derived/kernel-config/hi-v1.1.0.74.config:2644,2667,1611,727]. Los nodos `disp`/`lcd0`/`lcd_fb0` están en `status = okay` [verificado: dtb:1362-1366,1632-1633,1707-1712] |
| Retroiluminación | PWM canal 5, 10 kHz, y pin de habilitación `lcd_bl_en` [verificado: dtb:1699-1704] |
| Táctil | Capacitivo en I2C `twi3`: Goodix `gt9xxnew_ts` en 0x14 o TLSC `tlsc6x` en 0x2e, ambos módulos de kernel (`=m`), con el IRQ en el mismo pin [verificado: dtb:1224-1248; config:1515,1518]. Evdev activo [verificado: config:1437] |
| Resolución del táctil | El DTB declara 480x800 (`0x1e0 x 0x320`) [verificado: dtb:1232-1233], pero el táctil entrega 240x320 (medido, §1b) |
| UI de stock | `display-server`, `master-server`, `app-server`, `web-server` (binarios cerrados) y `lvgl_klipper` [verificado: docs/analysis/firmware-versions.md:25,34]. La pantalla y la nube hablan con `/tmp/klippy_uds` con órdenes propias, no con las de Moonraker [verificado: phase1-plan.md:158-161, rama de fases; phase6-plan.md:17-18] |
| Recursos | SoC T113-i, Cortex-A7, glibc 2.29, Python 3.9.12 [verificado: docs/hardware.md:8-11]. RAM libre y espacio: [supuesto: `free -m` y `df -h`, ver §4] |

Consecuencia clave: **240x320 está por debajo de lo que soportan los proyectos de UI existentes** (§2), y
solo un proceso puede usar el framebuffer a la vez.

## 1b. Lectura en la impresora (B40, 2026-11-10)

Captura de solo lectura con el firmware de stock en marcha: `data/captures/2026-11-10_hi-screen/screen-probe.txt` (abreviado `probe`).

| Dato | Valor medido | Consecuencia |
| - | - | - |
| Framebuffer | `/dev/fb0`, virtual 240x640, 32 bpp, `stride` 960 [verificado: probe:4,10-12]; `disp_reserve=307200` = 240·320·4 [verificado: probe:2] | Panel visible de 240x320 con dos páginas (doble búfer). LVGL con `fbdev` vale, con color de 32 bits |
| Retroiluminación | No existe `/sys/class/backlight`; solo `pwmchip0` [verificado: probe:16-18] | El brillo va por la pila `disp` o por el PWM; cómo lo hace `display-server` [supuesto: `strings` del binario en el PC] |
| Táctil | Un solo dispositivo, `gt9xxnew_ts` en `/dev/input/event0`; `tlsc6x` cargado pero sin dispositivo [verificado: probe:8,21,25,32-33] | El controlador real es el Goodix |
| Ejes del táctil | `ABS=2650000 0`: solo ejes multitáctiles (`ABS_MT_POSITION_X/Y`, `TRACKING_ID`, `TOUCH_MAJOR`, `WIDTH_MAJOR`), sin `ABS_X/ABS_Y`; `BTN_TOUCH` presente [verificado: probe:28-29, decodificado a mano] | El `evdev` de `lv_drivers` debe leer los ejes MT. El driver no declara rango (`EVIOCGABS` devuelve `max=0`) [verificado: probe:96-100], pero medido tocando las esquinas entrega **X 1-239, Y 0-314: coordenadas 1:1 con el panel de 240x320** [verificado: probe:102-117]. El 480x800 del DTB no se aplica. Orientación: Alejandro tocó en el orden arriba-izquierda, abajo-izquierda, abajo-derecha, arriba-derecha, y el ciclo medido tiene ese mismo sentido de giro: **no hay eje invertido ni ejes intercambiados**. Queda por distinguir entre origen arriba-izquierda (lo normal) y giro de 180° [supuesto: un toque único en una esquina conocida] |
| Quién usa la pantalla | `display-server` tiene abiertos `/dev/fb0` y `/dev/input/event0`, y cuatro ficheros de memoria compartida en `/tmp/shm/` (`device_state_shm`, `materail_box_shm`, `dev_maintain_shm`, `print_object_shm`) [verificado: probe:49-57] | Para usar el panel hay que parar `display-server`. Recibe el estado por memoria compartida; quien habla con `/tmp/klippy_uds` es otro proceso [supuesto: `master-server`] |
| Motor gráfico de stock | Sin biblioteca LVGL dinámica; usa `libfreetype`, `libpng16`, `libjpeg` [verificado: probe:60-76] | [supuesto: LVGL enlazado en estático; no afecta al plan] |
| Memoria | 488 MB, 365 MB disponibles con el stock en marcha; sin swap [verificado: probe:79-80] | Sobra para una UI LVGL (decenas de MB) |
| Disco | `/mnt/UDISK` 4,2 GB libres; overlay 233 MB libres [verificado: probe:85,88] | Sin problema de espacio |
| Python | PIL 8.2.0 instalado [verificado: probe:90] | Un prototipo en Python que dibuje en `fb0` es viable sin compilar nada |
| Fluidd | `/usr/share/fluidd` (en el SquashFS de solo lectura) [verificado: probe:94] | El panel del CFS (G) necesita una copia de Fluidd fuera de `/rom` o un cambio en el overlay |

Dos datos fuera del tema de la pantalla, para el hilo de fases:

- El almacenamiento aparece como `mmcblk0` con particiones GPT (`rootfs_data@mmcblk0p10`, `UDISK@mmcblk0p11`)
  [verificado: probe:2], no como SPI NAND con UBI como dice `docs/hardware.md:12`.
- La impresora arrancó con `root=/dev/mmcblk0p7`, que es `rootfsB` [verificado: probe:2]: el slot libre es el A.

## 2. Opciones

### Opción 0 — Sin pantalla útil; solo Fluidd (la de la decisión actual)

- Qué es: durante la sesión de Kalico `hi_kalico.sh` para `app` y `klipper` de stock (D5); la pantalla queda
  congelada o con el último estado, y se maneja todo desde Fluidd [verificado: phase1-plan.md:150-158, rama de
  fases].
- Riesgo: ninguno técnico. Coste: sin control en la máquina (parar, pausar, cambiar filamento) si falla la red.
- Ejemplo de uso: abrir `http://<ip>:80` (Fluidd) y pulsar «Pausa»; el botón de emergencia es `M112` en Fluidd.

### Opción A — Mantener la UI de stock contra Kalico

Hay dos variantes.

- **A1. Kalico en `/tmp/klippy_uds` y la UI de stock encendida.** La UI enviaría peticiones propietarias que
  Kalico no implementa (es lo que llevó a parar los servicios en D5 [verificado: phase1-plan.md:158-161]).
  Efecto probable: pantalla vacía o con errores, sin garantías de seguridad (órdenes ignoradas o mal
  interpretadas). Esfuerzo bajo, valor casi nulo.
- **A2. Pasarela UDS (shim) que traduce el protocolo propietario a Kalico/Moonraker.** Se conserva la UI
  completa, incluida la de impresión y el CFS. Requiere capturar y documentar el protocolo (no está en el
  repo [supuesto: `grep` en el fichero extraído del stock; `strings` en `display-server`/`master-server` solo
  da nombres]) y que cada orden tenga equivalente en Kalico (muchas son los `BOX_*`, `SET_*` cerrados de
  phase6-plan.md §3). Riesgo alto: la UI de stock asume el Klipper parcheado; cada versión OTA recompila
  los binarios [verificado: firmware-versions.md:34,96]. Esfuerzo alto.
- Ejemplo (A2, esquema): `display-server ⇄ /tmp/klippy_uds (shim) ⇄ Kalico /tmp/kalico_uds`, donde el shim
  responde `info`/estado y reenvía solo lo que Kalico entiende.

### Opción B — HelixScreen (LVGL, GPL-3.0)

- Qué es: UI táctil en C++/LVGL sin X11; dibuja en `/dev/fb0` (o DRM/KMS) y lee el táctil por evdev; habla con
  Moonraker en el puerto 7125; ~15 MB de RAM en objetivos embebidos. Soporta Creality K1 y K2 Plus; la Hi
  figura como «Preliminary… untested» [fuente: <https://github.com/prestonbrown/helixscreen>, `/reference/faq/`,
  `/dev/printers/creality-k2/`; no contrastado con el código].
- Binarios `armv7-a` hard-float publicados para otros equipos (K2: `armv7-a`) [fuente: página K2]. Los de
  Raspberry van contra glibc 2.31, la Hi tiene 2.29; los de K1/K2 son musl estático [fuente: README]. Hay que
  comprobar cuál es compatible [supuesto: `readelf -d`/`file` sobre el binario en el PC, nunca ejecutarlo en
  la Hi sin aprobación].
- Riesgos: **240x320 no está soportado** (se declara 480x320 «puede solaparse»; 800x480 es lo bien probado)
  [fuente: FAQ]; orientación vertical sin soporte confirmado; compite con la UI de stock por el framebuffer
  (en la K2 su instalador detiene `display-server`) [fuente: FAQ/K2]; su instalador es un `curl | sh`
  con acceso a flash, que contradice D5; Fluidd/Moonraker de stock deben ir contra Kalico (escalón 3 de D5).
- Ejemplo: tras `hi_kalico.sh start --ui` (Moonraker de stock contra Kalico, puerto 7125), instalar HelixScreen
  apuntando a ese Moonraker y comprobar si la vista de inicio cabe en 240x320. [supuesto: el procedimiento
  exacto de instalación y configuración hay que leerlo en su documentación antes de probar nada]

### Opción C — Guppyscreen (LVGL, GPL-3.0)

- Qué es: UI táctil LVGL sin X11/Wayland sobre Moonraker; instalador para K1/Max/CR-10 SE/Ender 3 V3 KE
  (MIPS). Sin Hi, K2 ni binarios ARMv7 citados; 240x320 no aparece [fuente: <https://github.com/ballaswag/guppyscreen>].
- Riesgos: igual que B y sin referencias para ARM de Creality; su instalador usa `wget --no-check-certificate`
  [fuente: README]. Sería compilarlo para ARMv7/glibc 2.29 y portar el tamaño de pantalla a mano.
  Descartable salvo que B no sirva.

### Opción D — KlipperScreen (GTK3, AGPL-3.0)

- Requiere un servidor gráfico (Xserver, Cage o Weston), Python con PyGObject y resolución mínima oficial
  **480x320** [fuente: <https://klipperscreen.readthedocs.io/en/latest/Hardware/>, `/Installation/`]. La Hi no
  tiene X ni GTK [supuesto: `opkg list-installed`/`ls /usr/lib | grep -i gtk`] y su RAM/flash son escasas.
- **Descartada en este análisis** (inviable en Tina y por debajo del mínimo), salvo ejecutarla en otro equipo
  que apunte a Moonraker, lo que no usa la pantalla de la Hi.

### Opción E — UI propia mínima (LVGL o Python sobre el framebuffer)

- Qué es: un estado simple de 240x320 (temperaturas, progreso, pausa/cancelar) escrito para la Hi, hablando
  con Moonraker o con el socket de Kalico. LVGL con `lv_drivers` (fbdev + evdev) compilado para ARMv7/glibc
  2.29, o un renderizado Python a `/dev/fb0` si hay PIL (¿la Hi lo tiene? [supuesto: `python3 -c "import PIL"`]).
- Riesgos: es la única que se adapta al panel real, pero hay que mantener código propio; el calibrado
  del táctil (480x800 frente a 240x320) y la retroiluminación son nuestros.
- Ejemplo (tamaño de la tarea): 3 pantallas (inicio, impresión, ajustes de temperatura) ≈ 600-900 líneas C++
  con LVGL [supuesto: estimación, sin base medida].

### Variante F — HelixScreen o LVGL con tema/ diseño de 240x320 propio

Si B funciona salvo el tamaño, se puede contribuir un layout vertical 240x320 (o el modo «tiny»). Depende de
que el equipo aguas arriba lo acepte; se decide tras ver B en el panel.

### Opción H — Adaptar PowerScreen (K1C-CFS-Power-Screen) o su fork ADL-Screen

Propuesta por Alejandro. Código leído en clones de solo lectura: `ADL-Screen@e3ecc09` (2026-11-08) y
`K1C-CFS-Power-Screen@bbc6a17` (2026-10-14). Las referencias `fichero:línea` son de ADL-Screen.

- Qué son: forks de Guppyscreen (GPL-3.0) en C++ con LVGL 8, unas 20 000 líneas en `src/`. ADL-Screen es
  PowerScreen mantenido aparte desde el 2026-11-06, con i18n (italiano por defecto) [verificado: NOTICE.md:3-5;
  src/main.cpp:47-49].
- Lo que encaja con la Hi:
  - Dibuja en fbdev y lee el táctil por evdev, con el tamaño leído del framebuffer, rotación por software
    (`display_rotate`) y calibración táctil opcional [verificado: src/main.cpp:58-112].
  - Habla con Moonraker por websocket (libhv) [verificado: src/websocket_client.cpp]; no usa `/tmp/klippy_uds`.
  - Enlace estático y compilación cruzada con `CROSS_COMPILE` [verificado: Makefile:4-12,26]: no depende de
    la glibc 2.29 de la Hi. Hoy solo se publica para MIPS [verificado: Makefile:77]; ARMv7 habría que montarlo.
  - Ya trae panel del CFS (`cfs_panel.cpp`, `cfs_model.cpp`), M600 y flujo de impresión.
- Lo que no encaja:
  - **Diseño fijo de 800x480 apaisado**: todo se escala con `ancho/800` y la pantalla de inicio usa posiciones
    absolutas sobre esa rejilla [verificado: src/powerui.h:11; src/powerui.cpp:12; src/main_panel.cpp:767]. En
    240x320 el factor sería 0,3: ilegible. Hay que **rehacer las vistas**, no ajustar un parámetro.
  - El CFS usa el objeto `box` y `BOX_INFO_REFRESH`, `BOX_MODIFY_TN_DATA`, `BOX_ENABLE_CFS_PRINT`,
    `BOX_NOZZLE_CLEAN` del Klipper de Creality [verificado: src/cfs_model.h:10; src/cfs_panel.cpp:535,880;
    src/print_panel.cpp:1427]; hay que portarlo a `creality_cfs` (D16).
  - Rutas y servicios de la K1 (`/usr/data/...`) [verificado: src/main.cpp:45]; su `installer.sh` no vale para la Hi.
  - Licencia: el código es GPL-3.0, pero el diseño PowerUI (tema, iconos, maquetas) es **CC BY-NC 4.0**
    [verificado: LICENSE-POWERUI.md:3-5], que no es compatible con redistribuir bajo GPL-3.0. Como las vistas
    se rehacen igualmente, se usaría el código sin los recursos PowerUI [supuesto: revisar qué ficheros de
    `assets/` y `src/powerui.*` cubre esa licencia].
- Cuál de los dos: PowerScreen es el original y la fuente de los cambios; ADL-Screen añade i18n y es más
  reciente, pero lleva cuatro días como fork. [supuesto: comparar `git log` de ambos antes de elegir]
- Ejemplo: reutilizar `websocket_client`, `state`, `cfs_model` y el arranque fbdev/evdev, y escribir tres
  vistas nuevas de 240x320 vertical (inicio, impresión, CFS). Se prueba en el PC con el simulador SDL del
  propio Makefile (compilación sin `CROSS_COMPILE`) antes de tocar la Hi.

- **Prueba en simulador (2026-11-10, en la nube, sin impresora):** ADL-Screen@e3ecc09 compilado con SDL a
  240x320, 320x240 y 800x480, sin Moonraker (vista de inicio en espera). A 800x480 se ve bien; a 240x320 y a
  320x240 los textos se solapan y se cortan y la vista ocupa solo el tercio superior: **ilegible sin rehacer
  las vistas** [verificado: capturas `pantalla/adl-screen-240-320-800.png` en los ficheros del proyecto]. El
  tema usa una fuente mínima de 12 px que no baja con la escala [verificado: src/main.cpp:149-151]. No se
  probaron las demás vistas (necesitan un Moonraker) ni PowerScreen, que comparte este código de escalado.

Frente a la opción E (UI propia): H ahorra el cliente de Moonraker, el modelo de estado y el del CFS, a cambio
de heredar 20 000 líneas pensadas para otra pantalla. En la práctica H es «UI propia sobre el motor de
PowerScreen».

### Complemento G — Panel del CFS dentro de Fluidd (para la opción 0)

Aportado por Alejandro: repos de la K1C que añaden un panel del CFS a Fluidd. Leídos en sus páginas de GitHub
por un subagente (sin ver el código ni las fechas de los commits, que no se pudieron leer):

| Repo | Qué es | Panel en Fluidd |
| - | - | - |
| [borferkic/K1C-CFS-Power-Script](https://github.com/borferkic/K1C-CFS-Power-Script) | Menú SSH, fork del Creality Helper Script, GPL-3.0 | **Sí**: «copying `power-cfs-panel.js` to the Fluidd folder and adding one `<script>` tag to Fluidd's index.html», más cambio de la revisión en `sw.js` por la caché PWA |
| [AlbertoTrento/ADL-Script](https://github.com/AlbertoTrento/ADL-Script) | Fork del anterior, GPL-3.0 | Hereda el panel (cuatro slots); mecanismo no descrito en su página |
| [borferkic/K1C-CFS-Power-Screen](https://github.com/borferkic/K1C-CFS-Power-Screen) | Sustituye la pantalla de la K1C (variante de Guppyscreen, MIPS) | No: solo registra su actualizador en Moonraker |

- Mecanismo: JavaScript inyectado en Fluidd, que lee el objeto `box` de Klipper y envía G-code por Moonraker
  (`BOX_MODIFY_TN_DATA` para tipo y color de material, `BOX_INFO_REFRESH` para refrescar). No toca Klipper ni la
  pantalla, así que **no compite con nada**: es un complemento de la opción 0, no una pantalla.
- Encaje con la Hi [verificado: firmware-versions.md:32 para Fluidd 1.30.0; el resto es supuesto]:
  - El panel depende de los nombres del Klipper parcheado de Creality (`box`, `BOX_*`). Kalico con
    `creality_cfs` (D16, phase6-plan) expone otros objetos y comandos [supuesto: comparar con
    `printer.objects.list` en Kalico y con las macros `T0`..`T3` ya hechas]. Habría que adaptar el JS, no usarlo tal cual.
  - Los tres son solo K1C (MIPS, firmware CFS 2.3.5.34); la Hi no aparece. El resto del Power-Script
    (sustituir `printer.cfg`, `box.cfg`, desactivar servicios de Creality) **no se debe ejecutar** en la Hi.
  - El cambio es de ficheros de Fluidd, reversible restaurando `index.html` y `sw.js`. El overlay es común a
    los slots A y B (phase1-plan §5.2), así que no se aísla por partición: instalar en la ruta de Fluidd de la
    sesión y no en la de stock si es posible [supuesto: leer la ruta real de Fluidd en la Hi].
  - Licencia GPL-3.0: se puede tomar como base citando el origen. PowerUI (tema de la pantalla) lleva licencia
    propia no comercial: no usarlo.
- Ejemplo: copiar solo `power-cfs-panel.js` a una copia de Fluidd y comprobar en el navegador si
  muestra «CFS disconnected» contra Kalico; después reescribir las llamadas a `box` por los objetos de `creality_cfs`.

## 3. Resumen comparativo

| Opción | Esfuerzo | Riesgo en la Hi | Encaja 240x320 | Convive con la UI de stock |
| - | - | - | - | - |
| 0 Solo Fluidd | nulo | nulo | — | sí (stock parado) |
| A1 Stock sobre Kalico | bajo | alto (órdenes sin respuesta) | sí | sí |
| A2 Pasarela UDS | alto | alto | sí | sí |
| B HelixScreen | medio | medio (framebuffer, glibc, instalador) | **no declarado** | no (excluyente) |
| C Guppyscreen | alto | alto | no declarado | no |
| D KlipperScreen | inviable | — | no (mín. 480x320) | no |
| E UI propia | alto | medio | sí | no |
| H PowerScreen / ADL-Screen | alto (vistas nuevas, port ARMv7 y CFS) | medio | no (diseño 800x480) | no |
| G Panel CFS en Fluidd | medio (adaptar JS) | bajo (solo ficheros web) | — (es web) | sí; complementa a 0 |

## 4. Comprobaciones de solo lectura (desde tu PC, por SSH)

Ninguna escribe en `/dev/fb0`, cambia parámetros ni toca los motores. Sube la salida a `data/captures/`.

```sh
# panel y framebuffer
cat /proc/cmdline
ls -l /dev/fb* /dev/input/ 2>&1
for f in virtual_size bits_per_pixel stride name; do echo $f; cat /sys/class/graphics/fb0/$f; done
ls /sys/class/backlight /sys/class/pwm 2>&1
# táctil: modelo, rango real y módulo cargado
cat /proc/bus/input/devices
lsmod | grep -i -E 'gt9|tlsc|disp|sunxi'
# quién usa el framebuffer y el socket (pid de display-server)
ps | grep -i -E 'display|app-server|master|lvgl|web-server' | grep -v grep
P=$(pidof display-server); cat /proc/$P/cmdline | tr '\0' ' '; echo
ls -l /proc/$P/fd; grep -E 'fb|input|lvgl|\.so' /proc/$P/maps | awk '{print $6}' | sort -u
# recursos
free -m; df -h; python3 -c "import PIL; print(PIL.__version__)" 2>&1
```

## 5. Tareas propuestas (para `docs/backlog.md`, formato del backlog de las fases)

El `backlog.md` de las fases está en otra rama y no existe aún en `dev`; por eso las tareas quedan aquí para
copiarlas al unir ramas. Siguientes ids tras B39: B40-B44. Todas U (sin analizar) salvo indicación.

### B40 — Pantalla: captura de solo lectura de hardware y procesos de la UI · S (hecha 2026-11-10, ver §1b)

- **Objetivo:** ejecutar los comandos del §4 y guardar la salida en `data/captures/<fecha>_hi-screen/`.
- **Hecho cuando:** quedan fijados (con [P]) la resolución y bpp del `fb0`, el modelo y rango del táctil,
  los ficheros y sockets que abre `display-server`, RAM libre y si hay PIL.
- **Riesgos:** ninguno; no pasar de lectura.

### B41 — Pantalla: protocolo UDS de la UI de stock · M (anulada: opción A descartada)

- **Objetivo:** documentar las peticiones que `display-server`/`master-server` envían a `/tmp/klippy_uds`
  (nombres de métodos y campos) para valorar A2.
- **Hecho cuando:** `docs/protocols/uds.md` con la lista de métodos y cuáles tienen equivalente en Kalico.
- **Riesgos:** capturarlo con un proxy sobre el socket **no es solo lectura**; empezar con `strings` sobre los
  binarios extraídos (PC) y pedir aprobación antes de cualquier proxy en la impresora.

### B42 — Pantalla: comprobar compatibilidad de binarios de HelixScreen con la Hi · S

- **Objetivo:** en el PC, con `file`/`readelf` (sin ejecutar) sobre el binario `armv7-a` que publiquen,
  ver libc enlazada y símbolos GLIBC requeridos frente a 2.29.
- **Hecho cuando:** conclusión escrita: usable tal cual / hay que recompilar / inviable.
- **Riesgos:** los binarios descargados son datos no fiables: carpeta aparte, `python -I`.

### B43 — Pantalla: prueba de dibujo en el framebuffer · M

- **Objetivo:** con la salida de B40 y con tu aprobación, escribir un fotograma de prueba en `/dev/fb0` en una
  sesión con la UI de stock parada.
- **Hecho cuando:** se ve el patrón en el panel y se documenta la forma de volver al estado normal.
- **Riesgos:** **escribe en un dispositivo**; requiere aprobación expresa. Sin efecto persistente (reinicio la
  deja como estaba) [supuesto: confirmar al probarlo].

### B44 — Pantalla: decisión de la opción · U

- **Objetivo:** elegir entre 0, A2, B/F o E con los datos de B40-B42 y anotar la decisión (D18, número por
  confirmar) en `docs/decisions.md`.
- **Hecho cuando:** decisión aprobada por ti.

### B45 — Pantalla: panel del CFS en Fluidd a partir del de la K1C · M

- **Objetivo:** valorar y adaptar `power-cfs-panel.js` (GPL-3.0) a los objetos y comandos de `creality_cfs`.
- **Hecho cuando:** mapa de las llamadas `box`/`BOX_*` del panel a Kalico, y prueba del panel contra Kalico
  (en modo batch o impresora) con tu aprobación.
- **Riesgos:** depende de que la fase 5 fije la interfaz del CFS; instalar toca ficheros de Fluidd en el overlay.
  Sin dependencia de la pantalla física.

### B46 — Pantalla: compilar PowerScreen/ADL-Screen para ARMv7 y simulador · M

- **Objetivo:** compilar el fork elegido en el simulador SDL (PC) y de forma cruzada, estático, para ARMv7
  hard-float; medir tamaño y qué vistas caben en 240x320.
- **Hecho cuando:** binario ARMv7 estático generado y capturas del simulador a 240x320 guardadas.
- **Riesgos:** ninguno en la impresora (no se ejecuta en la Hi en esta tarea).

### B47 — Pantalla: medir las coordenadas reales del táctil · S (hecha 2026-11-10: rango 240x320, sin ejes invertidos; falta descartar el giro de 180°)

- **Objetivo:** leer los eventos de `/dev/input/event0` (solo lectura, sin capturar el dispositivo) mientras
  Alejandro toca las cuatro esquinas, y anotar los valores de `ABS_MT_POSITION_X/Y`.
- **Hecho cuando:** quedan fijados el rango, la orientación y si hay ejes invertidos o intercambiados.
- **Riesgos:** con `display-server` en marcha los toques actúan sobre la UI de stock: tocar en una pantalla
  sin botones en las esquinas (p. ej. la de inicio) y con la impresora en reposo.
