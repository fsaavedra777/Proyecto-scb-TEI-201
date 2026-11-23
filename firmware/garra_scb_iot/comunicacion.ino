/*
 * comunicacion.ino — Protocolo con el gateway (una línea JSON por mensaje)
 *
 * SALIDA (Arduino -> PC), 115200 baudios:
 *   {"t":"tel", ...}  telemetría cada 500 ms: estado y lectura de cada sensor
 *   {"t":"evt", ...}  un evento por residuo: material, resultado, tiempos
 *   {"t":"est", ...}  cambio de estado de la máquina
 *   {"t":"cfg", ...}  configuración actual (al encender o con ESTADO)
 *   {"t":"ack", ...}  respuesta a un comando
 *   {"t":"log", ...}  mensaje para el operario
 *
 * ENTRADA (PC -> Arduino): comandos de texto terminados en salto de línea.
 *   Escriban AYUDA en el Monitor Serie para ver la lista.
 */

// ---------------------------- Ayudantes JSON -------------------------
// Se escribe directo al puerto, sin armar el texto en RAM (el UNO tiene 2 KB).
void jIni(const __FlashStringHelper *tipo) {
  Serial.print(F("{\"t\":\"")); Serial.print(tipo); Serial.print('"');
}
void jClave(const __FlashStringHelper *k) {
  Serial.print(F(",\"")); Serial.print(k); Serial.print(F("\":"));
}
void jNum(const __FlashStringHelper *k, float v, uint8_t dec) {
  jClave(k);
  if (isnan(v) || isinf(v)) Serial.print(F("null")); else Serial.print(v, dec);
}
void jInt(const __FlashStringHelper *k, long v) { jClave(k); Serial.print(v); }
void jTxt(const __FlashStringHelper *k, const __FlashStringHelper *v) {
  jClave(k); Serial.print('"'); Serial.print(v); Serial.print('"');
}
void jFin() { Serial.println('}'); }

const __FlashStringHelper *nombreEstado(Estado e) {
  switch (e) {
    case INICIANDO:     return F("INICIANDO");
    case SIN_CALIBRAR:  return F("SIN_CALIBRAR");
    case ESPERANDO:     return F("ESPERANDO");
    case ANALIZANDO:    return F("ANALIZANDO");
    case RECOGIENDO:    return F("RECOGIENDO");
    case DEPOSITANDO:   return F("DEPOSITANDO");
    case RETIRO_MANUAL: return F("RETIRO_MANUAL");
    case PAUSADO:       return F("PAUSADO");
    case PARADO:        return F("PARADO");
  }
  return F("?");
}

const __FlashStringHelper *nombreMaterial(Material m) {
  switch (m) {
    case METAL:    return F("METAL");
    case PLASTICO: return F("PLASTICO");
    case DESCARTE: return F("DESCARTE");
    default:       return F("NINGUNO");
  }
}

// ---------------------------- Mensajes de salida ---------------------
void enviarTelemetria() {
  static uint32_t secuencia = 0;     // permite al gateway medir paquetes perdidos
  // En ESPERANDO el ultrasónico ya se mide a 10 Hz; en reposo se mide aquí.
  if (!ocupado && estado != ESPERANDO && estado != ANALIZANDO) distanciaCm = medirDistanciaCm();
  inductivoAhora = leerInductivo();
  capacitivoAhora = leerCapacitivo();
  fsrAhora = leerFsr();

  jIni(F("tel"));
  jInt(F("n"), ++secuencia);
  jInt(F("ms"), millis());
  jTxt(F("est"), nombreEstado(estado));
  jNum(F("dist"), distanciaCm, 1);
  jNum(F("peso"), pesoG, 1);
  jInt(F("ind"), inductivoAhora);
  jInt(F("cap"), capacitivoAhora);
  jInt(F("fsr"), fsrAhora);
  jFin();
}

// Un evento por residuo. res: OK, FALLA_AGARRE, SOBREPESO, FALSA_DETECCION, PARO
void enviarEvento(const __FlashStringHelper *resultado) {
  jIni(F("evt"));
  jInt(F("n"), ciclo.numero);
  jTxt(F("res"), resultado);
  jTxt(F("mat"), nombreMaterial(ciclo.material));
  jClave(F("via")); Serial.print('"'); Serial.print(ciclo.via); Serial.print('"');
  jNum(F("peso"), ciclo.peso, 1);
  jInt(F("ind"), ciclo.pctInductivo);
  jInt(F("cap"), ciclo.pctCapacitivo);
  jInt(F("fsr"), ciclo.fsrMax);
  jInt(F("int"), ciclo.intentos);
  jInt(F("lat"), ciclo.latenciaMs);
  jInt(F("ciclo"), millis() - ciclo.tDeteccion);
  jFin();
}

void enviarCambioEstado() {
  jIni(F("est"));
  jInt(F("ms"), millis());
  jTxt(F("est"), nombreEstado(estado));
  jFin();
}

