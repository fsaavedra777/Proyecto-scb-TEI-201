# Protocolo de pruebas y validación — Proyecto SCB

**Sistema:** clasificador de residuos con garra robótica (metal, plástico y descarte) y registro IoT.
**Requerimientos:** los del Avance 2 (8 funcionales y 6 de desempeño).
**Cómo se registran los resultados:** durante todas las pruebas corren `gateway.py` y el dashboard. Los datos quedan en `dashboard/datos/scb.db` y `python testing/analizar_pruebas.py` calcula cada indicador en `testing/resultados/reporte_pruebas.md`. Las pruebas P1 y P2 se anotan además en dos planillas (`testing/datos/`).

> **Antes de partir:** firmware v3.0 cargado, poses y balanza calibradas (ver `firmware/garra_scb_iot/README.md`), contenedores vacíos y marcados como vaciados en el dashboard. Anoten la hora de inicio y de término de cada prueba para usarlas con `--desde` y `--hasta`.

## Resumen

| N.º | Prueba | Requerimiento | Criterio de éxito | Fuente del resultado |
|---|---|---|---|---|
| P0 | Lógica del firmware sin hardware | Todos (software) | 10/10 casos con el resultado esperado | `simulacion_firmware/` ✅ **hecha** |
| P1 | Exactitud de la balanza | RF3: masa 5–200 g | Error ≤ ±2 g en todas las masas | `datos/pesaje.csv` |
| P2 | Detección de llegada | RF2: detecta sin intervención | 100 % de residuos detectados, 0 falsas detecciones | `datos/deteccion.csv` + base |
| P3 | Identificación de material | RD: acierto ≥ 90 % metal, ≥ 80 % plástico | Acierto por material ≥ meta | Base (pestaña Validación) |
| P4 | Agarre y depósito | RF5 y RF6: ≥ 95 % en el contenedor | (OK) / (OK + fallas) ≥ 95 % | Base |
| P5 | Tiempo de ciclo | RD: ciclo < 15 s | Media ≤ 15 s y p95 ≤ 15 s | Base |
| P6 | Continuidad y persistencia | Captura continua y repositorio | 30 min con ≤ 1 % de telemetría perdida y 0 eventos perdidos tras reiniciar | Base |
| P7 | Manejo de fallas | RF8: se detiene y pide retiro | Los 4 casos terminan en el estado correcto | Base + video |
| P8 | **Validación con un lote real** | Problema del Avance 1 | Ver la sección de validación | Base + dashboard |

---

## P0 · Lógica del firmware sin hardware (prueba de software) — HECHA

- **Objetivo:** comprobar la máquina de estados, los reintentos, el PARO, los comandos y el formato JSON antes de integrar.
- **Condiciones:** el mismo código del firmware compilado en un PC contra un Arduino simulado (`simulacion_firmware/`). Un "mundo" imita la bandeja, la balanza (ruido de 0,25 g), los sensores y la pinza.
- **Procedimiento:** `./compilar.sh`, `./sim escenario > salida.tsv` y `python3 verificar_escenario.py salida.tsv`.
- **Criterio de éxito:** los 10 residuos del guion terminan con el resultado esperado, la telemetría no tiene saltos y los comandos inválidos se rechazan.
- **Resultado (22-11-2026):** 818 líneas JSON válidas; 698 paquetes de telemetría sin saltos, con periodo mediano de 500 ms; 10/10 eventos correctos; ciclo medio de 7,5 s y latencia de clasificación de 1,73 s; la calibración con 100 g dio un factor de 399,3 (el real era 400). Evidencia en `simulacion_firmware/resultado_verificacion.txt`.
- **Límite:** no reemplaza las pruebas físicas, porque no modela torques, rozamiento ni ruido eléctrico. Los tiempos reales van a ser mayores.

También se probó la cadena completa Arduino simulado → puerto serie virtual → `gateway.py` → SQLite → dashboard durante 100 s: 197 paquetes, 0 % perdido, y los comandos PAUSA, ESTADO y SEGUIR enviados desde la base llegaron y fueron respondidos.

## P1 · Exactitud de la balanza

- **Objetivo:** medir el error de la celda de carga ya calibrada.
- **Condiciones:** bandeja montada en su soporte final, sin que la toque nada más; mesa firme; `TARA` hecha con la bandeja vacía.
- **Materiales:** masas patrón de 5, 20, 50, 100 y 200 g. Si no hay pesas de laboratorio, usen objetos pesados en una balanza de cocina de 0,1 g.
- **Procedimiento:**
  1. `PAUSA` desde el dashboard, para que la garra no intente tomar las masas.
  2. Pongan cada masa en el centro de la bandeja, esperen 3 s y anoten en `pesaje.csv` el peso que muestra el dashboard.
  3. Retírenla y verifiquen que vuelva a 0 ± 0,5 g.
  4. Repitan 5 veces por masa (25 mediciones). Luego `SEGUIR`.
