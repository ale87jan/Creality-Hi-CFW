# Fase 3 — Sonda de presión y homing de Z

Análisis del 2026-11-10, hecho sin impresora y **más ligero que el de la fase 2**: cubre la compatibilidad
estática del módulo y el camino de `G28 Z`; no he leído entera la lógica de armado y disparo de `prtouch.py`.
Alcance: que Kalico use la sonda de presión de la boquilla (CS1237) para el homing de Z y `PROBE`. Fuera:
alineación de los dos Z (`z_align`, fase 4), limpieza de boquilla (`nozzle_clear`, fase 4) y malla de cama.

Notación como en [phase2-plan.md](phase2-plan.md): `fork:`, `stock:`, `captura:`; cada afirmación lleva
`[verificado: ...]` o `[supuesto: ...]`.

**Depende de las fases 1 y 2**, ninguna probada aún en la Hi. La sonda necesita X/Y con homing para ir al
centro de la cama.

## 1. Conclusiones

1. El `prtouch.py` del fork (K2) es compatible con la Hi **sin tocar código**: los 17 mensajes `prtouch` que usa
   existen con la misma firma en las dos MCU, sus pines por defecto son los de la Hi y ya contempla dos motores
   Z en cinemática cartesiana (§2).
2. Carga en modo batch contra los diccionarios reales de la Hi y emite la configuración esperada (§2).
3. El stock usa `prtouch_v3`, un `.so` cerrado, con opciones que el módulo de la K2 no tiene
   (`prth_tmp_comp`, `prth_max_chps`, `prth_min_fans`). El comportamiento no será idéntico (§3).
4. El `G28 Z` del `homing.py` del fork funciona sin escáner y sin `z_align`, pero llama a `NOZZLE_CLEAN`, que hay
   que definir (§4).
5. Es la fase con más riesgo físico: la boquilla toca la cama. El plan empieza con la sonda armada y Z lejos de
   la cama (§6).

## 2. Compatibilidad del módulo

| Comprobación | Resultado |
| - | - |
| Comandos y respuestas `prtouch` | `config_/start_/stop_prtouch_step`, `config_/start_/stop_/read_prtouch_pres`, `ack_prtouch`, `resault_prtouch_pres`: misma firma en `mcu` y `nozzle_mcu` de la Hi [verificado: fork:klippy/extras/prtouch.py:337-374 frente a fork:test/hi/mcu.dict y nozzle_mcu.dict] |
| Pines por defecto | `step_swap_pin: !PC7`, `pres_swap_pin: nozzle_mcu:PA15`, `pres_cs0_pin: nozzle_mcu:PB13, nozzle_mcu:PB14` [verificado: fork:klippy/extras/prtouch.py:109-110, 184-186]; son los de la Hi [verificado: captura:toolhead.cfg:75-79] |
| Dos motores Z | `stepper_z1` va en el hueco `oid_xstp` si la cinemática no es corexz [verificado: fork:klippy/extras/prtouch.py:320-330]. Que el firmware de la Hi lo interprete igual que el de la K2 es un [supuesto: el stock lo hace dentro del `.so`; comprobar en el paso 3.3 que paran los dos motores] |
| Carga en batch | Con la config de la fase 1 más `[prtouch]` emite `config_prtouch_step oid_xstp=<z1> oid_zstp=<z> swp_pin=PC7` y `config_prtouch_pres swp_pin=PA15 clk_pin=PB13 sdo_pin=PB14` [verificado: ejecución en batch del 2026-11-10; falta convertirla en test, B22] |
| `PC7` compartido | Es `endstop_pin` de X y `step_swap_pin` de la sonda: hay que añadirlo a `[duplicate_pin_override]`. El reenvío de `io_remap` solo está activo durante el homing de X ([phase2-plan.md](phase2-plan.md) §4) |

## 3. Diferencias con el stock

| | Stock Hi (`prtouch_v3`) | Fork (`prtouch`) |
| - | - | - |
| Implementación | `prtouch_v3_wrapper.cpython-39.so`, cerrado [verificado: stock:klippy/extras/prtouch_v3.py] | Python abierto, 1096 líneas |
| Compensación térmica | `prth_tmp_comp: 26, 300, 0, 0.20` [verificado: captura:toolhead.cfg:81] | `thermal_expansion` (mm/°C) en `PRTOUCH_HOME` [verificado: fork:config/k2/prtouch.cfg] |
| Ventilador mínimo, canales | `prth_min_fans: 0.65`, `prth_max_chps: 8` | No existen |
| Muestras | `samples: 3`, `average`, tolerancia 0.5 | Mismas opciones estándar |
| Umbrales | `pres_tri_hold: 4000, 10000, 500` | Misma opción, mismo valor en la K2 |
| Geometría | — | `home_xy` por defecto 175, 175 y zona de frotado de la K2 [verificado: fork:klippy/extras/prtouch.py:133, 149-152]: en la Hi, `home_xy: 130, 130`; **no usar `PRTOUCH_SCRUB`** |

Sin el código del `.so` no se puede saber qué hace exactamente `prth_tmp_comp` ni `prth_min_fans`
[supuesto: comparar el Z=0 que da Kalico con el de stock en frío y en caliente, paso 3.5].

## 4. Camino de `G28 Z`

