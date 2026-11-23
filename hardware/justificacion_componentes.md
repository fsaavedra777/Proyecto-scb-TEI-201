# Hardware del sistema IoT: archivos y justificación de componentes

Complementa a `README.md`, `BOM.xlsx` y `esquematico.pdf` de esta carpeta (equipo). El mapa de pines es el mismo en todos: inductivo D2, base D3, capacitivo D4, hombro D5, codo D6, HC-SR04 D7/D8, pinza D9, HX711 A0 (DT) / A1 (SCK), FSR A2.

| Archivo | Contenido |
|---|---|
| `esquematico/esquematico_scb.pdf` | Esquemático completo (también `.svg`, `.png` y el script `esquematico_scb.py` que lo genera) |
| `BOM_completo.xlsx` | Lista de materiales con cantidades y costos (hoja **BOM**), presupuesto de corriente (hoja **Consumo**) y asignación de pines (hoja **Pines**) |
| `fotos/` | Fotos del prototipo armado, mínimo 3 ángulos (**las agregan ustedes**) |

**Costo total del prototipo: unos $128.000 CLP** ($101.550 de electrónica y $26.225 de mecánica y encapsulado). Los precios con fondo amarillo en `BOM_completo.xlsx` son estimados: reemplácenlos por lo que pagaron.

## Arquitectura eléctrica

```
 220 V ──► Fuente S-50-5 ──► +5V_SRV ──┬──► 3× MG996R + SG90   (hasta 8,3 A con todo bloqueado)
                                        ├──► 1000 µF (amortigua picos)
                                        └──► MT3608 ──► +12V ──► LJ12A3 (metal) y LJC18A3 (plástico)
                                                                  │ salida NPN vía 1N4148
 Notebook ──USB──► Arduino UNO ◄────────────────────────────────┘
 (gateway)            ├── 5 V ──► HC-SR04, HX711 + celda, FSR-402
                      └── GND común con la fuente y el MT3608
```

## Justificación de cada componente

| Función | Componente | Rango y precisión | Consumo | Por qué este y no otro |
|---|---|---|---|---|
| Control | **Arduino UNO R3** | 16 MHz, 2 KB RAM, 14 E/S | 50 mA | El firmware usa 44 % de la flash y 22 % de la RAM, y quedan pines libres. Tiene 5 V nativos para todos los sensores. Un ESP32 daría WiFi, pero es de 3,3 V y obligaría a adaptar niveles en 5 señales; por eso el WiFi se resolvió con el notebook como gateway. |
| Llegada del residuo | **HC-SR04** | 2–400 cm, ±3 mm | 15 mA | Sin contacto y barato. Se monta a 15–20 cm sobre la bandeja, fuera de su zona ciega (< 2 cm). No ve bien las bolsas o el papel arrugado, por eso el firmware también detecta por masa. Un sensor IR se confunde con la luz y con superficies oscuras. |
| Masa | **Celda de 1 kg + HX711** | 24 bits a 10 SPS; ±0,3 g de ruido en simulación, meta ±2 g | 6 mA | Los residuos pesan entre 5 y 100 g. Una celda de 1 kg da buena resolución en ese rango, y una de 5 kg perdería sensibilidad. Además confirma que la garra levantó el objeto, porque la bandeja queda en 0 g. |
| Metal | **LJ12A3-4-Z/BX** (inductivo) | 4 mm ±10 % | ≤ 15 mA a 12 V | Solo reacciona a metales, así que la decisión es casi binaria (meta ≥ 90 %). Es de uso industrial, con rosca M12 para fijarlo bajo una bandeja delgada de 2–3 mm. |
| Plástico | **LJC18A3-H-Z/BX** (capacitivo) | 1–10 mm, ajustable | ≤ 15 mA a 12 V | Detecta no metales. Con su tornillo de sensibilidad se calibra para plásticos delgados. También ve papel húmedo, madera y agua, por eso se combina con la masa (≤ 60 g) y la meta es ≥ 80 %. |
| Agarre | **FSR-402** | 0,2–20 N, no lineal | < 1 mA | Solo hace falta saber si hay contacto: un umbral (150 de 1023) basta. Mide 18 mm y cabe en el dedo de la pinza v2. Una celda de carga en el dedo sería precisa pero muy pesada para el SG90. |
| Base, hombro, codo | **3× MG996R** | 9,4 kg·cm a 4,8 V, 180° | 0,9 A en movimiento; 2,5 A bloqueado | El hombro carga el brazo de 146 mm más el residuo. Con un residuo de 100 g a 0,15 m necesita unos 1,5 kg·cm más el peso propio, así que el MG996R deja margen. Los SG90 del diseño anterior no alcanzaban (ver falla F4 del protocolo). |
| Pinza | **SG90** | 1,8 kg·cm | 0,25 A | Solo abre y cierra, y es liviano en la punta del brazo. La pinza v2 ya estaba impresa para este servo. |
| Potencia servos | **Fuente S-50-5, 5 V 10 A** | 50 W | — | Peor caso, con los cuatro servos bloqueados: 8,3 A, y queda un 17 % de margen (hoja *Consumo* del BOM). Es estable, como corresponde a una instalación fija en planta. El regulador del Arduino entrega como máximo ~0,5 A, así que los servos nunca van ahí. |
| 12 V sensores | **MT3608** | 5 → 12 V, 2 A | 85 mA a 5 V | Los sensores de proximidad piden 6–36 V. Así se evita una segunda fuente: una sola toma de 220 V alimenta todo. |
| Protección | **2× 1N4148, 1000 µF** | — | — | El diodo deja que el sensor NPN tire el pin a 0 V, pero impide que los 12 V lleguen al Arduino. El condensador evita que los picos de los servos reinicien el sistema. |

## Montaje y diseño para la reparación

- **Caja de control** (ver `diseno-3d/`): el Arduino, la placa perforada, el HX711 y el MT3608 van dentro. La tapa se cierra con 4 tornillos M3 sobre insertos de bronce. El Arduino y la placa se atornillan a pilares, y el HX711 y el MT3608 van en rieles donde entran deslizando, sin tornillos.
- **Todo se conecta con borneras o conectores**: ningún sensor ni servo está soldado al circuito. Cambiar un servo quemado es abrir la tapa, soltar su conector, montar el repuesto y recalibrar sus poses con `PAUSA` / `MOVER` / `GUARDAR`, sin reprogramar.
- **Ranura en U en la tapa** para los cables: se sacan levantando la tapa, sin desarmar conectores.
- **Etiquetas** en cada cable (termorretráctil o cinta) con el nombre de su red en el esquemático (`SRV_BASE`, `IND`, `+12V`…).
- **Sin pegamento estructural.** La única excepción es el FSR, que va con cinta doble contacto y se reemplaza despegándolo.

## Pendiente para la entrega (lo hacen ustedes)

- [ ] Fotos del prototipo armado en `fotos/`: frente, lateral, desde arriba y la caja abierta.
- [ ] Reemplazar en `BOM_completo.xlsx` los precios estimados por los reales.
- [ ] Revisar que el capacitivo sea **/BX** (NPN). Si es /BY, cambiar a divisor (nota 5 del esquemático).