- **Criterio de éxito:** error absoluto ≤ 2 g en todas las mediciones.
- **Evidencia:** `datos/pesaje.csv` y el gráfico `resultados/pesaje_error.png`.

## P2 · Detección de llegada

- **Objetivo:** verificar que todo residuo se detecta y que nada más dispara el ciclo.
- **Procedimiento:**
  1. Dejen 20 residuos distintos, uno a la vez, incluyendo un papel arrugado y una bolsa, que no devuelven eco. Anoten si arrancó el ciclo.
  2. Pasen la mano sobre la bandeja 10 veces sin dejar nada.
  3. Con la bandeja vacía, muevan el brazo 10 veces (`PAUSA` + `IR SOBRE` / `IR REPOSO`, luego `SEGUIR`).
  4. Anoten todo en `deteccion.csv`.
- **Criterio de éxito:** 20/20 residuos detectados (por ultrasónico o por masa) y 0 ciclos con la bandeja vacía. Las manos que el sistema descarta como `FALSA_DETECCION` sin mover el brazo cuentan como correctas.
- **Evidencia:** planilla y columna `via` de la base (U = ultrasónico, P = masa).

## P3 · Identificación de material

- **Objetivo:** medir el acierto del inductivo, el capacitivo y la regla de decisión.
- **Materiales:** 30 residuos domiciliarios reales: 10 metales (latas de aluminio, tapas, latas de conserva chicas), 10 plásticos (botellas PET chicas, vasos, envases de yogur) y 10 de descarte (papel, cartón, madera, tela).
- **Procedimiento:** dejen cada residuo en el centro de la bandeja, uno a la vez y en orden aleatorio. Después, en la pestaña **Validación** del dashboard, anoten el material real de cada evento y guarden.
- **Criterio de éxito:** acierto ≥ 90 % en metal y ≥ 80 % en plástico.
- **Evidencia:** matriz de confusión (`resultados/matriz_confusion.png`) y tabla de acierto.
- **Si no se cumple:** revisen en la base los porcentajes `pct_ind` y `pct_cap` de los errores. Si el capacitivo no detecta plásticos delgados, suban su sensibilidad con el tornillo; si detecta papel, bájenla.

## P4 · Agarre y depósito

- Se mide con los mismos 30 residuos de P3.
- **Criterio de éxito:** OK / (OK + FALLA_AGARRE) ≥ 95 %, y que cada residuo OK haya caído dentro de su contenedor. Esto último se verifica a ojo: anoten los que cayeron fuera en la columna `nota` o en el informe.
- **Evidencia:** tabla P4 del reporte y video de la prueba.

## P5 · Tiempo de ciclo

- Se mide con los mismos 30 residuos. El firmware registra `ciclo_ms`, desde la detección hasta volver a reposo, y `latencia_ms`, desde la detección hasta decidir el material.
- **Criterio de éxito:** media y percentil 95 del ciclo ≤ 15 s.
- **Evidencia:** histograma `resultados/tiempo_ciclo.png`.

## P6 · Continuidad de la captura y persistencia del repositorio

- **Procedimiento:**
  1. Dejen el sistema encendido 30 min con el gateway corriendo, idealmente durante P3–P5.
  2. A mitad de la prueba, desenchufen el USB 10 s y vuelvan a enchufarlo: el gateway debe reconectarse solo.
  3. Cierren el gateway y el dashboard y vuelvan a abrirlos: el histórico debe seguir ahí.
- **Criterio de éxito:** ≤ 1 % de telemetría perdida fuera del corte provocado, reconexión automática y 0 eventos perdidos.
- **Evidencia:** tabla P6 y la nota de continuidad en la pestaña Datos del dashboard.

## P7 · Manejo de fallas

| Caso | Cómo provocarlo | Resultado esperado |
|---|---|---|
| Sobrepeso | Dejar un objeto de más de 100 g | Evento `SOBREPESO`, estado `RETIRO_MANUAL`, el brazo no se mueve |
| Agarre imposible | Un objeto muy liso o grande | 2 intentos, evento `FALLA_AGARRE`, `RETIRO_MANUAL` |
| PARO | Botón PARO del dashboard a mitad de un ciclo | Brazo congelado al instante, evento `PARO`; `SEGUIR` vuelve a reposo |
| Contenedor lleno | Bajar la capacidad a 3 unidades en el dashboard | Alerta «Contenedor lleno» hasta marcarlo como vaciado |

**Criterio de éxito:** 4/4 casos con el resultado esperado. **Evidencia:** eventos en la base y video corto de cada caso.

---

## Registro de fallas encontradas y cómo se resolvieron

