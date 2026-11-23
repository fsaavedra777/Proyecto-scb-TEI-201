# Prueba de software del firmware (sin hardware)

Compila **el mismo código** de `firmware/garra_scb_iot/` contra un Arduino simulado (`mock/`) y un "mundo" que imita la bandeja, la balanza, los sensores y la pinza (`sim.cpp`). Sirve para probar la lógica antes de integrar el robot. No reemplaza las pruebas físicas: no modela torques, rozamiento ni ruido eléctrico.

## Correrla (Linux, macOS o WSL en Windows; requiere g++)

```
./compilar.sh
./sim escenario > resultado_escenario.tsv
python3 verificar_escenario.py resultado_escenario.tsv
```

El escenario calibra el brazo por comandos (`MOVER`, `GUARDAR`, `TARA`, `CAL 100`) y luego deja 10 casos: lata de aluminio, botella PET, papel arrugado sin eco, envase resbaloso, frasco de 250 g, una mano, un objeto imposible de tomar, una tapa que se cae, un PARO a mitad de ciclo y una PAUSA pedida durante un ciclo.

## Resultado (23-11-2026, con el mapa de pines del prototipo)

`resultado_verificacion.txt`: **TODO OK**. Fueron 818 líneas JSON válidas, 698 paquetes de telemetría sin saltos (periodo de 500 ms) y 10/10 eventos con el resultado esperado. `resultado_mundo.tsv` registra lo que pasó "físicamente" en cada caso, por ejemplo en qué contenedor cayó cada residuo.

Esta prueba encontró la falla **F5** del protocolo (el papel sin eco no se detectaba), que se corrigió en el firmware.

## Modo demo

`./sim demo` genera residuos al azar en tiempo real por stdin/stdout. Con `socat` se conecta a un puerto serie virtual para probar `gateway.py` y el dashboard sin el robot:

```
socat pty,raw,echo=0,link=/tmp/ttySCB EXEC:"./sim demo",pty,raw,echo=0 &
python3 ../../dashboard/gateway.py --puerto /tmp/ttySCB --db /tmp/prueba.db
```