void enviarConfig() {
  jIni(F("cfg"));
  jClave(F("fw")); Serial.print(F("\"" FW_VERSION "\""));
  jInt(F("cal"), cfg.guardadas == TODO_GUARDADO);
  jInt(F("guardadas"), cfg.guardadas);
  jNum(F("factor"), cfg.factor, 2);
  jInt(F("fsr_umbral"), cfg.umbralFsr);
  jInt(F("usa_cap"), USAR_CAPACITIVO);
  jInt(F("usa_fsr"), USAR_FSR);
  jNum(F("dist_cm"), DIST_OBJETO_CM, 1);
  jNum(F("peso_min"), PESO_MIN_G, 1);
  jNum(F("peso_max"), PESO_MAX_G, 1);
  jNum(F("peso_max_plastico"), PESO_MAX_PLASTICO_G, 1);
  jInt(F("tel_ms"), PERIODO_TELEMETRIA_MS);
  jClave(F("poses")); Serial.print('[');
  for (uint8_t i = 0; i < N_POSES; i++) {
    if (i) Serial.print(',');
    Serial.print('['); Serial.print(cfg.poses[i].b); Serial.print(',');
    Serial.print(cfg.poses[i].h); Serial.print(','); Serial.print(cfg.poses[i].c); Serial.print(']');
  }
  Serial.print(']');
  jClave(F("pinza")); Serial.print('['); Serial.print(cfg.pinzaAbierta); Serial.print(',');
  Serial.print(cfg.pinzaCerrada); Serial.print(']');
  jFin();
}

void logMsg(const __FlashStringHelper *msg) {
  jIni(F("log")); jTxt(F("msg"), msg); jFin();
}

void ack(const char *cmd, bool ok, const __FlashStringHelper *msg) {
  jIni(F("ack"));
  jClave(F("cmd")); Serial.print('"'); Serial.print(cmd); Serial.print('"');
  jInt(F("ok"), ok);
  if (msg) jTxt(F("msg"), msg);
  jFin();
}

// ---------------------------- Comandos de entrada --------------------
char linea[40];
uint8_t largoLinea = 0;

void leerComandos() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (largoLinea > 0) {
        linea[largoLinea] = '\0';
        largoLinea = 0;
        procesarComando(linea);
      }
    } else if (largoLinea < sizeof(linea) - 1) {
      linea[largoLinea++] = toupper(c);
    }
  }
  if (paro && estado != PARADO) atenderParo();
}

// Nombre de pose -> índice (0-5), 6 = ABIERTA, 7 = CERRADA, 255 = desconocido
uint8_t indicePose(const char *s) {
  if (!s) return 255;
  if (!strcmp_P(s, PSTR("REPOSO")))   return P_REPOSO;
  if (!strcmp_P(s, PSTR("SOBRE")))    return P_SOBRE;
  if (!strcmp_P(s, PSTR("BANDEJA")))  return P_BANDEJA;
  if (!strcmp_P(s, PSTR("METAL")))    return P_METAL;
  if (!strcmp_P(s, PSTR("PLASTICO"))) return P_PLASTICO;
  if (!strcmp_P(s, PSTR("DESCARTE"))) return P_DESCARTE;
  if (!strcmp_P(s, PSTR("ABIERTA")))  return 6;
  if (!strcmp_P(s, PSTR("CERRADA")))  return 7;
  return 255;
}

// Los movimientos manuales solo se permiten con el sistema detenido
bool modoAjuste() {
  return !ocupado && (estado == PAUSADO || estado == SIN_CALIBRAR);
}
bool enReposo() {
  return !ocupado && (estado == ESPERANDO || estado == PAUSADO || estado == SIN_CALIBRAR);
}

