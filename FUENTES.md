# Declaración de fuentes y uso de IA — Proyecto SCB

Este archivo declara todo el código, las librerías, los diseños y los textos que no escribimos desde cero, de dónde salieron y cómo los adaptamos al proyecto. Todos los integrantes podemos explicar cualquier parte del código, incluida la generada con IA.

> **Para el equipo, antes de subir:** completen las líneas marcadas **[COMPLETAR]** con lo que ustedes cambiaron al probar en el robot real (poses, umbrales, velocidades, pines). Esa parte tiene que estar escrita por ustedes.

## 1. Librerías y dependencias

### Firmware (Arduino UNO)

| Librería | Versión | Uso en el proyecto | Fuente |
|---|---|---|---|
| Servo | 1.3.0 (incluida en el IDE) | Control de los 3 MG996R y el SG90 (`brazo.ino`) | https://github.com/arduino-libraries/Servo |
| HX711 Arduino Library (Bogdan Necula) | 0.7.5 | Lectura del ADC de 24 bits de la celda de carga: `is_ready()` y `read()` en `sensores.ino`. Copia sin modificar en `firmware/libraries/HX711` (licencia MIT) | https://github.com/bogde/HX711 |
| EEPROM | núcleo Arduino AVR | Guardar las poses, el factor de la balanza y el umbral del FSR (`memoria.ino`) | https://docs.arduino.cc/learn/built-in-libraries/eeprom |

### Gateway, dashboard y análisis (Python)

| Librería | Versión probada | Uso | Fuente |
|---|---|---|---|
| pyserial | 3.5 | Leer el puerto serie del Arduino (`gateway.py`) | https://github.com/pyserial/pyserial |
| sqlite3 | biblioteca estándar | Repositorio de datos (`db.py`) | https://docs.python.org/3/library/sqlite3.html |
| Streamlit | 1.67 | Interfaz del dashboard (`dashboard.py`) | https://streamlit.io |
| pandas | 3.0 | Cálculo de indicadores (`indicadores.py`) | https://pandas.pydata.org |
| Plotly | 7.1 | Gráficos del dashboard | https://plotly.com/python/ |
| matplotlib | 3.11 | Gráficos del reporte de pruebas | https://matplotlib.org |

### Documentación y diseño 3D

| Herramienta | Versión | Uso | Fuente |
|---|---|---|---|
| CadQuery | 2.8 | Modelo paramétrico de la caja de control y del gemelo 3D | https://github.com/CadQuery/cadquery |
| VTK | 9.6 | Renders | https://vtk.org |
| ReportLab | 5.0 | Planos técnicos en PDF | https://www.reportlab.com |
| schemdraw | 0.23 | Esquemático eléctrico | https://schemdraw.readthedocs.io |
| openpyxl | 3.1 | BOM en Excel | https://openpyxl.readthedocs.io |

## 2. Código y diseños externos adaptados

### Medición de distancia con el HC-SR04 (`medirDistanciaCm` en `sensores.ino`)
- **Fuente:** patrón estándar de la hoja de datos del HC-SR04: pulso de 10 µs en Trig y `pulseIn` en Echo; distancia = µs / 58.
- **Adaptación:** se agregó un timeout de 25 ms (devuelve -1 si no hay eco), lectura a 10 Hz y confirmación con 3 lecturas seguidas bajo 12 cm. Como respaldo, el residuo también se detecta por masa sostenida 0,5 s (falla F5 del protocolo).

### Tara y calibración del HX711 (`hacerTara`, `calibrarBalanza`, `actualizarBalanza`)
- **Fuente:** ejemplo de calibración de la librería HX711 de bogde (tara con promedio y factor = cuentas / masa conocida).
- **Adaptación:** la lectura es **no bloqueante** (solo lee cuando `is_ready()`), para no frenar los servos ni la telemetría. Se usa un promedio móvil de 4 lecturas, el factor se guarda en la EEPROM con el comando `CAL <g>`, y la balanza también confirma que la garra levantó el residuo (bandeja < 5 g).

### Diseño mecánico del brazo
- **[COMPLETAR / CONFIRMAR]** Una versión anterior del brazo se adaptó del **EEZYbotARM Mk2** de Carlo Franciscone (Thingiverse thing:1454048, licencia CC BY-NC). Si alguna pieza de esa versión sigue en el prototipo final, mantengan esta cita; si el brazo final es solo el v3 (base, torreta, eslabón y antebrazo para MG996R), borren este punto.

## 3. Uso de inteligencia artificial

Herramienta en todos los casos: **Claude (Anthropic)**, en un proyecto de claude.ai, entre octubre y noviembre de 2026.

