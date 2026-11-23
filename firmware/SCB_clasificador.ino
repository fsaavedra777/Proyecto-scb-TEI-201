/*
  SCB - Clasificador de residuos con brazo (Arduino UNO)
  Taller de diseño en ingeniería - Avance 2 / Prototipo Alpha

  Librerías: Servo (incluida), EEPROM (incluida), HX711 (Bogdan Necula "bogde")
  Monitor Serie: 115200 baudios, "Nueva línea" activado.

  Pines
    Servos : Base D3, Hombro D5, Codo D6, Garra D9
    HC-SR04: TRIG D7, ECHO D8
    HX711  : DT A0, SCK A1
    FSR-402: A2 (5 V - FSR - A2 - 10 kΩ - GND)
    LJ12A3 (inductivo) : D2      LJC18A3 (capacitivo): D4
    (salidas NPN: activo = LOW, se usa INPUT_PULLUP)
*/

#include <Servo.h>
#include <EEPROM.h>
#include <HX711.h>

// ---------------- Pines ----------------
const uint8_t PIN_BASE = 3, PIN_HOMBRO = 5, PIN_CODO = 6, PIN_GARRA = 9;
const uint8_t PIN_TRIG = 7, PIN_ECHO = 8;
const uint8_t PIN_IND = 2, PIN_CAP = 4;
const uint8_t PIN_HX_DT = A0, PIN_HX_SCK = A1, PIN_FSR = A2;

// ---------------- Parámetros (ver requerimientos) ----------------
const float    DIST_DETECCION_CM  = 12.0;  // RF-02
const uint8_t  LECTURAS_DETECCION = 3;     // RF-02
const float    MASA_MIN_G         = 5.0;   // RF-03 / RF-05 (bandeja vacía < 5 g)
const float    MASA_MAX_G         = 50.0;  // RNF-02 (si pasa, error RF-08)
const int      FSR_AGARRE         = 150;   // lectura sobre la cual hay agarre
const uint8_t  MAX_INTENTOS       = 2;     // RF-05 / RF-08
const uint16_t PASO_MS            = 20;    // 1° cada 20 ms = 50 °/s (RNF-04)
const uint8_t  ANG_MIN = 10, ANG_MAX = 170; // límites de ángulo (RNF-04)
const bool     SENSOR_ACTIVO_BAJO = true;  // NPN normalmente abierto

// ---------------- Posiciones (se calibran por Serie y quedan en EEPROM) ----------------
struct Pose { uint8_t b, h, c; };
enum { P_REPOSO, P_ARRIBA, P_AGARRE, P_METAL, P_PLASTICO, P_DESCARTE, N_POSES };
const char* const NOMBRES[N_POSES] = {"reposo", "arriba bandeja", "agarre bandeja",
                                      "contenedor metal", "contenedor plastico", "contenedor descarte"};

struct Config {
  uint16_t magic;
  Pose poses[N_POSES];
  uint8_t gAbierta, gCerrada;
  float factor;
};
const uint16_t MAGIC = 0x5C0B;
Config cfg;

// VALORES INICIALES DE EJEMPLO: hay que calibrarlos con el brazo real
void cfgPorDefecto() {
  cfg.magic = MAGIC;
  cfg.poses[P_REPOSO]    = {90, 90, 90};
  cfg.poses[P_ARRIBA]    = {90, 70, 100};
  cfg.poses[P_AGARRE]    = {90, 80, 120};
  cfg.poses[P_METAL]     = {30, 80, 100};
  cfg.poses[P_PLASTICO]  = {150, 80, 100};
  cfg.poses[P_DESCARTE]  = {170, 80, 100};
  cfg.gAbierta = 45;   // CAD: 71 mm de apertura a 45°
  cfg.gCerrada = 90;   // CAD: dedos paralelos a 90°
  cfg.factor = 1.0;
}
void guardarCfg() { EEPROM.put(0, cfg); }

// ---------------- Objetos y estado ----------------
Servo sB, sH, sC, sG;
HX711 balanza;
int aB, aH, aC, aG;           // ángulos actuales
bool parada = false;

