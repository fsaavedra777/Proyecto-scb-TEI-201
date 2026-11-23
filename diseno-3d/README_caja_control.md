# Diseño 3D: caja de control y gemelo 3D

| Archivo | Qué es |
|---|---|
| `SCB_caja_control_gemelo.step` | **Gemelo 3D de la caja**: base, tapa y los volúmenes del Arduino UNO, la placa perforada con borneras y condensador, el HX711 y el MT3608, cada uno con su nombre y color |
| `SCB_componentes_externos.step` | Volúmenes de lo que va fuera de la caja: MG996R, SG90, HC-SR04, inductivo M12, capacitivo M18, celda de 1 kg, FSR-402 y fuente S-50-5 |
| `planos/planos_caja_control.pdf` | 3 hojas A3 a escala 1:1: base, tapa y ensamble (vistas ortogonales, cotas, tolerancias, lista de piezas y cómo reparar) |
| `renders/` | Exterior, interior y explosionada, en PNG con fondo transparente |
| `stl/` | `caja_base.stl` y `caja_tapa.stl`, listos para imprimir (caben en una cama de 160 mm) |
| `fuente/` | Scripts paramétricos que generan todo lo anterior (CadQuery) |

## La caja en números

- Exterior de 154,8 × 104,8 × 45,4 mm con la tapa; interior útil de 150 × 100 × 40 mm. Paredes de 2,4 mm.
- **Sin interferencias**: se verificó por cálculo de intersección entre todos los cuerpos. El componente más alto, el condensador, llega a 26,6 mm y el techo útil está a 37,5 mm.
- **Diseño para la reparación**: la tapa se cierra con 4 tornillos M3 avellanados sobre insertos de bronce, el Arduino y la placa van atornillados con tuercas cautivas, y el HX711 y el MT3608 entran deslizando en rieles, sin tornillos. Los cables salen por una ranura en U que se abre al levantar la tapa.
- Holgura de 0,3 mm por lado en todos los ajustes entre piezas impresas.

## Armar el gemelo completo en Fusion 360

1. **Archivo → Abrir → SCB_caja_control_gemelo.step**. Fusion lo convierte y quedan los componentes con sus nombres en el navegador.
2. **Insertar → Insertar en el diseño actual** el STEP del robot (`Robot_SCB_para_Fusion.step` o el del brazo v3) y `SCB_componentes_externos.step`.
3. Muevan cada servo o sensor de la biblioteca a su lugar en el brazo o la estación (**Modificar → Mover/Copiar**, o **Ensamblar → Unión**), y la caja y la fuente sobre la base MDF.
4. **Guardar** → queda el `.f3d`. Exporten también un `.f3z` (Archivo → Exportar) para subirlo a GitHub.
5. Para la demo: oculten la tapa con el ojito del navegador y muestren los componentes internos, o usen **Inspeccionar → Análisis de sección**.

**Sobre la parametrización.** El modelo paramétrico vive en `fuente/caja_control.py`: todas las medidas salen de la sección `PARÁMETROS`, por ejemplo `L_INT`, `PARED`, `HOLGURA` o la posición de cada componente. Cambian un valor, corren `python caja_control.py` y se regeneran el STEP, los STL, los planos (`planos.py`) y los renders (`render_caja.py`). Al importarse en Fusion, el STEP queda como geometría fija: si el evaluador pide ver parámetros en Fusion, muestren este script y expliquen que es el árbol paramétrico del diseño.

## Imprimir

| Pieza | Orientación | Soportes | Relleno | Masa aprox. |
|---|---|---|---|---|
| `caja_base.stl` | Boca hacia arriba | No | 20 % | 100 g |
| `caja_tapa.stl` | Ya viene boca abajo | No | 20 % | 50 g |

Después de imprimir: coloquen los 4 insertos M3 con el cautín a unos 220 °C, presionen las 8 tuercas M3 en los hexágonos de abajo y prueben que el USB del Arduino calce en su calado antes de cablear.
