/*
 * brazo.ino — Movimiento del brazo (3x MG996R) y de la pinza (SG90)
 *
 * Todos los movimientos son suaves (de a 1 grado) y las tres articulaciones
 * llegan al mismo tiempo. Durante cada paso se llama a esperar(), que mantiene
 * viva la telemetría y permite cortar con PARO.
 */

uint8_t limitar(uint8_t servo, int ang) {
  return constrain(ang, LIMITES[servo][0], LIMITES[servo][1]);
}

// Arranque: se escribe la posición ANTES de attach() para que el servo no
// salte a 90° al energizarse.
void iniciarServos() {
  bool hayReposo = cfg.guardadas & (1 << P_REPOSO);
  angulo[0] = limitar(0, hayReposo ? cfg.poses[P_REPOSO].b : 90);
  angulo[1] = limitar(1, hayReposo ? cfg.poses[P_REPOSO].h : 90);
  angulo[2] = limitar(2, hayReposo ? cfg.poses[P_REPOSO].c : 90);
  angulo[3] = limitar(3, (cfg.guardadas & (1 << 6)) ? cfg.pinzaAbierta : 90);
  for (uint8_t i = 0; i < 4; i++) {
    servos[i].write(angulo[i]);
    servos[i].attach(PIN_SERVOS[i]);
  }
}

// Lleva base, hombro y codo a una pose. Devuelve false si hubo PARO.
bool moverBrazo(const Pose &p, uint8_t msPorGrado) {
  if (paro) { atenderParo(); return false; }
  uint8_t objetivo[3] = { limitar(0, p.b), limitar(1, p.h), limitar(2, p.c) };
  uint8_t inicio[3]   = { angulo[0], angulo[1], angulo[2] };
  int pasos = 0;
  for (uint8_t i = 0; i < 3; i++) pasos = max(pasos, abs((int)objetivo[i] - (int)inicio[i]));

  ocupado = true;
  for (int k = 1; k <= pasos; k++) {
    for (uint8_t i = 0; i < 3; i++) {
      // interpolación lineal: todas las articulaciones terminan juntas
      uint8_t a = inicio[i] + (long)((int)objetivo[i] - (int)inicio[i]) * k / pasos;
      if (a != angulo[i]) { angulo[i] = a; servos[i].write(a); }
    }
    if (!esperar(msPorGrado)) { ocupado = false; return false; }
  }
  ocupado = false;
  return true;
}

// Mueve un solo servo (se usa para la pinza y para el comando MOVER)
bool moverServo(uint8_t i, int destino, uint8_t msPorGrado) {
  if (paro) { atenderParo(); return false; }
  uint8_t obj = limitar(i, destino);
  ocupado = true;
  while (angulo[i] != obj) {
    angulo[i] += (obj > angulo[i]) ? 1 : -1;
    servos[i].write(angulo[i]);
    if (!esperar(msPorGrado)) { ocupado = false; return false; }
  }
  ocupado = false;
  return true;
}

bool moverPinza(uint8_t ang, uint8_t msPorGrado) {
  return moverServo(3, ang, msPorGrado);
}

// Cierra de a 1 grado hasta que el FSR pase el umbral (o hasta el ángulo de
// "cerrada" si el FSR está desactivado o no siente nada). Luego aprieta unos
// grados más para sujetar firme. Devuelve en fsrMax la mayor fuerza leída.
bool cerrarPinzaSintiendo(int &fsrMax) {
  if (paro) { atenderParo(); return false; }
  int8_t dir = (cfg.pinzaCerrada > angulo[3]) ? 1 : -1;
  uint8_t extra = 0;
  bool sintio = false;
  fsrMax = 0;
  ocupado = true;
  while (angulo[3] != limitar(3, cfg.pinzaCerrada)) {
    angulo[3] += dir;
    servos[3].write(angulo[3]);
    if (!esperar(MS_POR_GRADO_PINZA)) { ocupado = false; return false; }
    int f = leerFsr();
    if (f > fsrMax) fsrMax = f;
    if (USAR_FSR && f >= (int)cfg.umbralFsr) sintio = true;
    if (sintio && ++extra >= APRIETE_EXTRA) break;
  }
  ocupado = false;
  return true;
}
