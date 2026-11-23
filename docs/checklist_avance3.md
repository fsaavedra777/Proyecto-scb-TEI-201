# Checklist del Avance 3 — qué está listo y qué falta

✅ = listo en este repositorio · ⬜ = lo hace el equipo antes del 24-11

## Software (30 %)
- ✅ Firmware con captura continua y muestreo justificado (`firmware/`)
- ✅ Repositorio persistente: SQLite + CSV (`dashboard/gateway.py`)
- ✅ Dashboard en tiempo real e histórico (`dashboard/dashboard.py`)
- ✅ Información útil: alertas con acción, llenado, composición, acierto y tiempos
- ✅ Código modular y comentado (5 pestañas en el firmware; gateway, base, indicadores e interfaz separados)
- ⬜ Cargar el firmware en el robot, calibrar las poses y la balanza, y correr el sistema completo al menos 3 veces el día anterior

## Hardware (30 %)
- ✅ Justificación de cada componente (`hardware/justificacion_componentes.md`)
- ✅ Esquemático completo (`hardware/esquematico/esquematico_scb.pdf`)
- ✅ BOM con cantidades y costos (`hardware/BOM_completo.xlsx`)
- ⬜ Reemplazar en el BOM los precios estimados (fondo amarillo) por los reales
- ⬜ Fotos del prototipo armado, mínimo 3 ángulos (`hardware/fotos/`)
- ⬜ Imprimir la caja de control, montar la electrónica y etiquetar los cables
- ⬜ Revisar que el capacitivo sea /BX (NPN); si es /BY, cambiar a divisor

## Diseño 3D (20 %)
- ✅ Gemelo 3D de la caja con componentes internos (`diseno-3d/SCB_caja_control_gemelo.step`)
- ✅ Planos con vistas, cotas, tolerancias y escala (`diseno-3d/planos/planos_caja_control.pdf`)
- ✅ Renders exterior, interior y explosionado (`diseno-3d/renders/`)
- ⬜ Abrir los STEP en Fusion, juntarlos con el STEP del robot y guardar `.f3d` / `.f3z` en `diseno-3d/`
- ⬜ Practicar mostrar los componentes internos en Fusion

## Testing (10 %)
- ✅ Protocolo P0–P8 con objetivo, condiciones, procedimiento, criterio y evidencia (`testing/protocolo_pruebas.md`)
- ✅ P0 hecha: simulación del firmware 10/10 y cadena gateway → base sin pérdidas
- ✅ Fallas F1–F6 documentadas con causa y solución
- ⬜ Hacer P1–P8 con el robot y correr `python testing/analizar_pruebas.py`
- ⬜ Copiar `dashboard/datos/scb.db` (o los CSV) de las pruebas a `testing/datos/`
- ⬜ Agregar al menos una falla de las pruebas físicas (F7) y completar el párrafo de validación

## GitHub (5 %)
- ✅ Estructura de carpetas y README completo
- ✅ FUENTES.md con librerías, código externo y uso de IA
- ⬜ Completar las líneas **[COMPLETAR]** de FUENTES.md
- ✅ Repositorio público: https://github.com/fsaavedra777/Proyecto-scb-TEI-201
- ⬜ Subir antes de presentar las fotos, el `.f3d`, los datos de las pruebas y FUENTES.md completo

## Presentación (5 %)
- ✅ Guion con tiempos, roles, demo paso a paso y preguntas (`docs/guion_presentacion.md`)
- ✅ Diapositivas en Canva: «Proyecto SCB – Avance 3» (12 páginas, con notas del orador por integrante)
- ⬜ Reemplazar en las diapositivas 9 y 10 los «[__]» amarillos por los resultados reales del reporte de pruebas
- ⬜ Diapositiva 8: arrastrar `diseno-3d/renders/caja_explosionada.png` al marco y borrar el texto amarillo
- ✅ Diapositiva 11: URL del repositorio
- ⬜ (Opcional) Diapositiva 7: reemplazar la imagen por `hardware/esquematico/esquematico_scb.png`
- ⬜ Ensayar 8–10 minutos con cronómetro
