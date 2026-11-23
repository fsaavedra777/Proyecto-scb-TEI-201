# SCB · Sistema Clasificador de Basura

Una garra robótica recibe residuos domiciliarios en una bandeja, los identifica como **metal, plástico o descarte** con sensores inductivo, capacitivo y de masa, y deja cada uno en su contenedor. Cada lectura y cada residuo quedan registrados en una base de datos, y un dashboard en tiempo real los convierte en indicadores y alertas para el operario y el administrador.

**TEI201 Taller de Diseño en Ingeniería · Universidad Adolfo Ibáñez · 2026-2**
**Equipo:** Facundo Saavedra · Matías Jara · Martín Olivares   **Profesor:** Luís Andueza

## Problema (Avance 1)

En Chile solo cerca del 10 % del sector domiciliario recicla. Los residuos llegan mezclados a las plantas, y entre 1.500 y 2.000 trabajadores quedan expuestos a riesgos sanitarios al separarlos a mano. SCB separa en el origen, sin contacto humano después de dejar el residuo, y mide qué llega y cuánto se recupera.

## Cómo funciona

```
 Residuo ─► Bandeja ─► HC-SR04 (llegada) + HX711 (masa) + inductivo (metal) + capacitivo (plástico)
                                   │
                          Arduino UNO: máquina de estados
                                   │ decide el material
                        Brazo 3× MG996R + pinza SG90 con FSR ─► contenedor correcto
                                   │
                     USB, JSON cada 500 ms + 1 evento por residuo
                                   ▼
          gateway.py (notebook) ─► SQLite + CSV ─► dashboard (Streamlit, localhost:8501)
                ▲                                       │ alertas e indicadores
                └──── comandos: PAUSA, TARA, PARO ──────┘
```

| Paso del ciclo IoT | En SCB |
|---|---|
| **Captura** | Ultrasónico a 10 Hz; telemetría de todos los sensores a 2 Hz (de 12 a 30 puntos por ciclo) |
| **Repositorio** | `dashboard/datos/scb.db` (SQLite, histórico completo) y respaldo diario en CSV |
| **Visualización** | Dashboard con estado en vivo, gráficos de 2 min, composición, residuos por hora y tiempos de ciclo |
| **Información** | Llenado de contenedores, masa reciclable recuperada, éxito de agarre, acierto por material y alertas con la acción sugerida |
| **Decisión** | Cuándo vaciar cada contenedor, cuándo recalibrar, cómo planificar los retiros |

## Estructura del repositorio

Este archivo describe el **sistema IoT completo del Avance 3** (firmware, base de datos, dashboard, pruebas y gemelo 3D). La descripción general del proyecto está en [`README.md`](README.md).

```
├── README.md                          descripción general del proyecto (equipo)
├── README_IoT.md                      este archivo: sistema IoT, cómo replicarlo y usarlo
├── FUENTES.md                         librerías, código externo y uso de IA (obligatorio)
├── firmware/
│   ├── garra_scb_iot/                 firmware v3.0 IoT del Arduino UNO (el que se usa en la demo) y su README
│   ├── libraries/HX711/               copia de la librería HX711 0.7.5 (MIT)
│   └── SCB_clasificador.ino           versión del prototipo Alpha (Avance 2)
├── dashboard/                         gateway.py, base SQLite/CSV, dashboard.py y lanzadores de Windows
├── hardware/
│   ├── esquematico/                   esquemático eléctrico completo (PDF/SVG/PNG y script)
│   ├── esquematico.pdf / .svg         esquema de conexiones (equipo)
│   ├── BOM_completo.xlsx              BOM con costos, presupuesto de corriente y pines
│   ├── BOM.xlsx                       BOM y mapa de conexiones (equipo)
│   ├── justificacion_componentes.md   por qué cada componente y diseño para la reparación
│   └── fotos/                         fotos del prototipo armado
├── diseno-3d/                         gemelo 3D completo (SCB_gemelo_completo.step), caja de control,
│   │                                  planos, renders, STL y scripts paramétricos
│   └── modelo_3d/                     piezas del brazo v3, pinza, estación y base (STL/STEP),
│                                      ensambles del robot y planos de armado
├── testing/                           protocolo de pruebas, análisis de resultados, simulación del firmware
└── docs/                              guía de armado, checklist del Avance 3 y guion de la presentación
```

## Replicar el sistema

**Hardware.** Lista completa en `hardware/BOM_completo.xlsx`, unos $128.000 CLP. Conexiones en `hardware/esquematico/esquematico_scb.pdf`. Lo esencial: los servos van a la fuente de 5 V y 10 A, nunca al Arduino, y todo comparte GND.

**Firmware.**
1. Arduino IDE 2.x → Gestor de librerías → instalar **HX711 Arduino Library** (Bogdan Necula).
2. Abrir `firmware/garra_scb_iot/garra_scb_iot.ino` → placa Arduino UNO → Subir.
3. Calibrar una sola vez desde el Monitor Serie (115200 baudios): las poses del brazo con `PAUSA` / `MOVER` / `GUARDAR` y la balanza con `TARA` / `CAL 100`. Paso a paso en `firmware/garra_scb_iot/README.md`.

**Gateway y dashboard** (Python 3.10 o superior):
```
cd dashboard
pip install -r requirements.txt
python gateway.py                      # deja corriendo: Arduino -> base de datos
python -m streamlit run dashboard.py   # en otra terminal: abre http://localhost:8501
```
En Windows basta con doble clic en `dashboard/instalar_windows.bat` (una vez) y luego en `iniciar_windows.bat`. Cierren el Monitor Serie del IDE antes, porque el puerto solo admite un programa a la vez.

**Dashboard:** es local, en `http://localhost:8501` del notebook conectado al Arduino. Para mostrarlo en otra pantalla de la misma red: `http://<IP-del-notebook>:8501`.

## Resultados

- Prueba de software del firmware (sin hardware): **10/10 casos correctos**, telemetría sin pérdidas (`testing/simulacion_firmware/`).
- Pruebas físicas P1–P8 y validación con un lote real: ver `testing/protocolo_pruebas.md` y `testing/resultados/reporte_pruebas.md`, que se genera con `python testing/analizar_pruebas.py`.

## Licencia y créditos

Proyecto académico. Las fuentes externas y el uso de herramientas de IA están declarados en [FUENTES.md](FUENTES.md).
