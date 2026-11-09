# Firmware oficial

Las imágenes OTA de Creality **no se versionan** (son grandes y propietarias). Se guardan en `ota/` y sus
extracciones en `extracted/`; ambas carpetas están en `.gitignore`.

## Imágenes en uso

| Fichero | Modelo | Build | Tamaño | SHA-256 |
| - | - | - | - | - |
| `CR4NU200360C20_ota_img_V1.1.0.60.img` | Hi (**instalada**) | 2025-11-26 | 125915648 | `d900b9a5a1411c65b4249d7caf11183790f5adbb11c02ff9579f557685cf6936` |
| `CR4NU200360C20_ota_img_V1.1.0.74.img` | Hi (última) | 2026-07-24 | 125784576 | `e58fdf4922cb65220a0b4e760e8d31e23eaae25587141b36eaac6f56a33333b6` |
| `CR0CN200400C10_R_202610280949_ota_img_V1.1.8.3.img` | K2 (familia) | 2026-10-28 | 150176256 | `e254dc130a9e51b567bc105340ee32a75cc5ccc44f2efb95c7d07fb699df9bbc` |

## Imágenes retiradas

Ya analizadas en [docs/analysis/firmware-versions.md](../docs/analysis/firmware-versions.md). Se eliminaron el
2026-11-09; los checksums permiten verificar una copia si vuelve a hacer falta.

| Fichero | Build | Tamaño | SHA-256 |
| - | - | - | - |
| `CR4NU200360C20_ota_img_V1.1.0.50.img` | 2025-08-06 | 125915648 | `1bbc46da6bcc26f8152f278dd546f97339a843b63b584a6b78fd3f227391a89d` |
| `CR4NU200360C20_ota_img_V1.1.0.65.img` | 2026-01-23 | 125784576 | `9060de00ebcf8fb9df3401fff924861e2af608fab85e9f9440708d6c97eaa16a` |
| `CR4NU200360C20_ota_img_V1.1.0.73.img` | 2026-06-23 | 125784576 | `2b45e55bc9bd574b7759c7e78a0578d42193d2ff801b797f985c636de12ee6f4` |

Comprobar una imagen:

```bash
sha256sum firmware/ota/*.img
```

## Extraer

Requiere 7-Zip (`7z` en el PATH):

```bash
python tools/fwextract.py ota firmware/ota/CR4NU200360C20_ota_img_V1.1.0.60.img firmware/extracted/hi-v1.1.0.60
python tools/fwextract.py bootimg firmware/extracted/hi-v1.1.0.60/outer/kernel firmware/extracted/hi-v1.1.0.60/boot
python tools/fwextract.py mcu-dict firmware/extracted/hi-v1.1.0.60/rootfs/usr/share/klipper/fw/F018/mcu0_110_G32-mcu0_020_000.bin
```

Formato del paquete: CPIO `newc` de SWUpdate con `sw-description`, `uboot`, `kernel` (Android boot image con
zImage gzip y DTB) y `rootfs` (SquashFS zlib). Actualización A/B por `/dev/by-name/{bootA,bootB,rootfsA,rootfsB}`;
`sw-description` no comprueba el modelo.

Los ficheros extraídos son datos no confiables: se leen y analizan, nunca se ejecutan.