enum Estado { ESPERANDO, ANALIZANDO, RECOGIENDO, DEPOSITANDO, ERROR_ST };
Estado estado = ESPERANDO;
enum Tipo { T_DESCARTE, T_METAL, T_PLASTICO };
Tipo tipo = T_DESCARTE;
float masaG = 0;
uint8_t lecturasOk = 0;
unsigned long tInicio = 0, tUltimaLectura = 0;
const __FlashStringHelper* msgError = nullptr;
bool errorAvisado = false;

#define MOVER(x) if (!(x)) { error(F("Parada de emergencia")); return; }

// ---------------- Utilidades ----------------
int sgn(int x) { return (x > 0) - (x < 0); }

void error(const __FlashStringHelper* m) {
  msgError = m; estado = ERROR_ST; errorAvisado = false;
}

bool abortado() {                       // 'X' por Serie = parada inmediata
  bool x = false;
  while (Serial.available()) { char c = Serial.read(); if (c == 'X' || c == 'x') x = true; }
  if (x) parada = true;
  return x;
}

bool irAngulos(int b, int h, int c) {
  b = constrain(b, ANG_MIN, ANG_MAX);
  h = constrain(h, ANG_MIN, ANG_MAX);
  c = constrain(c, ANG_MIN, ANG_MAX);
  while (aB != b || aH != h || aC != c) {
    if (abortado()) return false;
    aB += sgn(b - aB); aH += sgn(h - aH); aC += sgn(c - aC);
    sB.write(aB); sH.write(aH); sC.write(aC);
    delay(PASO_MS);
  }
  return true;
}
bool irPose(uint8_t p) { return irAngulos(cfg.poses[p].b, cfg.poses[p].h, cfg.poses[p].c); }

bool irGarra(int g) {
  g = constrain(g, ANG_MIN, ANG_MAX);
  while (aG != g) {
    if (abortado()) return false;
    aG += sgn(g - aG);
    sG.write(aG);
    delay(PASO_MS);
  }
  return true;
}

