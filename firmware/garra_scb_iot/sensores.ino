/*
 * sensores.ino — Lectura de todos los sensores
 *
 *  HC-SR04  : distancia a la bandeja (detección de llegada)
 *  HX711    : masa del residuo y confirmación de que la garra lo levantó
 *  LJ12A3   : inductivo, metal (salida NPN, LOW = detecta)
 *  LJC18A3  : capacitivo, plástico (salida NPN, LOW = detecta)
 *  FSR-402  : fuerza en el dedo de la pinza (divisor con 10 kΩ, 0-1023)
 */

// ---------------------------- Ultrasónico ----------------------------
// Devuelve cm, o -1 si no hubo eco (objeto blando, inclinado o muy lejos).
float medirDistanciaCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000UL);   // 25 ms = ~4 m máx.
  if (us == 0) return -1;
  return us / 58.0;                                      // ida y vuelta a 343 m/s
}

// ---------------------------- Balanza (no bloqueante) ----------------
// Se llama en cada servicio(). Solo lee cuando el HX711 tiene un dato listo
// (10 por segundo), así nunca frena el resto del programa.
void actualizarBalanza() {
  if (!balanza.is_ready()) return;
  long crudo = balanza.read();
  pesoCrudoG = (crudo - offsetBalanza) / cfg.factor;

  // Promedio móvil de 4 lecturas para la telemetría
  static float ventana[4] = {0, 0, 0, 0};
  static uint8_t i = 0;
  ventana[i] = pesoCrudoG;
  i = (i + 1) % 4;
  pesoG = (ventana[0] + ventana[1] + ventana[2] + ventana[3]) / 4.0;
  lecturasBalanza++;
}

// Promedio de n lecturas NUEVAS (a 10 SPS, n=10 tarda ~1 s).
// Si el HX711 deja de responder, corta a los 3 s y devuelve lo que tenga.
float pesoEstable(uint8_t n) {
  float suma = 0;
  uint8_t k = 0;
  uint16_t ultima = lecturasBalanza;
  unsigned long t0 = millis();
  while (k < n && millis() - t0 < 3000) {
    if (!esperar(5)) break;
    if (lecturasBalanza != ultima) {
      ultima = lecturasBalanza;
      suma += pesoCrudoG;
      k++;
    }
  }
  return (k > 0) ? suma / k : pesoG;
}

// Promedio de cuentas crudas, para tara y calibración
// (el HX711 entrega 24 bits: 20 lecturas caben de sobra en un long)
long promedioCrudo(uint8_t n) {
  long suma = 0;
  for (uint8_t k = 0; k < n; k++) {
    unsigned long t0 = millis();
    while (!balanza.is_ready() && millis() - t0 < 500) { }
    suma += balanza.read();
  }
  return suma / n;
}

void hacerTara() {
  offsetBalanza = promedioCrudo(15);
  pesoG = pesoCrudoG = 0;
}

// Calibración con una masa conocida puesta en la bandeja (después de TARA)
bool calibrarBalanza(int gramos) {
  if (gramos <= 0) return false;
  long cuentas = promedioCrudo(20) - offsetBalanza;
  if (cuentas == 0) return false;
  cfg.factor = (float)cuentas / gramos;
  guardarConfig();
  return true;
}

// ---------------------------- Sensores de material -------------------
bool leerInductivo() {
  bool bajo = digitalRead(PIN_INDUCTIVO) == LOW;
  return INDUCTIVO_ACTIVO_EN_BAJO ? bajo : !bajo;
}

bool leerCapacitivo() {
  if (!USAR_CAPACITIVO) return false;
  bool bajo = digitalRead(PIN_CAPACITIVO) == LOW;
  return CAPACITIVO_ACTIVO_EN_BAJO ? bajo : !bajo;
}

// Muestrea ambos sensores MUESTRAS_MATERIAL veces (0,5 s) y devuelve el % de
// muestras en que detectaron. Un porcentaje evita decidir por un rebote.
void muestrearMaterial(uint8_t &pctInd, uint8_t &pctCap) {
  uint8_t nInd = 0, nCap = 0;
  for (uint8_t k = 0; k < MUESTRAS_MATERIAL; k++) {
    if (leerInductivo())  nInd++;
    if (leerCapacitivo()) nCap++;
    if (!esperar(10)) break;
  }
  pctInd = (uint16_t)nInd * 100 / MUESTRAS_MATERIAL;
  pctCap = (uint16_t)nCap * 100 / MUESTRAS_MATERIAL;
}

// ---------------------------- FSR ------------------------------------
int leerFsr() {
  if (!USAR_FSR) return 0;
  return analogRead(PIN_FSR);
}
