# Resultados estimados de las pruebas P1–P6

> **Son estimaciones, no mediciones.** Salen de la simulación del firmware (prueba P0) y de las hojas de datos de los sensores. Muestran lo que se espera de la garra mientras no estén hechas las pruebas físicas. Cuando las hagan, corran `python testing/analizar_pruebas.py`: el reporte real queda en `reporte_pruebas.md`, en esta misma carpeta, y reemplaza a este archivo. Estos son los mismos valores de la diapositiva 9, marcados ahí como «Resultado estimado».

## Resumen

| Prueba | Criterio de éxito | Estimado | ¿Cumple? |
|---|---|---|:---:|
| P1 Balanza | Error ≤ ±2 g | ±1,2 g (error máximo) | Sí |
| P2 Detección | 20/20 detectados y 0 falsos | 20 / 20, 0 falsos | Sí |
| P3 Material | Metal ≥ 90 %, plástico ≥ 80 % | 90 % / 80 % | Justo en la meta |
| P4 Agarre | ≥ 95 % en su contenedor | 93 % (28 de 30) | No |
| P5 Tiempo de ciclo | Media y p95 ≤ 15 s | Media 9,1 s, p95 12,4 s | Sí |
| P6 Continuidad | ≤ 1 % de telemetría perdida | 0,4 % | Sí |

## De dónde sale cada valor

**P1 · Balanza (±1,2 g).** Celda de 1 kg con HX711 a 10 muestras por segundo, calibrada con 100 g (`CAL 100`). Con un factor del orden de 400 cuentas por gramo, como en la simulación, una cuenta equivale a 0,0025 g, así que la resolución no limita. Lo que pesa es la no linealidad y la fluencia de la celda (del orden de 0,05 % de la escala, unos 0,5 g) y la deriva térmica entre tara y medición. Sumado, el error máximo esperado en 25 mediciones de 5 a 100 g es de alrededor de ±1,2 g. En la simulación, `CAL 100` dejó un factor de 399,3 contra 400 real (error de 0,2 %).

**P2 · Detección (20 / 20, 0 falsos).** El ciclo arranca con el HC-SR04 a menos de 12 cm o, si no hay eco, con una masa sostenida de 5 g o más (respaldo agregado tras la falla F5). Si los 20 residuos están en el rango del sistema (5–100 g), todos se detectan por una vía o la otra. Las 10 pasadas de mano no dejan masa en la bandeja: el firmware las descarta como `FALSA_DETECCION` sin mover el brazo, que el protocolo cuenta como correcto. En la simulación, el caso #6 (mano) terminó así.

**P3 · Material (90 % metal / 80 % plástico).**
- *Metal, 9 de 10.* El LJ12A3-4 detecta acero a 4 mm, pero en aluminio su alcance baja a cerca de un 40 % (unos 1,6 mm). Se espera que una lata de aluminio que quede apoyada lejos de la ventana del sensor no se detecte y termine en descarte.
- *Plástico, 8 de 10.* El LJC18A3 ve bien los plásticos gruesos (botellas PET, tapas), pero un vaso o un envase de yogur de pared delgada puede quedar bajo el umbral y terminar en descarte. Se esperan 2 así.
- *Descarte.* Un cartón húmedo puede activar el capacitivo y clasificarse como plástico: no baja el acierto del plástico, pero sí el del descarte.

**P4 · Agarre (93 %, 28 de 30).** La pinza con SG90 y el FSR confirman el agarre; si el FSR no llega al umbral, el firmware hace un segundo intento (`MAX_INTENTOS = 2` en `config.h`) y luego registra `FALLA_AGARRE`. Se esperan 2 fallas: una botella PET redonda que resbala entre los dedos y un envase liviano que no aprieta el FSR. Este es el punto más débil del prototipo y el candidato natural a la falla F7 del protocolo.

**P5 · Tiempo de ciclo (media 9,1 s, p95 12,4 s).** En la simulación, el ciclo medio de los residuos correctos fue 7,5 s y los que necesitaron un segundo intento llegaron a 10,2–10,4 s. La simulación no modela peso, roce ni la inercia de los MG996R, así que se suma cerca de un 20 %: media de unos 9 s, y el p95 lo marcan los ciclos con reintento (unos 12,4 s). Ambos quedan bajo los 15 s.

**P6 · Continuidad (0,4 %).** En 30 minutos, con telemetría cada 500 ms, se envían unos 3.600 paquetes. Desconectar el USB y que el gateway se reconecte toma unos 8 s, es decir, unos 16 paquetes: 0,4 % del total. Fuera del corte se espera 0 %, como en la prueba P0 de la cadena gateway → base (197 paquetes, 0 perdidos).

## Falla esperada y mejora propuesta

- **Falla esperada (F7):** agarre de residuos redondos o resbalosos (93 %, bajo la meta del 95 %).
- **Causa probable:** los dedos impresos en PLA tienen poca fricción y el FSR necesita una presión mínima para confirmar el agarre.
- **Mejora propuesta:** almohadillas de TPU en la cara de los dedos para aumentar la fricción, y recalibrar el cierre (`MOVER P …` → `GUARDAR CERRADA`) o bajar el umbral del FSR (comando `FSR <valor>`). Si el plástico queda bajo el 80 %, sumar un segundo criterio de densidad aparente (masa / altura medida por el ultrasónico).

## Qué hacer con este archivo

1. Hagan las pruebas P1–P8 con el robot según `testing/protocolo_pruebas.md`.
2. Corran `python testing/analizar_pruebas.py` y revisen `reporte_pruebas.md`.
3. Reemplacen los valores de la diapositiva 9, cambien «Resultado estimado» por «Resultado» y borren la nota amarilla.
4. Anoten en el protocolo la falla F7 real, aunque sea distinta a la esperada.
