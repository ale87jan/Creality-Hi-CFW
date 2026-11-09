# Datos

## `captures/` — leídos en la impresora

| Carpeta | Contenido |
| - | - |
| `2026-11-09_hi-v1.1.0.60/` | `bed_mcu.json`: diccionario de la MCU de la cama (`ttyS4`). `motors.json`: dirección y 77 parámetros de los motores 0x81 (X) y 0x82 (Y), con el valor decodificado y los bytes crudos. `printer-config/`: config de Klipper que corre en la impresora |

- `bed_mcu.json` y `motors.json`: generados con `tools/hi_probe.py` (solo lectura) y Klipper de stock parado.
- `printer-config/`: los 15 `.cfg` copiados de la impresora (`printer_data/config`). Son la config reorganizada
  del usuario para el Klipper de stock (`v1.1.0.60-cfw.1`), idéntica a `ale87jan/Creality-Hi-Custom-Klipper`,
  rama `dev`, commit `f2747f8` (2026-11-08), carpeta `config/F018_CR4NU200360C20`. Ese repo tiene además
  `cfs_materials.cfg` y `original/` (config de stock). Usa comandos del Klipper parcheado de Creality: es la
  base para escribir la config de Kalico, no se carga tal cual.

## `derived/` — extraídos de las imágenes OTA

| Carpeta | Contenido | Herramienta |
| - | - | - |
| `mcu-dictionaries/hi/` | Diccionarios de las MCU principal y boquilla (V1.1.0.60) y de la cama (copia de la captura) | `fwextract.py mcu-dict` |
| `mcu-dictionaries/k2/` | Diccionarios de la OTA de la K2 V1.1.8.3: F008 (K2 Plus), F012 (K2 Pro), F038, K1 | `fwextract.py mcu-dict` |
| `dtb/` | Device tree de la Hi V1.1.0.74 (idéntico al de V1.1.0.60) y de la K2 V1.1.8.3, como texto | `fwextract.py bootimg` + `dtb` |
| `kernel-config/` | `.config` del kernel (IKCONFIG) de la Hi V1.1.0.74 y de la K2 V1.1.8.3 | `fwextract.py bootimg` |
| `strings/` | **Solo local, no se publica.** `strings` ordenados de los módulos Cython de Creality (Hi .60/.74 y K2) y de firmwares del CFS | `strings \| sort -u` |
| `diffs/` | Diff de los `.py` de klippy entre la K2 V1.1.8.3 y la Hi V1.1.0.74 | `diff -r` |

Ver la nota de licencias de [RESEARCH.md](../RESEARCH.md).
