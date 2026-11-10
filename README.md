# Creality Hi CFW

Firmware alternativo para la **Creality Hi** (F018): Kalico (fork de Klipper; en concreto, la versión de
[Jacob10383](https://github.com/Jacob10383/kalico) para la K2 Plus) con módulos abiertos en lugar del Klipper
antiguo y los módulos cerrados de Creality.

> **Estado:** investigación terminada, desarrollo sin empezar. Nada de este repositorio está listo para
> instalarse en una impresora.

## Enfoque

- Portar el CFW de la K2 Plus ([Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware)):
  la K2 y la Hi comparten SoC, sistema, MCU, bus RS-485, motores de lazo cerrado, sonda y CFS.
- Conservar el sistema Tina de stock: el kernel de la K2 no soporta la pantalla ni el `uart4` de la Hi.
- No reflashear las MCU: Kalico habla con su firmware de stock.
- Instalar en la partición A/B libre para poder volver a stock.

Detalles en [docs/analysis/k2-port-feasibility.md](docs/analysis/k2-port-feasibility.md) y plan en
[docs/roadmap.md](docs/roadmap.md).

## Repositorios

| Repo | Contenido |
| - | - |
| `Creality-Hi-CFW` (este) | Investigación, documentación, herramientas y, más adelante, instalador y releases |
| [Creality-Hi-Kalico](https://github.com/ale87jan/Creality-Hi-Kalico), fork de [Jacob10383/kalico](https://github.com/Jacob10383/kalico) | Código: Kalico y módulos de la Hi |

Mismo reparto que el CFW de la K2 ([docs/decisions.md](docs/decisions.md), D3).

## Estructura de este repo

```text
guia/        guía de usuario (esqueleto)
docs/        hardware, protocolos, análisis y hoja de ruta
data/        capturas de la impresora y datos extraídos de las OTA
firmware/    imágenes OTA y extracciones (no versionadas)
tools/       herramientas de extracción y sondeo, con tests
```

## Herramientas

| Herramienta | Dónde se ejecuta | Uso |
| - | - | - |
| `tools/fwextract.py` | PC (Python 3, 7-Zip) | Extraer imágenes OTA, diccionarios de MCU, kernel, DTB |
| `tools/hi_probe.py` | Impresora (Python 3.9 + pyserial de stock) | Leer diccionarios de MCU y parámetros de los motores, solo lectura |

Tests sin hardware:

```bash
python -m unittest discover -s tools/tests -v
```

## Documentación

- [guia/](guia/README.md): guía de usuario (instalar, volver a stock, configuración, macros, CFS, problemas, FAQ). Esqueleto.
- [docs/hardware.md](docs/hardware.md): SoC, puertos serie, MCU, motores, sonda y CFS.
- [docs/protocols/rs485.md](docs/protocols/rs485.md): trama, direcciones y funciones de motores y CFS.
- [docs/protocols/mcu.md](docs/protocols/mcu.md): comandos de las MCU y compatibilidad con Kalico.
- [docs/analysis/firmware-versions.md](docs/analysis/firmware-versions.md): cambios entre V1.1.0.50 y V1.1.0.74.
- [docs/decisions.md](docs/decisions.md): decisiones de diseño.
- [RESEARCH.md](RESEARCH.md): metodología, fuentes y licencias.

## Licencia

GPLv3 ([LICENSE](LICENSE)). Proyecto independiente, sin relación con Creality.
