# Guion de la presentación — Avance 3 (8–10 min + 3 min de preguntas)

**Roles:** Facundo presenta el problema, la solución y el GitHub. Matías maneja la demo en vivo (robot y dashboard). Martín presenta el diseño 3D y los resultados. Los tres responden preguntas.

Las diapositivas están en Canva («Proyecto SCB – Avance 3», 12 páginas). Cada una tiene en sus **notas del orador** el texto completo de quien la presenta.

| Min | Diapositiva | Quién | Qué decir (idea central) |
|---|---|---|---|
| 0:00 | 1. Portada | Facundo | Nombre, equipo y una frase: «una garra que separa la basura y dice qué llega» |
| 0:20 | 2. El problema | Facundo | 10 % de reciclaje domiciliario; separación manual con riesgo sanitario para 1.500–2.000 trabajadores; nadie tiene datos para decidir |
| 1:00 | 3. Solución: ciclo IoT | Facundo | Captura → Arduino → USB → gateway → SQLite → dashboard → decisión. Por qué gateway: el UNO no tiene WiFi. Por qué 2 Hz |
| 2:00 | 4. **Demo en vivo** | Matías | (ver abajo) |
| 5:30 | 5. Información para decidir | Matías | Llenado, alertas con acción, composición, masa reciclable y acierto, y quién decide con cada una |
| 6:15 | 6. Componentes justificados | Martín | Por qué cada componente: rango, precisión, consumo y compatibilidad |
| 6:55 | 7. Esquemático, costo y reparación | Martín | Esquemático y BOM ($128.000). **Abrir la caja frente al evaluador** |
| 7:40 | 8. Gemelo 3D | Martín | Cambiar a Fusion: caja con componentes adentro, planos y renders |
| 8:25 | 9. Pruebas y resultados | Martín | Acierto por material contra la meta, ciclo medio, pérdida de datos y una falla con su solución |
| 9:25 | 10. Validación | Martín | Párrafo de validación con los números del lote real |
| 9:55 | 11. GitHub | Facundo | Estructura del repo, URL, FUENTES.md |
| 10:20 | 12. Cierre | Todos | Preguntas |

> Si se pasan de 10 min, acorten la diapositiva 6 (dejen la justificación para las preguntas) y la 5 (la demo ya mostró las alertas).

## Demo en vivo (3–4 min), paso a paso

**Antes de entrar:** notebook con batería cargada, la fuente de 5 V enchufada, `iniciar_windows.bat` corriendo, el dashboard en la pestaña **En vivo** con la base **Real**, los contenedores vacíos y marcados como vaciados, y 4 residuos a mano (lata, botella chica, papel, frasco pesado).

1. **Mostrar que captura en vivo:** «Esto es la telemetría del Arduino, dos veces por segundo». Acerquen la mano a la bandeja: la distancia baja en el gráfico. Al no haber masa, el sistema la descarta como falsa detección.
2. **Lata:** déjenla en la bandeja. Narren los estados: *Analizando* (la pesa y muestrea los sensores), *Recogiendo*, *Depositando*. Señalen el evento: METAL, OK, gramos y segundos de ciclo, y que el contenedor Metal sube.
3. **Botella** → Plástico. **Papel** → Descarte. Si el papel no da eco, digan: «lo detectó por masa, por eso tenemos dos sensores de llegada».
4. **Decisión:** bajen en la barra lateral la capacidad del contenedor a 3 unidades. Aparece la alerta «Contenedor … lleno: vacíelo ahora» y el operario pulsa *Marcar vaciado*. «Así el operario sabe cuándo intervenir sin mirar los contenedores.»
5. **Falla controlada:** el frasco pesado → *Sobrepeso*, el brazo no se mueve y el sistema pide retiro manual.
6. **Indicadores:** pestaña Indicadores: composición, masa reciclable y tiempo de ciclo contra la meta de 15 s.

**Plan B (si el brazo falla en vivo):** sigan con la captura. Los sensores, la base y el dashboard funcionan igual, y el sistema pasa a *Retiro manual*. Expliquen la falla con calma: también es un dato. **No usen la base simulada en la evaluación.**

## Preguntas probables y respuestas cortas

- **¿Por qué muestrean a 2 Hz?** Un ciclo dura entre 6 y 15 s: a 2 Hz hay de 12 a 30 puntos por ciclo, suficientes para ver llegada, pesaje y retiro, usando menos del 5 % del puerto serie. Las llegadas se detectan aparte, a 10 Hz.
- **¿Dónde quedan los datos y cómo sobreviven a un reinicio?** En `scb.db` (SQLite) y en CSV diarios. El Arduino no guarda datos, solo su calibración en la EEPROM. Si se desconecta el USB, el gateway se reconecta solo.
- **¿Por qué no usaron WiFi?** El UNO no tiene. Un ESP32 trabaja a 3,3 V y habría que adaptar niveles en 5 señales. El notebook como gateway es la arquitectura IoT clásica de dispositivo + pasarela.
- **¿Cómo saben si clasifica bien?** En la pestaña Validación anotamos el material real de cada residuo de prueba y el sistema calcula la matriz de confusión y el acierto por material contra las metas (90 % metal, 80 % plástico).
- **¿Qué hace el diodo del sensor inductivo?** El sensor es NPN y se alimenta a 12 V. El diodo deja que tire el pin a 0 V cuando detecta, pero no deja pasar los 12 V al Arduino. El pin usa la resistencia pull-up interna.
- **¿Por qué esa fuente?** En el peor caso, con los 4 servos bloqueados, piden 8,3 A; la fuente da 10 A y queda un 17 % de margen. El Arduino entrega como máximo unos 0,5 A.
- **¿Cómo se repara?** Cuatro tornillos de la tapa; todo va con borneras o conectores; los módulos salen deslizando de sus rieles; y un servo nuevo se recalibra por comandos, sin reprogramar.
- **¿Qué hizo la IA y qué hicieron ustedes?** Está detallado en FUENTES.md. Todos podemos explicar cualquier función: por ejemplo, `esperar()` mantiene la telemetría durante los movimientos y permite cortar con PARO.
- **¿Qué mejorarían?** (usen su análisis crítico) Un segundo criterio para el plástico, como la densidad aparente o un sensor de color, y una placa con WiFi para no depender del notebook.