// ---------------- Sensores ----------------
float distanciaCm() {
  digitalWrite(PIN_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long d = pulseIn(PIN_ECHO, HIGH, 30000UL);
  if (d == 0) return 999.0;
  return d / 58.0;
}

int leerFSR() {
  long s = 0;
  for (uint8_t i = 0; i < 4; i++) s += analogRead(PIN_FSR);
  return s / 4;
}

float leerMasa() {
  if (!balanza.wait_ready_timeout(500)) return -1;
  return balanza.get_units(5);
}

bool activo(uint8_t pin) { return digitalRead(pin) == (SENSOR_ACTIVO_BAJO ? LOW : HIGH); }

bool votar(uint8_t pin) {               // mayoría de 10 lecturas
  uint8_t n = 0;
  for (uint8_t i = 0; i < 10; i++) { if (activo(pin)) n++; delay(10); }
  return n >= 7;
}

// ---------------- Pinza ----------------
bool cerrarHastaAgarre() {              // cierra de a 1° hasta que el FSR supere el umbral
  int dir = sgn((int)cfg.gCerrada - aG);
  while (aG != cfg.gCerrada) {
    if (abortado()) return false;
    if (leerFSR() >= FSR_AGARRE) return true;
    aG += dir; sG.write(aG); delay(PASO_MS);
  }
  return leerFSR() >= FSR_AGARRE;
}

// ---------------- Estados ----------------
void estadoEsperando() {
  if (millis() - tUltimaLectura < 100) return;
  tUltimaLectura = millis();
  if (distanciaCm() < DIST_DETECCION_CM) lecturasOk++; else lecturasOk = 0;
  if (lecturasOk >= LECTURAS_DETECCION) {
    lecturasOk = 0;
    parada = false;
    tInicio = millis();
    Serial.println(F("[ESPERANDO] Residuo detectado"));
    estado = ANALIZANDO;
  }
}

void estadoAnalizando() {
  delay(500);                           // deja asentar la bandeja
  masaG = leerMasa();
  Serial.print(F("[ANALIZANDO] Masa: ")); Serial.print(masaG, 1); Serial.println(F(" g"));
  if (masaG < 0) { error(F("Balanza no responde")); return; }
  if (masaG < MASA_MIN_G) { Serial.println(F("Falso positivo, vuelvo a esperar")); estado = ESPERANDO; return; }
  if (masaG > MASA_MAX_G) { error(F("Supera la masa maxima")); return; }

  if (votar(PIN_IND))      tipo = T_METAL;
  else if (votar(PIN_CAP)) tipo = T_PLASTICO;
  else                     tipo = T_DESCARTE;

  Serial.print(F("[ANALIZANDO] Tipo: "));
  Serial.println(tipo == T_METAL ? F("metal") : tipo == T_PLASTICO ? F("plastico") : F("descarte"));
  estado = RECOGIENDO;
}

void estadoRecogiendo() {
  for (uint8_t intento = 1; intento <= MAX_INTENTOS; intento++) {
    Serial.print(F("[RECOGIENDO] Intento ")); Serial.println(intento);
    MOVER(irGarra(cfg.gAbierta));
    MOVER(irPose(P_ARRIBA));
    MOVER(irPose(P_AGARRE));
    bool agarro = cerrarHastaAgarre();
    if (parada) { error(F("Parada de emergencia")); return; }
    MOVER(irPose(P_ARRIBA));
    delay(400);
    float m = leerMasa();               // bandeja vacía = el residuo salió con la garra
    Serial.print(F("  FSR=")); Serial.print(leerFSR());
    Serial.print(F("  bandeja=")); Serial.print(m, 1); Serial.println(F(" g"));
    if (agarro && m >= 0 && m < MASA_MIN_G) { estado = DEPOSITANDO; return; }
    MOVER(irGarra(cfg.gAbierta));       // suelta y reintenta
  }
  MOVER(irPose(P_REPOSO));
  error(F("No logro tomar el residuo"));
}

void estadoDepositando() {
  uint8_t destino = tipo == T_METAL ? P_METAL : tipo == T_PLASTICO ? P_PLASTICO : P_DESCARTE;
  Serial.print(F("[DEPOSITANDO] -> ")); Serial.println(NOMBRES[destino]);
  MOVER(irPose(destino));
  MOVER(irGarra(cfg.gAbierta));
  delay(400);
  MOVER(irPose(P_REPOSO));
  Serial.print(F("[LISTO] Ciclo en ")); Serial.print((millis() - tInicio) / 1000.0, 1);
  Serial.println(F(" s. Listo para el siguiente."));
  estado = ESPERANDO;
}

void estadoError() {
  if (!errorAvisado) {
    Serial.print(F("[ERROR] ")); Serial.println(msgError);
    Serial.println(F("RETIRO MANUAL del residuo y envie R para reiniciar."));
    errorAvisado = true;
  }
}

// ---------------- Comandos por Monitor Serie (banco de pruebas / calibración) ----------------
void ayuda() {
  Serial.println(F("B/H/C/G <ang>: mover base/hombro/codo/garra | M n: ir a pose n | S n: guardar pose actual en n"));
  Serial.println(F("O: guardar garra actual como ABIERTA | L: como CERRADA | P: imprimir config"));
  Serial.println(F("E: tara (bandeja vacia) | K <g>: calibrar con masa conocida | D: diagnostico de sensores"));
  Serial.println(F("R: reiniciar tras error | X: parada inmediata"));
  Serial.println(F("Poses: 0 reposo, 1 arriba, 2 agarre, 3 metal, 4 plastico, 5 descarte"));
}

void imprimirCfg() {
  for (uint8_t i = 0; i < N_POSES; i++) {
    Serial.print(i); Serial.print(' '); Serial.print(NOMBRES[i]); Serial.print(F(": "));
    Serial.print(cfg.poses[i].b); Serial.print(','); Serial.print(cfg.poses[i].h);
    Serial.print(','); Serial.println(cfg.poses[i].c);
  }
  Serial.print(F("Garra abierta=")); Serial.print(cfg.gAbierta);
  Serial.print(F(" cerrada=")); Serial.print(cfg.gCerrada);
  Serial.print(F(" | factor balanza=")); Serial.println(cfg.factor, 3);
}

void diagnostico() {
  Serial.print(F("Dist=")); Serial.print(distanciaCm(), 1);
  Serial.print(F(" cm | Masa=")); Serial.print(leerMasa(), 1);
  Serial.print(F(" g | FSR=")); Serial.print(leerFSR());
  Serial.print(F(" | Ind=")); Serial.print(activo(PIN_IND));
  Serial.print(F(" Cap=")); Serial.println(activo(PIN_CAP));
}

void atenderSerial() {
  if (!Serial.available()) return;
  char c = toupper(Serial.read());
  if (c == '\n' || c == '\r' || c == ' ') return;
  float v = Serial.parseFloat();
  int n = (int)v;
  bool libre = (estado == ESPERANDO || estado == ERROR_ST);
  if (c == 'X') { parada = true; return; }
  if (c == '?') { ayuda(); return; }
  if (c == 'D') { diagnostico(); return; }
  if (c == 'P') { imprimirCfg(); return; }
  if (c == 'R') { parada = false; if (estado == ERROR_ST) { estado = ESPERANDO; Serial.println(F("Reiniciado")); } return; }
  if (!libre) return;                   // lo demás solo con el sistema detenido
  parada = false;
  switch (c) {
    case 'B': irAngulos(n, aH, aC); break;
    case 'H': irAngulos(aB, n, aC); break;
    case 'C': irAngulos(aB, aH, n); break;
    case 'G': irGarra(n); break;
    case 'M': if (n >= 0 && n < N_POSES) irPose(n); break;
    case 'S':
      if (n >= 0 && n < N_POSES) { cfg.poses[n] = {(uint8_t)aB, (uint8_t)aH, (uint8_t)aC}; guardarCfg(); Serial.println(F("Pose guardada")); }
      break;
    case 'O': cfg.gAbierta = aG; guardarCfg(); Serial.println(F("Garra abierta guardada")); break;
    case 'L': cfg.gCerrada = aG; guardarCfg(); Serial.println(F("Garra cerrada guardada")); break;
    case 'E': balanza.tare(10); Serial.println(F("Tara hecha")); break;
    case 'K':
      if (v > 0) {
        balanza.set_scale(1);
        cfg.factor = balanza.get_value(10) / v;
        balanza.set_scale(cfg.factor);
        guardarCfg();
        Serial.print(F("Factor = ")); Serial.println(cfg.factor, 3);
      }
      break;
    default: Serial.println(F("Comando desconocido (? para ayuda)")); break;
  }
}

// ---------------- setup / loop ----------------
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_IND, INPUT_PULLUP);
  pinMode(PIN_CAP, INPUT_PULLUP);

  EEPROM.get(0, cfg);
  if (cfg.magic != MAGIC) { cfgPorDefecto(); guardarCfg(); }

  balanza.begin(PIN_HX_DT, PIN_HX_SCK);
  balanza.set_scale(cfg.factor);
  balanza.tare(10);                     // bandeja vacía al encender

  aB = cfg.poses[P_REPOSO].b; aH = cfg.poses[P_REPOSO].h; aC = cfg.poses[P_REPOSO].c;
  aG = cfg.gAbierta;
  sB.write(aB); sH.write(aH); sC.write(aC); sG.write(aG);   // primero la posición, luego attach
  sB.attach(PIN_BASE); sH.attach(PIN_HOMBRO); sC.attach(PIN_CODO); sG.attach(PIN_GARRA);

  Serial.println(F("SCB listo. Envie ? para ayuda."));
  if (cfg.factor == 1.0) Serial.println(F("AVISO: balanza sin calibrar (comando K)."));
}

void loop() {
  atenderSerial();
  switch (estado) {
    case ESPERANDO:   estadoEsperando();   break;
    case ANALIZANDO:  estadoAnalizando();  break;
    case RECOGIENDO:  estadoRecogiendo();  break;
    case DEPOSITANDO: estadoDepositando(); break;
    case ERROR_ST:    estadoError();       break;
  }
}