Stock [verificado: captura:sensorless.cfg:188-204; stock:klippy/extras/homing.py:414-425]:
va al centro (`G1 X130 Y130`), fija `SET_KINEMATIC_POSITION Z=305`, y `G28 Z` ejecuta antes la alineación de los
dos Z (`run_G28_two_Z`, con `[z_align]` y los fotoeléctricos `PB15`/`PB14`) y después el homing con la sonda
(`endstop_pin: probe:z_virtual_endstop`, 5 mm/s). Al terminar sube a Z=10.

Fork [verificado: fork:klippy/extras/homing.py:724-735, 975-989, 1128-1165]:

- Ordena Y, X y después Z; si X/Y no tienen homing los hace antes.
- Con `register_as_probe: True` ejecuta `NOZZLE_CLEAN` antes de bajar: hay que definir esa macro. En la fase 3,
  vacía; la limpieza real llega con `nozzle_clear` (fase 4).
- Va al centro de `[bed_mesh]` o de los límites de X/Y, y baja con la sonda.
- Sin `[cartographer]`, `_is_probe_model_ready` devuelve verdadero; sin `[z_align]` no hay alineación previa.
- Después sube a una altura fija.

Diferencia importante: en la fase 3 **no hay alineación de los dos Z**. Si el puente está inclinado, el homing
en el centro sigue siendo válido, pero la inclinación no se corrige hasta la fase 4.

## 5. Qué se puede hacer sin impresora

| Trabajo | Depende de la Hi |
| - | - |
| `config/hi/phase3.cfg`: `[prtouch]` con los valores de stock, `stepper_z` con `probe:z_virtual_endstop`, `NOZZLE_CLEAN` vacía, `PC7` en `duplicate_pin_override` | No |
| Test en batch: carga, `config_prtouch_*` correctos, `G28 Z` sin X/Y con homing no mueve Z | No |
| Reestructurar `config/hi/` para que cada fase no tenga que anular opciones de la anterior (el `endstop_pin` de `stepper_z1` de la fase 1 no se puede quitar desde un `include`) | No |
| Umbrales, velocidades, compensación térmica | **Sí** [supuesto] |

## 6. Plan en la impresora (después de la fase 2)

Cama y boquilla frías y limpias. Z siempre lejos de la cama hasta el paso 3.4.

| Paso | Acción | Riesgo | Criterio |
| - | - | - | - |
| 3.1 | En stock: `PROBE` en el centro 5 veces, en frío; anotar Z y dispersión | El de stock | Referencia para comparar |
| 3.2 | Kalico: arrancar con `[prtouch]`; `QUERY_PROBE` | Ninguno | Carga sin errores; sonda no disparada |
| 3.3 | Con Z a más de 50 mm de la cama: `PROBE` y tocar la boquilla con un objeto blando | Bajo: si no dispara, Z baja hasta agotar el recorrido de la orden; mano en el interruptor | Z se para al tocar; paran los dos motores Z |
| 3.4 | `G28 X Y`, centro, `G28 Z` a 5 mm/s con la mano en el interruptor | **Choque con la cama si no dispara** | Se para al contacto; Z=0 coherente |
| 3.5 | `PROBE` 5 veces en frío y con la boquilla a 170 °C; comparar con 3.1 | Bajo | Dispersión y Z similares a stock |

### Hecho el 2026-11-10

Las tres primeras filas están hechas en el fork: `config/hi/phase3.cfg`, `test/test_hi_prtouch.py` y el reparto
de `config/hi/` en `base.cfg` y `motors.cfg`. En batch, la MCU principal recibe `config_prtouch_step` con los
OID de `stepper_z` y `stepper_z1` y `swp_pin=PC7`, y la de la boquilla `config_prtouch_pres` con `PA15`, `PB13`
y `PB14` [verificado: fork:test/test_hi_prtouch.py]. Con `startup_writes: none`, `G28`, `G28 Z`, `PROBE` y
`G1 Z5` se rechazan sin generar pasos. La config usa los valores de `[prtouch_v3]` de la impresora
(`samples: 3`, `average`, 10 reintentos) [verificado: captura:printer-config/printer.cfg].

## 7. Decisiones que necesito

1. **Módulo de la sonda**: usar el `prtouch.py` de la K2 tal cual, solo con config (recomendada: no hace falta
   tocar código y los arreglos de upstream llegan solos), o una copia aparte como en D8. **Cerrada: D11, tal cual** (2026-11-10).
2. **Cerrada: D12, `z_align` antes que la sonda** (2026-11-10). Orden de las fases 3 y 4: sonda antes que `z_align` (como está en el roadmap; el homing de Z funciona sin
   alinear) o `z_align` antes, para que el primer contacto con la cama sea con el puente ya alineado.
3. **`NOZZLE_CLEAN` en la fase 3**: macro vacía (recomendada) o portar antes `nozzle_clear`.

## 8. Riesgos

| Id | Riesgo | Mitigación |
| - | - | - |
| R1 | La sonda no dispara y la boquilla empuja la cama | Pasos 3.3 antes que 3.4; 5 mm/s; mano en el interruptor; corriente de Z de stock |
| R2 | Solo para un motor Z al disparar | Paso 3.3 lejos de la cama |
| R3 | Z=0 distinto al de stock por la compensación térmica | Paso 3.5; no imprimir hasta comparar |
| R4 | `PC7` queda con el reenvío de `io_remap` activo y la sonda lee el final de carrera de X | `io_remap` se apaga al terminar el homing de X y en cualquier error de comando |
| R5 | Puente inclinado sin `z_align` | Decisión 2; comprobar a ojo antes de 3.4 |
