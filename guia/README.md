# Guía de usuario del CFW de la Creality Hi

Guía para instalar, usar y deshacer Kalico en la Creality Hi (F018) sobre el Tina de stock. Es un **esqueleto**:
resume lo que ya existe y enlaza a los planes técnicos en lugar de copiarlos.

> **Aviso:** nada de esto se ha ejecutado todavía en la impresora [verificado: [docs/ESTADO.md](../docs/ESTADO.md)].
> Los pasos están probados solo contra una impresora simulada (`scripts/selftest.sh`) y en modo batch en PC.
> Hasta que se pruebe en la Hi, toda afirmación sobre su comportamiento real es [supuesto].

## Páginas

| Página | Contenido | Madurez |
| - | - | - |
| [instalar.md](instalar.md) | Requisitos, paso 0 de solo lectura, instalación y arranque de una sesión | Borrador |
| [stock.md](stock.md) | Vuelta al Klipper de stock | Borrador |
| [config.md](config.md) | Ficheros `.cfg` por fase y cómo elegir cuál arranca | Borrador |
| [macros.md](macros.md) | Comandos y macros (homing, limpieza, malla, impresión) | Esqueleto |
| [cfs.md](cfs.md) | CFS: bus, comandos, cambio de filamento | Esqueleto |
| [problemas.md](problemas.md) | Síntoma, causa y solución | Esqueleto |
| [faq.md](faq.md) | Preguntas cortas | Esqueleto |

## Convenciones

- `[verificado: fichero:línea]`: leído en el código o comprobado con una prueba. `[supuesto]`: sin comprobar en la
  impresora. Si una página no marca una afirmación, trátala como [supuesto].
- Las órdenes con `<ip>` se ejecutan desde el PC; el resto, en la impresora por SSH.
- Seguridad: las pruebas empiezan en solo lectura. No se escribe ningún parámetro de los motores
  (`SYS_PARAM`, `FLASH_PARAM`, calibraciones, `MOTOR_FLASH_PARAM COMMIT=1`) sin aprobación expresa.

## Documentación técnica (no se duplica aquí)

- [docs/roadmap.md](../docs/roadmap.md) y [docs/ESTADO.md](../docs/ESTADO.md): fases y estado.
- [docs/decisions.md](../docs/decisions.md): decisiones D1 a D17.
- [docs/hardware.md](../docs/hardware.md) y [docs/protocols/](../docs/protocols/): hardware y protocolos.
- Planes: [fase 1](../docs/phase1-plan.md), [2](../docs/phase2-plan.md), [3](../docs/phase3-plan.md),
  [4](../docs/phase4-plan.md), [5](../docs/phase5-plan.md), [6](../docs/phase6-plan.md).
- [docs/backlog.md](../docs/backlog.md): tareas pendientes.