void procesarComando(char *texto) {
  char *cmd = strtok(texto, " ");
  char *a1 = strtok(NULL, " ");
  char *a2 = strtok(NULL, " ");
  if (!cmd) return;
  char nombre[10];                     // copia: un comando anidado puede pisar 'linea'
  strncpy(nombre, cmd, sizeof(nombre) - 1);
  nombre[sizeof(nombre) - 1] = '\0';

  if (!strcmp_P(cmd, PSTR("AYUDA"))) {
    logMsg(F("ESTADO | TARA | CAL <gramos> | FSR <umbral>"));
    logMsg(F("PAUSA | SEGUIR | PARO"));
    logMsg(F("En pausa: MOVER <B|H|C|P> <grados> | GUARDAR <pose> | IR <pose>"));
    logMsg(F("Poses: REPOSO SOBRE BANDEJA METAL PLASTICO DESCARTE ABIERTA CERRADA"));
    logMsg(F("FABRICA borra la calibracion guardada"));
    ack(nombre, true, NULL);
  }
  else if (!strcmp_P(cmd, PSTR("ESTADO"))) {
    enviarConfig();
    ack(nombre, true, NULL);
  }
  else if (!strcmp_P(cmd, PSTR("PARO"))) {
    paro = true;                                   // se atiende en esperar()/leerComandos()
    ack(nombre, true, NULL);
  }
  else if (!strcmp_P(cmd, PSTR("PAUSA"))) {
    if (estado == ESPERANDO) { cambiarEstado(PAUSADO); ack(nombre, true, NULL); }
    else if (estado == PAUSADO || estado == SIN_CALIBRAR || estado == PARADO) ack(nombre, true, F("Ya detenido"));
    else { pausaPedida = true; ack(nombre, true, F("Se pausa al terminar el ciclo")); }
  }
  else if (!strcmp_P(cmd, PSTR("SEGUIR"))) {
    if (ocupado || estado == ANALIZANDO || estado == RECOGIENDO || estado == DEPOSITANDO) {
      ack(nombre, false, F("Ciclo en curso")); return;
    }
    if (estado == PARADO) {
      paro = false;
      cambiarEstado(PAUSADO);
      if (cfg.guardadas & (1 << P_REPOSO)) moverBrazo(cfg.poses[P_REPOSO], MS_POR_GRADO_BRAZO * 2);
      if (cfg.guardadas & (1 << 6)) moverPinza(cfg.pinzaAbierta, MS_POR_GRADO_PINZA);
    }
    if (cfg.guardadas != TODO_GUARDADO) {
      cambiarEstado(SIN_CALIBRAR);
      ack(nombre, false, F("Faltan poses: use GUARDAR"));
      return;
    }
    pausaPedida = false;
    cambiarEstado(ESPERANDO);
    ack(nombre, true, NULL);
  }
  else if (!strcmp_P(cmd, PSTR("TARA"))) {
    if (!enReposo()) { ack(nombre, false, F("Solo en reposo")); return; }
    hacerTara();
    ack(nombre, true, F("Tara hecha"));
  }
  else if (!strcmp_P(cmd, PSTR("CAL"))) {
    if (!enReposo()) { ack(nombre, false, F("Solo en reposo")); return; }
    int g = a1 ? atoi(a1) : 0;
    if (calibrarBalanza(g)) { ack(nombre, true, F("Factor guardado")); enviarConfig(); }
    else ack(nombre, false, F("Uso: TARA con bandeja vacia, luego CAL <gramos> con la masa puesta"));
  }
  else if (!strcmp_P(cmd, PSTR("FSR"))) {
    int u = a1 ? atoi(a1) : 0;
    if (u < 1 || u > 1023) { ack(nombre, false, F("Uso: FSR <1-1023>")); return; }
    cfg.umbralFsr = u;
    guardarConfig();
    ack(nombre, true, F("Umbral guardado"));
  }
  else if (!strcmp_P(cmd, PSTR("MOVER"))) {
    if (!modoAjuste()) { ack(nombre, false, F("Primero PAUSA")); return; }
    int8_t s = !a1 ? -1 : a1[0] == 'B' ? 0 : a1[0] == 'H' ? 1 : a1[0] == 'C' ? 2 : a1[0] == 'P' ? 3 : -1;
    if (s < 0 || !a2) { ack(nombre, false, F("Uso: MOVER <B|H|C|P> <grados>")); return; }
    moverServo(s, atoi(a2), MS_POR_GRADO_BRAZO);
    ack(nombre, true, NULL);
    enviarAngulos();
  }
  else if (!strcmp_P(cmd, PSTR("GUARDAR"))) {
    if (!modoAjuste()) { ack(nombre, false, F("Primero PAUSA")); return; }
    uint8_t p = indicePose(a1);
    if (p == 255) { ack(nombre, false, F("Pose desconocida")); return; }
    if (p < N_POSES) cfg.poses[p] = { angulo[0], angulo[1], angulo[2] };
    else if (p == 6) cfg.pinzaAbierta = angulo[3];
    else             cfg.pinzaCerrada = angulo[3];
    cfg.guardadas |= (1 << p);
    guardarConfig();
    ack(nombre, true, cfg.guardadas == TODO_GUARDADO ? F("Calibracion completa: envie SEGUIR") : F("Guardada"));
  }
  else if (!strcmp_P(cmd, PSTR("IR"))) {
    if (!modoAjuste()) { ack(nombre, false, F("Primero PAUSA")); return; }
    uint8_t p = indicePose(a1);
    if (p == 255 || !(cfg.guardadas & (1 << p))) { ack(nombre, false, F("Pose no guardada")); return; }
    if (p < N_POSES) moverBrazo(cfg.poses[p], MS_POR_GRADO_BRAZO);
    else moverPinza(p == 6 ? cfg.pinzaAbierta : cfg.pinzaCerrada, MS_POR_GRADO_PINZA);
    ack(nombre, true, NULL);
  }
  else if (!strcmp_P(cmd, PSTR("FABRICA"))) {
    if (!enReposo()) { ack(nombre, false, F("Solo en reposo")); return; }
    configPorDefecto();
    guardarConfig();
    cambiarEstado(SIN_CALIBRAR);
    ack(nombre, true, F("Calibracion borrada"));
  }
  else {
    ack(nombre, false, F("Comando desconocido. Escriba AYUDA"));
  }
}

// Ángulos actuales, para anotar la calibración
void enviarAngulos() {
  jIni(F("ang"));
  jInt(F("b"), angulo[0]); jInt(F("h"), angulo[1]);
  jInt(F("c"), angulo[2]); jInt(F("p"), angulo[3]);
  jFin();
}