| N.º | Dónde | Falla | Causa | Solución | Verificación |
|---|---|---|---|---|---|
| F1 | Revisión del CAD (Avance 2) | Los engranajes de la pinza no engranaban | Eran discos lisos de 20 mm separados 12 mm | Engranajes de módulo 2 con 16 dientes (Ø primitivo 32 mm): pinza v2 | Modelo sin interferencias; abre 71 mm |
| F2 | Revisión del CAD (Avance 2) | El servo de la pinza no podía mover el engranaje | Su eje quedaba a 19 mm del engranaje motriz | Servo reubicado con el eje bajo el engranaje | Pinza v2 impresa y armada |
| F3 | Revisión del CAD (Avance 2) | El FSR-402 no cabía en el dedo | El sensor mide 18 mm, la cara del dedo 12 × 7 mm, y quedaba mirando hacia arriba | Dedo de 20 mm de alto con rebaje en la cara interna | Pinza v2 |
| F4 | Cálculo de torque (Avance 2) | El brazo de microservos no levantaba un residuo | Con el brazo estirado, el hombro necesitaba casi el torque máximo de un SG90 | Rediseño del brazo para 3 MG996R (brazo v3) | Brazo v3 impreso |
| F5 | Prueba P0 de software (22-11) | Un papel arrugado sin eco **no se detectaba** | El respaldo por masa exigía más de 10 g y el papel pesaba 6,5 g | Umbral del respaldo bajado a 5 g, igual que la masa mínima del sistema | P0: el papel se detecta por masa (`via = P`) y va a descarte |
| F6 | Revisión del diseño de la caja (22-11) | El HX711 no podía sacarse de su riel | El riel del MT3608 bloqueaba el espacio para deslizarlo | MT3608 reubicado; ambos rieles se abren hacia una zona libre central | Recorrido libre verificado en el modelo |
| F7 | *(pruebas físicas)* | | | | |
| F8 | *(pruebas físicas)* | | | | |

> Agreguen al menos una falla de las pruebas físicas (F7, F8…). Es lo que más pesa en el análisis crítico. Ejemplos probables: plásticos delgados que el capacitivo no ve, servos que tiemblan si el GND no es común, o una pose de agarre que roza la bandeja.

### Análisis crítico (completar con los resultados)

- **Qué funcionó:** …
- **Qué no alcanzó la meta y por qué:** compárenlo con los porcentajes de los sensores (`pct_ind`, `pct_cap`) y con los intentos.
- **Mejora propuesta y fundamento:** por ejemplo, si el plástico queda bajo el 80 %: agregar un segundo criterio (densidad aparente = masa / altura medida por el ultrasónico) o reemplazar el capacitivo por un sensor óptico de color. Si el ciclo supera 15 s: subir la velocidad (`MS_POR_GRADO_BRAZO` de 15 a 10) y evaluar si aparecen fallas de agarre.

---

## Validación contra el problema original (Avance 1)

**Problema:** en Chile solo cerca del 10 % del sector domiciliario recicla. Los residuos llegan mezclados a las plantas, y entre 1.500 y 2.000 trabajadores quedan expuestos a riesgos sanitarios al separarlos a mano. **Usuarios:** el operario de planta (principal) y el administrador de la instalación (secundario).

**Prueba P8 (lote real):** 30 residuos domiciliarios mezclados, los mismos de P3, dejados uno a uno como lo haría un usuario, con el dashboard abierto.

Después de la prueba, completen este párrafo con los números del reporte:

> «En el Avance 1 identificamos que la separación manual de residuos mezclados expone a los operarios y que casi nada se recupera. En la prueba de validación, SCB recibió **[30]** residuos domiciliarios sin que nadie tocara la bandeja después de dejarlos. Separó correctamente el **[__] %** (metal **[__] %**, plástico **[__] %**), con un ciclo medio de **[__] s**, y recuperó **[__] g** de material reciclable, el **[__] %** de la masa clasificada. El dashboard registró que el lote era **[__] %** metal, **[__] %** plástico y **[__] %** descarte, y generó **[__]** alertas: por ejemplo, avisó cuándo vaciar el contenedor de plástico y detectó **[__]** fallas de agarre que pidieron intervención. Esto muestra que el sistema detecta y separa el fenómeno real y que entrega información para decidir: el operario sabe cuándo vaciar o recalibrar sin revisar los contenedores a mano, y el administrador conoce la composición y la masa recuperable de lo que llega para planificar los retiros.»

| Información que genera SCB | Decisión que permite | Quién la toma |
|---|---|---|
| Llenado de cada contenedor (unidades y gramos) con alerta al 80 % | Cuándo vaciar cada contenedor; pausar si no se puede | Operario |
| Fallas de agarre seguidas y falsas detecciones | Cuándo recalibrar la pinza o revisar el ultrasónico | Operario |
| Composición del flujo (% metal, plástico y descarte) y masa reciclable recuperada | Planificar retiros y dimensionar contenedores; medir cuánto se recicla | Administrador |
| Acierto por material (validación) | Ajustar sensores o umbrales antes de escalar el sistema | Equipo de diseño |