### 3.1 Firmware v3.0 (`firmware/garra_scb_iot/`, todas las pestañas)
- **Prompts (resumen):** "estamos ocupando solo Arduino UNO y el sensor, hazme un código para eso" (octubre); "desarrolla esta guía para la entrega final", con la guía del Avance 3 adjunta (22-11-2026).
- **Qué generó la IA:** la máquina de estados (ESPERANDO → ANALIZANDO → RECOGIENDO → DEPOSITANDO, con RETIRO_MANUAL, PAUSADO y PARADO); el protocolo JSON de telemetría y eventos; los comandos de calibración guardados en la EEPROM; el movimiento suave e interpolado de los servos; y el cierre de la pinza "sintiendo" con el FSR.
- **Adaptación al proyecto:** pines, sensores y umbrales del prototipo (mismo mapa de pines que el cableado y que `firmware/SCB_clasificador.ino`: inductivo LJ12A3 en D2 y capacitivo LJC18A3 en D4, MG996R en D3, D5 y D6, SG90 en D9, HX711 en A0/A1, FSR en A2) y metas del Avance 2 (5–100 g, 12 cm). **[COMPLETAR: poses, umbral del FSR, sensibilidad del capacitivo y velocidades que ajustaron al probar.]**
- **Comprensión:** el `loop()` llama siempre a `servicio()`, que lee la balanza cuando hay dato, atiende comandos y manda telemetría cada 500 ms. Toda espera o movimiento usa `esperar()`, que también llama a `servicio()`, así los datos no se cortan mientras el brazo se mueve, y un `PARO` corta el movimiento en el paso siguiente. El material se decide por porcentaje de muestras (≥ 60 % de 50 lecturas), no por una sola lectura. Se verificó compilando para el UNO (44 % de la flash) y con 10 casos en la simulación de `testing/simulacion_firmware/`.

### 3.2 Gateway, base de datos y dashboard (`dashboard/`)
- **Qué generó la IA:** `gateway.py` (lectura serie, guardado en SQLite y CSV, cola de comandos, reconexión y conteo de paquetes perdidos), `db.py`, `indicadores.py` y `dashboard.py` (Streamlit).
- **Adaptación:** indicadores y alertas definidos a partir del problema del Avance 1 (operario y administrador) y de las metas del Avance 2. **[COMPLETAR: capacidad real de sus contenedores y cualquier cambio que hicieron.]**
- **Comprensión:** el Arduino UNO no tiene WiFi, así que el notebook es el gateway. Cada línea JSON se guarda en una tabla según su tipo (`tel` en telemetría, `evt` en eventos). El dashboard no habla con el Arduino: lee la base, y para mandar un comando escribe en la tabla `comandos`, que el gateway envía por el puerto serie. Se probó con el firmware simulado en un puerto virtual: 197 paquetes y 0 % perdido.

### 3.3 Pruebas (`testing/`)
- **Qué generó la IA:** el protocolo P0–P8, `analizar_pruebas.py`, las planillas y la simulación del firmware (`simulacion_firmware/`: Arduino simulado y escenario de 10 casos).
- **Adaptación:** **[COMPLETAR: resultados reales, fallas F7 en adelante y análisis crítico; esto lo escriben ustedes.]**
- **Comprensión:** la simulación compila el mismo código del firmware contra versiones falsas de `Arduino.h`, `Servo.h`, `HX711.h` y `EEPROM.h` con tiempo virtual, y un "mundo" responde como la bandeja y la pinza.

### 3.4 Hardware y diseño 3D
- **Qué generó la IA:** el esquemático (`hardware/esquematico/esquematico_scb.py`), `BOM_completo.xlsx` con el presupuesto de corriente, la caja de control y el gemelo 3D (`caja_control.py`), la biblioteca de componentes externos, los planos (`planos.py`) y los renders. En avances anteriores: el rediseño de la pinza v2 (corrección de engranajes, eje del servo y alojamiento del FSR), el brazo v3 para MG996R y las piezas de la estación de sensado.
- **Adaptación:** **[COMPLETAR: medidas reales que verificaron con pie de metro, cambios de impresión y precios reales en el BOM.]**
- **Comprensión:** la caja es paramétrica: todas las medidas salen de la sección `PARÁMETROS`. Los componentes se modelan como volúmenes referenciales con sus medidas de hoja de datos, y se verificó por intersección de sólidos que no haya interferencias.

### 3.5 Documentación y presentación
- **Qué generó la IA:** primeras versiones de `README_IoT.md`, de los README de las carpetas del sistema IoT (`firmware/garra_scb_iot/`, `dashboard/`, `diseno-3d/README_caja_control.md`, `testing/simulacion_firmware/`), del guion y de la presentación del Avance 3, y en el Avance 2 la presentación y el guion. El `README.md` principal y los README de carpeta originales los escribió el equipo.
- **Adaptación:** **[COMPLETAR: qué reescribieron.]** Los datos del problema (10 % de reciclaje domiciliario y 1.500–2.000 trabajadores expuestos) vienen de nuestra propuesta original.
