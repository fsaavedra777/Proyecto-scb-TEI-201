# Gateway, repositorio de datos y dashboard

```
 Arduino UNO ──USB (JSON, 115200)──► gateway.py ──► datos/scb.db (SQLite, histórico completo)
      ▲                                  │      └─► datos/csv/ (respaldo diario en CSV)
      │                                  ▼
      └──── comandos (PAUSA, TARA…) ◄─ cola en SQLite ◄── dashboard.py (navegador, localhost:8501)
```

El Arduino UNO no tiene WiFi, así que el notebook hace de **gateway IoT**: recibe los datos por USB, los guarda de forma persistente y los sirve al dashboard. Si se reinicia el Arduino o el PC, el histórico sigue en `datos/scb.db`.

## Instalar (una vez)

Python 3.10 o superior. En Windows, doble clic en `instalar_windows.bat`, o en una terminal:

```
pip install -r requirements.txt
```

## Usar en la demo

1. Conecten el Arduino por USB y **cierren el Monitor Serie del IDE**: el puerto solo lo puede usar un programa a la vez.
2. Doble clic en `iniciar_windows.bat`. Abre dos ventanas: el gateway (muestra cada evento) y el dashboard (se abre el navegador en `http://localhost:8501`).
   - A mano: `python gateway.py` en una terminal y `python -m streamlit run dashboard.py` en otra.
   - Si no encuentra el Arduino: `python gateway.py --listar` y luego `python gateway.py --puerto COM4`.
3. En el dashboard dejen seleccionada la base **Real**.

## Qué muestra el dashboard y qué decisión apoya

| Pestaña | Para quién | Información | Decisión que permite |
|---|---|---|---|
| En vivo | Operario | Estado, peso, distancia, sensores, gráfico de 2 min | Saber si el equipo está trabajando o detenido |
| | | **Alertas con acción**: contenedor lleno, fallas de agarre seguidas, falsas detecciones, sin datos, PARO, balanza descalibrada | Vaciar un contenedor, recalibrar la pinza, tarar o revisar el cable |
| | | Llenado de cada contenedor (unidades y gramos desde el último vaciado) | Cuándo vaciar, con el botón «Marcar vaciado» |
| Indicadores | Administrador | Composición de lo que llega, masa reciclable recuperada, éxito de agarre, ciclo medio, residuos por hora | Dimensionar contenedores y retiros; ver si se cumplen las metas |
| Validación | Equipo | Matriz de confusión y acierto por material contra las metas (metal ≥ 90 %, plástico ≥ 80 %) | Ajustar la sensibilidad de los sensores o los umbrales |
| Datos | Todos | Tabla completa, descarga CSV, % de telemetría perdida | Análisis posterior y evidencia de las pruebas |

La barra lateral envía comandos al Arduino (Pausar, Reanudar, Tarar, Estado y PARO) y fija la capacidad de los contenedores.

## Archivos

| Archivo | Qué hace |
|---|---|
| `gateway.py` | Lee el puerto serie, guarda en SQLite y CSV, mide paquetes perdidos, reenvía los comandos y se reconecta solo |
| `db.py` | Esquema de la base y funciones para escribirla |
| `indicadores.py` | Cálculo de indicadores, llenado, matriz de confusión y alertas (lo usan el dashboard y el análisis de pruebas) |
| `dashboard.py` | Interfaz en Streamlit |
| `datos/` | Base de datos y CSV (no se suben a GitHub; copien a `testing/datos/` los de sus pruebas) |

## Probar sin el robot

`python gateway.py --simular` genera datos inventados en **otra base** (`datos/scb_simulado.db`). En el dashboard elijan «Simulada»: aparece un aviso rojo de datos simulados. Sirve para practicar la presentación, **no como evidencia ni para la demo**, que debe ser con el sistema real.
