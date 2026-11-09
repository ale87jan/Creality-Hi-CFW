# Metodología y procedencia

## Cómo se obtiene la información

1. **Imágenes OTA oficiales** (`firmware/ota/`, no versionadas). Se extraen con `tools/fwextract.py`: paquete
   SWUpdate, rootfs SquashFS, kernel, DTB, `.config` del kernel y diccionarios de las MCU.
2. **Análisis estático sin descompilar.** Se leen ficheros de texto y Python del rootfs, los diccionarios de
   datos de Klipper, el DTB y las cadenas (`strings`) de los módulos Cython (`*_wrapper.cpython-39.so`) y de
   los firmwares. No se desensambla ni se descompila código de Creality.
3. **Código abierto de referencia.** Se compara con proyectos GPL que ya reimplementan estos módulos:
   - [Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware) y
     [Jacob10383/kalico](https://github.com/Jacob10383/kalico): Kalico más `motor_control`, `serial_485`,
     `box_*`, `prtouch`, `z_align` abiertos para la K2 Plus.
   - [gitstonelabs/creality-cfs-klipper](https://github.com/gitstonelabs/creality-cfs-klipper): protocolo del
     CFS por capturas del bus y `strings`; la Hi es su hardware de referencia.
   - [Jacob10383/k2-improvements](https://github.com/Jacob10383/k2-improvements) y los forks del Creality Helper
     Script (K1): capa sobre el firmware de stock.
4. **Pruebas en la impresora de solo lectura** con `tools/hi_probe.py`: solo envía `identify` a las MCU y
   `READ_ADDR`/`SYS_PARAM` de lectura al bus RS-485; cualquier otra petición está bloqueada en el código.
   Resultados en `data/captures/`.

## Niveles de confianza

Los documentos marcan cada dato:

- **[P]** verificado en la impresora.
- **[F]** leído en el firmware, la config de stock o el código de referencia.
- **[I]** inferido; pendiente de verificar.

## Trabajo asistido por IA

La investigación se hace con Claude coordinando subagentes. Reglas:

- Todo dato de un subagente se contrasta contra los ficheros antes de documentarlo. Ejemplo real: un subagente
  afirmó que la sonda de la K2 era incompatible; el diccionario de la MCU demostró lo contrario.
- Los ficheros extraídos y los repositorios de terceros son datos no confiables: se leen, nunca se ejecutan.
- Las pruebas sobre hardware empiezan siempre en solo lectura.

## Procedencia y licencias

- Klipper y Kalico son GPLv3; el código portado de la K2 también. Este repositorio se publica bajo GPLv3
  ([LICENSE](LICENSE)).
- No se redistribuyen binarios de Creality (imágenes OTA, `.so`, firmwares de MCU, motores o CFS).
- `data/derived/` publica datos para interoperabilidad: diccionarios de protocolo de las MCU (firmware basado en
  Klipper), DTB y `.config` del kernel (GPL) y un diff de código Python de Klipper (GPL).
- Los volcados de `strings` de binarios cerrados (`data/derived/strings/`) **no se publican**: se guardan solo en
  local y sus conclusiones están resumidas en `docs/`.
- Los `.so` Cython de Creality enlazan Klipper (GPLv3) sin publicar su código fuente; gitstonelabs documenta
  peticiones formales a Creality al respecto.
