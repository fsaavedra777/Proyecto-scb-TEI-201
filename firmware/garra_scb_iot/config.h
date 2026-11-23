/*
 * config.h — Parámetros del Proyecto SCB (Avance 3)
 *
 * Aquí está todo lo que se ajusta sin tocar la lógica: pines, sensores
 * habilitados, umbrales y tiempos. Las POSES del brazo y la calibración de la
 * balanza NO van aquí: se guardan en la EEPROM con los comandos GUARDAR y CAL
 * (ver README del firmware), así sobreviven a un reinicio.
 */
#pragma once
#include <Arduino.h>

#define FW_VERSION "3.0"

// ============================ PINES (Arduino UNO) ============================
// Mismo mapa que el cableado del prototipo (hoja "Conexiones" de hardware/BOM.xlsx,
// hardware/esquematico.svg y firmware/SCB_clasificador.ino). Si recablean algo,
// cámbienlo SOLO aquí: el simulador de testing/ también lee estos valores.
const uint8_t PIN_INDUCTIVO     = 2;    // LJ12A3-4-Z/BX (NPN), cable negro
const uint8_t PIN_SERVO_BASE    = 3;    // MG996R base
const uint8_t PIN_CAPACITIVO    = 4;    // LJC18A3-H-Z/BX (NPN), cable negro
const uint8_t PIN_SERVO_HOMBRO  = 5;    // MG996R hombro
const uint8_t PIN_SERVO_CODO    = 6;    // MG996R codo
const uint8_t PIN_TRIG          = 7;    // HC-SR04 Trig
const uint8_t PIN_ECHO          = 8;    // HC-SR04 Echo
const uint8_t PIN_SERVO_PINZA   = 9;    // SG90 garra
const uint8_t PIN_HX_DT         = A0;   // HX711 DT
const uint8_t PIN_HX_SCK        = A1;   // HX711 SCK
const uint8_t PIN_FSR           = A2;   // FSR-402: 5 V - FSR - A2 - 10 kΩ - GND
const uint8_t PIN_LED           = 13;   // LED integrado: indica el estado
// Si los sensores de proximidad se alimentan a 12 V, su salida NPN debe entrar
// al Arduino a través de un diodo 1N4148 (cátodo hacia el sensor): ver esquemático.

// ============================ SENSORES ======================================
const bool USAR_CAPACITIVO = true;          // false: el plástico se decide solo por masa
const bool USAR_FSR        = true;          // false: la pinza cierra hasta el ángulo guardado
const bool INDUCTIVO_ACTIVO_EN_BAJO  = true; // NPN (/BX): detecta = LOW
const bool CAPACITIVO_ACTIVO_EN_BAJO = true; // NPN (/BX). Si su sensor es /BY (PNP): false
                                             // y conectar con divisor 15k/10k (ver esquemático)

// ============================ TIEMPOS =======================================
// Muestreo justificado por el problema: un ciclo dura ~10-15 s, así que a 2 Hz
// el dashboard recibe 20-30 puntos por ciclo (se ve llegada, pesaje y retiro)
// sin saturar el puerto serie (< 5 % de 115200 baudios).
const unsigned long PERIODO_TELEMETRIA_MS  = 500;   // 2 Hz hacia el dashboard
const unsigned long PERIODO_ULTRASONICO_MS = 100;   // 10 Hz para detectar llegadas
const uint8_t  LECTURAS_CONFIRMACION = 3;     // 3 lecturas seguidas = objeto real (300 ms)
const uint8_t  LECTURAS_CONFIRMACION_PESO = 5; // respaldo: masa sostenida 0,5 s (bolsas, papel)
const uint8_t  MUESTRAS_MATERIAL     = 50;    // 50 muestras x 10 ms = 0,5 s por sensor
const uint8_t  PORCENTAJE_DETECCION  = 60;    // % de muestras activas para decir "detecta"
const uint8_t  LECTURAS_PESO_ESTABLE = 10;    // HX711 a 10 SPS -> ~1 s de promedio

// ============================ UMBRALES ======================================
const float DIST_OBJETO_CM      = 12.0;   // bajo esto hay algo en la bandeja
const float PESO_MIN_G          = 5.0;    // bajo esto la bandeja está vacía
const float PESO_MAX_G          = 100.0;  // sobre esto la garra no lo intenta (meta a validar)
const float PESO_MAX_PLASTICO_G = 60.0;   // un plástico domiciliario pesa menos que esto
const uint16_t UMBRAL_FSR_DEFECTO = 150;  // 0-1023, se cambia con el comando FSR <valor>

// ============================ MOVIMIENTO ====================================
const uint8_t MS_POR_GRADO_BRAZO = 15;  // más alto = más lento y suave
const uint8_t MS_POR_GRADO_PINZA = 25;  // la pinza cierra lento para "sentir" el objeto
const uint8_t APRIETE_EXTRA      = 3;   // grados que sigue cerrando tras sentir el objeto
const uint8_t MAX_INTENTOS       = 2;   // intentos de agarre antes de pedir retiro manual

// Límites mecánicos {mín, máx} de cada servo: base, hombro, codo, pinza.
// Ningún comando puede sacar un servo de este rango.
const uint8_t LIMITES[4][2] = {
  {10, 170},
  {30, 150},
  {30, 150},
  {40, 140},
};

// ============================ TIPOS =========================================
enum Estado : uint8_t {
  INICIANDO, SIN_CALIBRAR, ESPERANDO, ANALIZANDO, RECOGIENDO,
  DEPOSITANDO, RETIRO_MANUAL, PAUSADO, PARADO
};

enum Material : uint8_t { METAL, PLASTICO, DESCARTE, NINGUNO };

// Índices de las poses guardadas en la EEPROM
enum PoseId : uint8_t { P_REPOSO, P_SOBRE, P_BANDEJA, P_METAL, P_PLASTICO, P_DESCARTE, N_POSES };

struct Pose { uint8_t b, h, c; };   // ángulos de base, hombro y codo

// Lo que se guarda en la EEPROM (sobrevive a reinicios)
struct Config {
  uint16_t magic;          // marca de configuración válida
  float    factor;         // cuentas del HX711 por gramo
  Pose     poses[N_POSES];
  uint8_t  pinzaAbierta;
  uint8_t  pinzaCerrada;
  uint8_t  guardadas;      // bit 0-5: poses, bit 6: abierta, bit 7: cerrada
  uint16_t umbralFsr;
};

const uint16_t CONFIG_MAGIC = 0x5CB3;
const uint8_t  TODO_GUARDADO = 0xFF;
