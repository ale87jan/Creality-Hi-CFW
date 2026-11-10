# Instalar

Instalación escalonada, sin escribir en flash (decisión D5 en [decisions.md](../docs/decisions.md)). Detalle y
razones: [phase1-plan.md §5.3, §6 y §8](../docs/phase1-plan.md).

## Requisitos

- Creality Hi modelo F018 con firmware **1.1.0.60**; `hi_install.sh` rechaza otro modelo o versión salvo
  `--any-version` [verificado: scripts/hi_install.sh:25-26].
- SSH a la impresora. `scp -O` es obligatorio (no hay sftp-server) y un fichero por llamada [verificado:
  CLAUDE.md].
- Python 3.9 de stock, sin git ni gcc: por eso se instala un `.tar.gz` con el `c_helper.so` ya compilado (D6)
  [verificado: [phase1-plan.md §6](../docs/phase1-plan.md)].
- Impresora en reposo y fría.

## Escalones

| Escalón | Qué cambia | Vuelta a stock |
| - | - | - |
| 1. Ficheros | `hi_install.sh` copia el paquete a `/mnt/UDISK/kalico-hi`; nada se ejecuta | `hi_restore.sh --purge` |
| 2. Sesión | `hi_kalico.sh start` para los servicios de Creality y lanza Kalico; nada persistente | `hi_kalico.sh stop` o reiniciar |
| 3. Fluidd | `hi_kalico.sh start --ui` apunta el Moonraker de stock a Kalico | Igual que el 2 |

No se toca flash, overlay, variables de U-Boot ni parámetros de motores [verificado: scripts/hi_install.sh:1-17].

## 0. Inventario de solo lectura

Ejecutar `scripts/hi_step0.sh` en la impresora y subir el resultado a `data/captures/`. Valores esperados por
sección: [phase1-plan.md, paso 0](../docs/phase1-plan.md). Si algo no coincide, parar.

## 1. Preparar el paquete (en el PC)

1. Compilar `c_helper.so`: `scripts/build_chelper.sh` (Docker) [verificado: carga en ARMv7 emulado con glibc 2.28].
2. Generar el paquete: `scripts/make_bundle.sh <ruta a Creality-Hi-Kalico>` → `build/kalico-hi-<commit>.tar.gz`
   y su `.sha256` [verificado: scripts/make_bundle.sh].

## 2. Instalar y arrancar (en la impresora)

```sh
sh hi_install.sh --dry-run /tmp/kalico-hi-<rev>.tar.gz   # comprueba todo y no escribe
sh hi_install.sh /tmp/kalico-hi-<rev>.tar.gz
hi_kalico.sh start --dry-run
hi_kalico.sh start
hi_kalico.sh status
```

Con Kalico en marcha la pantalla de la impresora queda sin servicio hasta `stop` [verificado:
[phase1-plan.md §5.3](../docs/phase1-plan.md)]. Pruebas siguientes (temperaturas, ventiladores, Z): tabla de
pasos 1 a 13 del mismo plan.

## Pendiente

- Instalación en la partición A/B libre y arranque automático: solo diseñado
  ([phase1-plan.md §9](../docs/phase1-plan.md)). El overlay es común a los dos slots, así que el slot libre no
  aísla cambios de ficheros [verificado: phase1-plan.md, hallazgos].
