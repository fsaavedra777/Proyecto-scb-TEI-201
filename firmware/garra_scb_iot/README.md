# Firmware SCB v3.0 (Arduino UNO)

Máquina de estados que detecta, pesa, identifica y clasifica cada residuo, y envía por USB una línea JSON por mensaje para el gateway.

```
SIN_CALIBRAR ──(GUARDAR las 8 poses + SEGUIR)──► ESPERANDO ◄──────────────────────┐
                                                   │ ultrasónico 3x < 12 cm        │
                                                   │ o masa > 5 g por 0,5 s        │
                                                   ▼                               │
                                              ANALIZANDO ── < 5 g ──► FALSA_DETECCION
                                                   │ ── > 100 g ──► SOBREPESO ─► RETIRO_MANUAL
                                                   ▼                                │
                                              RECOGIENDO ── 2 intentos fallidos ────┘
                                                   ▼
                                              DEPOSITANDO ──► evento OK ────────────┘
  PARO (en cualquier momento) ──► PARADO ──(SEGUIR)──► ESPERANDO
```

## Cargarlo

1. Arduino IDE 2.x → Gestor de librerías → instalar **HX711 Arduino Library** (Bogdan Necula, 0.7.5). `Servo` y `EEPROM` vienen con el IDE.
   Sin internet: copien la carpeta `firmware/libraries/HX711` a `Documentos/Arduino/libraries/` y reinicien el IDE.
2. Abrir `garra_scb_iot/garra_scb_iot.ino` (se abren solas las otras pestañas).
3. Placa **Arduino UNO**, el puerto que corresponda → Subir.
4. Monitor Serie a **115200 baudios**, con fin de línea "Nueva línea". Escriban `AYUDA`.

Compilado: 14 472 bytes (44 % de la flash) y 469 bytes de RAM (22 %).

## Primera calibración (una sola vez, queda en la EEPROM)

Al primer encendido parte en `SIN_CALIBRAR` y **el brazo no se mueve solo**. Con la bandeja vacía:

| Paso | Comandos | Qué hacer |
|---|---|---|
| 1. Reposo | `MOVER H 100`, `MOVER C 80`… → `GUARDAR REPOSO` | Brazo recogido, fuera de la vista del ultrasónico |
| 2. Sobre la bandeja | `MOVER …` → `GUARDAR SOBRE` | Pinza unos 4 cm sobre el centro de la bandeja |
| 3. Agarre | `MOVER …` → `GUARDAR BANDEJA` | Dedos a la altura del residuo |
| 4. Pinza | `MOVER P 100` → `GUARDAR ABIERTA`; `MOVER P 50` → `GUARDAR CERRADA` | Abierta: entra una lata. Cerrada: dedos juntos **sin forzar** |
| 5. Contenedores | `MOVER B 30` … → `GUARDAR METAL`, igual para `PLASTICO` y `DESCARTE` | Pinza sobre la boca de cada contenedor |
| 6. Probar | `IR SOBRE`, `IR BANDEJA`, `IR METAL`… | Revisar que no choque con nada |
| 7. Balanza | `TARA` (vacía) → poner masa conocida → `CAL 100` → retirarla | Guarda el factor de la celda |
| 8. FSR | Mirar `fsr` en la telemetría apretando un residuo → `FSR 150` | Umbral entre "nada" y "agarrado" |
| 9. Listo | `SEGUIR` | Pasa a `ESPERANDO` |

Si cambian un servo o la pinza en terreno, basta repetir el paso afectado: `PAUSA`, `MOVER`, `GUARDAR`, `SEGUIR`. `FABRICA` borra todo.

## Comandos

| Comando | Cuándo | Efecto |
|---|---|---|
| `ESTADO` | siempre | Devuelve la configuración (`{"t":"cfg",...}`) |
| `PAUSA` / `SEGUIR` | siempre | Pausa (al terminar el ciclo en curso) / reanuda |
| `PARO` | siempre | Congela el brazo de inmediato; `SEGUIR` lo lleva a reposo |
| `TARA`, `CAL <g>` | en reposo | Tara y calibración de la balanza |
| `FSR <1-1023>` | siempre | Umbral del sensor de fuerza |
| `MOVER <B\|H\|C\|P> <grados>` | en pausa | Mueve un servo, sin salir de los límites de `config.h` |
| `GUARDAR <pose>`, `IR <pose>` | en pausa | Guarda o prueba una pose |

## Mensajes que envía (115200 baudios, una línea JSON cada uno)

| Tipo | Ejemplo | Frecuencia |
|---|---|---|
| Telemetría | `{"t":"tel","n":812,"ms":406120,"est":"ESPERANDO","dist":17.2,"peso":0.1,"ind":0,"cap":0,"fsr":3}` | cada 500 ms |
| Evento | `{"t":"evt","n":4,"res":"OK","mat":"PLASTICO","via":"U","peso":8.9,"ind":0,"cap":100,"fsr":425,"int":2,"lat":1731,"ciclo":10401}` | 1 por residuo |
| Estado | `{"t":"est","ms":112221,"est":"ANALIZANDO"}` | al cambiar |
| Respuesta | `{"t":"ack","cmd":"TARA","ok":1,"msg":"Tara hecha"}` | por comando |

Campos del evento: `res` = OK, FALLA_AGARRE, SOBREPESO, FALSA_DETECCION o PARO; `via` = U (ultrasónico) o P (masa); `ind`/`cap` = % de muestras en que detectó cada sensor; `fsr` = fuerza máxima en el agarre; `int` = intentos; `lat` = ms desde la detección hasta decidir el material; `ciclo` = ms desde la detección hasta volver a reposo.

**Frecuencia de muestreo.** El ultrasónico se lee a 10 Hz, así la llegada se confirma en 0,3 s. La telemetría sale a 2 Hz: un ciclo dura entre 6 y 15 s, por lo que se registran entre 12 y 30 puntos por ciclo, suficientes para ver la llegada, el pesaje y el retiro sin ocupar más del 5 % del puerto serie.

## Probar la lógica sin el robot

`testing/simulacion_firmware/` compila este mismo código contra un Arduino simulado y corre 10 casos (metal, plástico, papel sin eco, agarre resbaloso, sobrepeso, mano, objeto imposible, caída, PARO y PAUSA). Ver el README de esa carpeta.
