# Preguntas frecuentes

**¿Es seguro? ¿Puedo volver a stock?** El procedimiento actual no escribe en flash y se deshace con
`hi_kalico.sh stop` o reiniciando ([stock.md](stock.md)). Aún no se ha probado en la Hi [verificado:
[ESTADO.md](../docs/ESTADO.md)].

**¿Se reflashean las MCU?** No: Kalico habla con el firmware de stock [verificado: README.md].

**¿Por qué no se instala el CFW de la K2 tal cual?** El kernel de la K2 no soporta la pantalla ni el `uart4` de
la Hi, y `z_align` y `box` de la K2 no valen ([k2-port-feasibility.md](../docs/analysis/k2-port-feasibility.md)).

**¿Qué pasa con la pantalla?** Se queda sin servicio mientras corre Kalico. Se empieza con consola SSH y Fluidd
(D7); un sustituto para el panel 240x320 está sin analizar.

**¿Puedo imprimir ya?** No: nada se ha probado en la Hi. El objetivo es una pieza multicolor con el CFS
([roadmap.md](../docs/roadmap.md)).

**¿Garantía?** Proyecto independiente, sin relación con Creality [verificado: README.md]. [supuesto] Modificar el
software puede afectar a la garantía.

**¿Otras versiones de firmware?** Solo 1.1.0.60 está contrastada; diferencias con otras en
[firmware-versions.md](../docs/analysis/firmware-versions.md).

**¿Dónde se reportan fallos?** En los issues de [Creality-Hi-CFW](https://github.com/ale87jan/Creality-Hi-CFW/issues).
