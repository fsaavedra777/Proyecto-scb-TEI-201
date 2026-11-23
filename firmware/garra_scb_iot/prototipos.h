/*
 * prototipos.h — Índice de todas las funciones del firmware, por pestaña.
 * El IDE de Arduino las declara solo, pero tenerlas aquí sirve como mapa del
 * código y permite compilarlo fuera del IDE (simulación en testing/).
 */
#pragma once
#include "config.h"

// garra_scb_iot.ino — máquina de estados
void estadoEsperando();
void estadoAnalizando();
Material decidirMaterial(uint8_t pctInd, uint8_t pctCap, float peso);
void estadoRecogiendo();
void estadoDepositando();
void estadoRetiro();
void esperarBandejaLibre();
void cambiarEstado(Estado nuevo);
void servicio();
bool esperar(unsigned long ms);
void atenderParo();
void actualizarLed();

// brazo.ino — servos
uint8_t limitar(uint8_t servo, int ang);
void iniciarServos();
bool moverBrazo(const Pose &p, uint8_t msPorGrado);
bool moverServo(uint8_t i, int destino, uint8_t msPorGrado);
bool moverPinza(uint8_t ang, uint8_t msPorGrado);
bool cerrarPinzaSintiendo(int &fsrMax);

// comunicacion.ino — JSON y comandos
void jIni(const __FlashStringHelper *tipo);
void jClave(const __FlashStringHelper *k);
void jNum(const __FlashStringHelper *k, float v, uint8_t dec);
void jInt(const __FlashStringHelper *k, long v);
void jTxt(const __FlashStringHelper *k, const __FlashStringHelper *v);
void jFin();
const __FlashStringHelper *nombreEstado(Estado e);
const __FlashStringHelper *nombreMaterial(Material m);
void enviarTelemetria();
void enviarEvento(const __FlashStringHelper *resultado);
void enviarCambioEstado();
void enviarConfig();
void logMsg(const __FlashStringHelper *msg);
void ack(const char *cmd, bool ok, const __FlashStringHelper *msg);
void leerComandos();
uint8_t indicePose(const char *s);
bool modoAjuste();
bool enReposo();
void procesarComando(char *texto);
void enviarAngulos();

// memoria.ino — EEPROM
void configPorDefecto();
void cargarConfig();
void guardarConfig();

// sensores.ino — lecturas
float medirDistanciaCm();
void actualizarBalanza();
float pesoEstable(uint8_t n);
long promedioCrudo(uint8_t n);
void hacerTara();
bool calibrarBalanza(int gramos);
bool leerInductivo();
bool leerCapacitivo();
void muestrearMaterial(uint8_t &pctInd, uint8_t &pctCap);
int leerFsr();
