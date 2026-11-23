#!/bin/sh
# Une las pestañas del firmware en el mismo orden que el IDE de Arduino y
# compila el simulador. Requiere g++ (Linux, macOS o WSL en Windows).
set -e
cd "$(dirname "$0")"
FW=../../firmware/garra_scb_iot
cat $FW/garra_scb_iot.ino $FW/brazo.ino $FW/comunicacion.ino $FW/memoria.ino $FW/sensores.ino > garra_scb_iot.ino.cpp
g++ -std=c++17 -O1 -Wall -Wno-unused-function -I mock -I $FW -o sim sim.cpp
echo "Listo: ./sim escenario   o   ./sim demo"
